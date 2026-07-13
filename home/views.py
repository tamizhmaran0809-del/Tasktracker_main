import csv

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TaskFormSet
from .models import (
    CustomUser,
    Designation,
    DESIGNATION_TEAM_MAP,
    REPORTING_ROLES,
    Role,
    Task,
    Team,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _team_for_designation(designation):
    """Look up (or create) the Team a new user belongs to, based on
    their designation. Returns None for designations with no fixed team
    (e.g. Manager, Intern) — those users simply see only their own tasks."""
    team_name = DESIGNATION_TEAM_MAP.get(designation)
    if not team_name:
        return None
    team, _ = Team.objects.get_or_create(name=team_name)
    return team


def _visible_tasks_for(user):
    """Core role-based visibility rule, reused by dashboard, view_tasks
    and the CSV export so they always agree with each other.

    - Admin / company-wide (Manager designation) -> every task in the company
    - Everyone else    -> tasks belonging to their own team
    - No team assigned -> just the tasks assigned to them personally
    """
    if user.is_company_wide:
        return Task.objects.all()
    if user.team:
        return Task.objects.filter(team=user.team)
    return Task.objects.filter(assigned_to=user)


def _assignable_employees_for(user):
    """Who this user is allowed to assign tasks to / see on the roster.

    - Company-wide (Admin / Manager designation) -> anyone in the company
    - Other reporting persons                    -> only members of their own team
    """
    if user.is_company_wide:
        return CustomUser.objects.exclude(pk=user.pk)
    if user.team:
        return CustomUser.objects.filter(team=user.team).exclude(pk=user.pk)
    return CustomUser.objects.none()


# ------------------------------------------------------------------
# Auth views
# ------------------------------------------------------------------

@login_required(login_url="login")
def register(request):
    user = request.user

    # Only Admin, or a Reporting Person with the "Manager" designation,
    # can register new employees. This is now an "add employee" action
    # inside the app, not a public self-signup page.
    if not (user.role == Role.ADMIN or user.designation == Designation.MANAGER):
        messages.error(request, "You don't have permission to register new employees.")
        return redirect("index")

    if request.method == "POST":
        employee_name = request.POST.get("employee_name", "").strip()
        employee_id = request.POST.get("employee_id", "").strip()
        role = request.POST.get("role")
        designation = request.POST.get("designation")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "home/register.html")

        if CustomUser.objects.filter(employee_id=employee_id).exists():
            messages.error(request, "This Employee ID is already registered.")
            return render(request, "home/register.html")

        CustomUser.objects.create_user(
            employee_id=employee_id,
            employee_name=employee_name,
            password=password1,
            role=role,
            designation=designation,
            team=_team_for_designation(designation),
            is_approved=True,
        )

        messages.success(
            request,
            "Account created successfully. You can now sign in."
        )
        return redirect("login")

    return render(request, "home/register.html")


