from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager,
)
from django.utils import timezone


class Role(models.TextChoices):
    """
    Simplified permission tiers. This is separate from Designation —
    Designation (HR, Tech Lead, Manager, Developer, ...) is the actual
    job title and is used to auto-assign a Team. Role controls what a
    user is ALLOWED to do in the app.
    """
    ADMIN = "ADMIN", "Admin"
    REPORTING_PERSON = "REPORTING_PERSON", "Reporting Person"
    EMPLOYEE = "EMPLOYEE", "Employee"
    INTERN = "INTERN", "Intern"


class Designation(models.TextChoices):
    MANAGER = "manager", "Manager"
    HR = "hr", "HR"
    TECH_LEAD = "tech_lead", "Technical Lead"
    TEAM_LEAD_DEV = "team_lead_dev", "Team Lead"
    DEVELOPER = "developer", "Software Developer"
    TESTING_LEAD = "testing_lead", "Testing Lead"
    TESTER = "tester", "Testing Engineer"
    DM_LEAD = "dm_lead", "Digital Marketing Lead"
    DM_EXEC = "dm_exec", "Digital Marketing Executive"
    INTERN = "intern", "Intern"


# ------------------------------------------------------------------
# Role-based access rules (single source of truth used across views)
# ------------------------------------------------------------------

# Roles allowed to assign tasks to others ("reporting person" roles).
REPORTING_ROLES = [
    Role.ADMIN,
    Role.REPORTING_PERSON,
]

# Roles that are ALWAYS company-wide regardless of designation.
COMPANY_WIDE_ROLES = [Role.ADMIN]

# Designations that make a Reporting Person company-wide even though
# their role isn't ADMIN (e.g. a "Manager" designation).
COMPANY_WIDE_DESIGNATIONS = [Designation.MANAGER]

# Which team a designation belongs to. Used to auto-assign a team at
# registration time so task visibility can be scoped correctly.
DESIGNATION_TEAM_MAP = {
    Designation.HR: "HR",
    Designation.TECH_LEAD: "Development",
    Designation.TEAM_LEAD_DEV: "Development",
    Designation.DEVELOPER: "Development",
    Designation.TESTING_LEAD: "Testing",
    Designation.TESTER: "Testing",
    Designation.DM_LEAD: "Digital Marketing",
    Designation.DM_EXEC: "Digital Marketing",
}


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    """Custom manager for employee login."""

    def create_user(self, employee_id, employee_name, password=None, **extra_fields):
        if not employee_id:
            raise ValueError("Employee ID is required")

        if not employee_name:
            raise ValueError("Employee Name is required")

        user = self.model(
            employee_id=employee_id,
            employee_name=employee_name,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, employee_id, employee_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_approved", True)
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("designation", Designation.MANAGER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            employee_id=employee_id,
            employee_name=employee_name,
            password=password,
            **extra_fields
        )


class CustomUser(AbstractBaseUser, PermissionsMixin):
    employee_id = models.CharField(max_length=20, unique=True)
    employee_name = models.CharField(max_length=150)

    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )

    designation = models.CharField(
        max_length=20,
        choices=Designation.choices
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    # No manual admin approval anymore — accounts are usable as soon as
    # they are created. The field is kept (defaulting to True) so nothing
    # else that references it breaks.
    is_approved = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "employee_id"
    REQUIRED_FIELDS = ["employee_name"]

    def __str__(self):
        return f"{self.employee_name} ({self.employee_id})"

    # ---- Compatibility helpers used by templates ----

    @property
    def username(self):
        return self.employee_id

    @property
    def employee_code(self):
        return self.employee_id

    def get_full_name(self):
        return self.employee_name

    def get_short_name(self):
        return self.employee_name.split(" ")[0]

    def get_initials(self):
        parts = [p for p in self.employee_name.strip().split(" ") if p]
        letters = "".join(p[0] for p in parts)[:2]
        return letters.upper() or "?"

    # ---- Role-based access helpers ----

    @property
    def is_reporting_person(self):
        """Can this user assign tasks to others?"""
        return self.role in REPORTING_ROLES

    @property
    def is_company_wide(self):
        """Can this user see/assign across the whole company?

        True for Admins, and for Reporting Persons whose designation is
        Manager (so a "Manager" behaves company-wide like Admin, even
        though their role tier is REPORTING_PERSON).
        """
        return (
            self.role in COMPANY_WIDE_ROLES
            or self.designation in COMPANY_WIDE_DESIGNATIONS
        )

    @property
    def is_intern(self):
        return self.role == Role.INTERN


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        BLOCKED = "BLOCKED", "Blocked"

    title = models.TextField()

    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="tasks_received",
    )
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tasks_given",
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title[:40]} -> {self.assigned_to.employee_name}"