def login(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id", "").strip()
        password = request.POST.get("password")

        user = authenticate(request, username=employee_id, password=password)

        if user is None:
            messages.error(request, "Invalid Employee ID or password.")
            return render(request, "home/login.html")

        # No admin-approval gate — correct ID + password logs you straight in.
        auth_login(request, user)
        return redirect("index")

    return render(request, "home/login.html")


def logout(request):
    auth_logout(request)
    return redirect("login")


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@login_required(login_url="login")
def index(request):
    user = request.user
    qs = _visible_tasks_for(user)

    # -------------------------------------------------------------
    # "Preview dashboard as designation" — only for reporting persons
    # (Admin + Reporting Person). Admin/company-wide users can preview
    # any designation present in the whole company. A team-scoped
    # reporting person (e.g. a Team Lead) only gets designations that
    # exist within their own team.
    # -------------------------------------------------------------
    preview_designations = []
    selected_designation = request.GET.get("preview_designation", "").strip()

    if user.is_reporting_person:
        if user.is_company_wide:
            designation_values = set(
                CustomUser.objects.values_list("designation", flat=True)
            )
        elif user.team:
            designation_values = set(
                CustomUser.objects.filter(team=user.team).values_list("designation", flat=True)
            )
        else:
            designation_values = set()

        preview_designations = [
            (value, label) for value, label in Designation.choices
            if value in designation_values
        ]

        valid_values = {value for value, _ in preview_designations}
        if selected_designation and selected_designation in valid_values:
            qs = qs.filter(assigned_to__designation=selected_designation)
        else:
            selected_designation = ""

    selected_designation_label = dict(Designation.choices).get(selected_designation, "")

    total_tasks = qs.count()
    completed_tasks = qs.filter(status=Task.Status.COMPLETED).count()
    pending_tasks = qs.filter(status=Task.Status.PENDING).count()
    blocked_tasks = qs.filter(status=Task.Status.BLOCKED).count()

    recent_activity = qs.select_related("assigned_to")[:6]

    return render(request, "home/index.html", {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "blocked_tasks": blocked_tasks,
        "recent_activity": recent_activity,
        "preview_designations": preview_designations,
        "selected_designation": selected_designation,
        "selected_designation_label": selected_designation_label,
    })


# ------------------------------------------------------------------
# Task assignment (reporting-person roles only)
# ------------------------------------------------------------------

@login_required(login_url="login")
def task_assign_list(request):
    user = request.user

    if not user.is_reporting_person:
        messages.error(request, "You don't have permission to assign tasks.")
        return redirect("index")

    employees = _assignable_employees_for(user).annotate(
        open_count=Count(
            "tasks_received",
            filter=~Q(tasks_received__status=Task.Status.COMPLETED),
        )
    )

    if user.is_company_wide:
        scope_message = "You can assign tasks to anyone across the company."
    else:
        team_name = user.team.name if user.team else "no team yet"
        scope_message = f"You can assign tasks within your team ({team_name})."

    return render(request, "home/task_assign_list.html", {
        "employees": employees,
        "scope_message": scope_message,
    })


@login_required(login_url="login")
def task_assign_form(request, emp_id):
    user = request.user

    if not user.is_reporting_person:
        messages.error(request, "You don't have permission to assign tasks.")
        return redirect("index")

    employee = get_object_or_404(_assignable_employees_for(user), pk=emp_id)
    reporting_to_choices = CustomUser.objects.filter(role__in=REPORTING_ROLES).exclude(pk=user.pk)

    if request.method == "POST":
        formset = TaskFormSet(request.POST, prefix="tasks")

        if formset.is_valid():
            created = 0
            for form in formset:
                task_text = form.cleaned_data.get("task", "").strip()
                if not task_text:
                    continue

                Task.objects.create(
                    title=task_text,
                    assigned_to=employee,
                    assigned_by=user,
                    team=employee.team,
                    due_date=form.cleaned_data.get("due_date"),
                    due_time=form.cleaned_data.get("due_time"),
                )
                created += 1

            if created:
                messages.success(
                    request,
                    f"{created} task(s) assigned to {employee.get_full_name()}."
                )
                return redirect("task_assign_list")

            messages.error(request, "Please enter at least one task.")
    else:
        formset = TaskFormSet(prefix="tasks")

    return render(request, "home/task_assign_form.html", {
        "employee": employee,
        "formset": formset,
        "reporting_to_choices": reporting_to_choices,
    })


# ------------------------------------------------------------------
# Read-only view of tasks in scope
# ------------------------------------------------------------------

@login_required(login_url="login")
def view_tasks(request):
    user = request.user

    if user.is_intern:
        messages.error(request, "You don't have permission to view this page.")
        return redirect("index")

    qs = _visible_tasks_for(user)

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(assigned_to__employee_name__icontains=query)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, "home/view_tasks.html", {
        "tasks": qs.select_related("assigned_to", "team"),
        "query": query,
        "status_filter": status_filter,
    })


# ------------------------------------------------------------------
# "My tasks" — every employee's own worklist (not for Admin)
# ------------------------------------------------------------------

@login_required(login_url="login")
def my_tasks(request):
    if request.user.role == Role.ADMIN:
        messages.error(request, "You don't have permission to view this page.")
        return redirect("index")

    tasks = Task.objects.filter(assigned_to=request.user).select_related("assigned_by")
    return render(request, "home/my_tasks.html", {"tasks": tasks})


@login_required(login_url="login")
def update_task_status(request, task_id):
    task = get_object_or_404(Task, pk=task_id, assigned_to=request.user)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in Task.Status.values:
            task.status = new_status
            task.save(update_fields=["status", "updated_at"])
            messages.success(request, "Task status updated.")

    return redirect("my_tasks")


# ------------------------------------------------------------------
# CSV export — respects the same scope + filters as view_tasks
# ------------------------------------------------------------------

@login_required(login_url="login")
def export_tasks_csv(request):
    user = request.user
    qs = _visible_tasks_for(user)

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(assigned_to__employee_name__icontains=query)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tasks.csv"'

    writer = csv.writer(response)
    writer.writerow(["Title", "Assigned To", "Assigned By", "Team", "Status", "Due Date", "Due Time"])

    for task in qs.select_related("assigned_to", "assigned_by", "team"):
        writer.writerow([
            task.title,
            task.assigned_to.get_full_name(),
            task.assigned_by.get_full_name() if task.assigned_by else "-",
            task.team.name if task.team else "-",
            task.get_status_display(),
            task.due_date or "",
            task.due_time or "",
        ])

    return response