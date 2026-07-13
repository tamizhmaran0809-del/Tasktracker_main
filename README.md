# Task Tracker — E2E Solutions

Django project with role-based task assignment and tracking.

## Setup

```bash
cd taskite
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/register/ to create your first account, or
http://127.0.0.1:8000/admin/ using the superuser you just created.

## Login flow

No admin-approval step. Register → account is usable immediately →
sign in with Employee ID + Password.

## Roles & access (home/models.py)

| Role | Can assign tasks? | Task visibility |
|---|---|---|
| Admin, Manager | Yes | Whole company |
| HR, Tech Lead, Team Lead, Testing Lead, DM Lead | Yes | Own team only |
| Employee | No | Only tasks assigned to them |

This logic lives in one place — `CustomUser.is_reporting_person` and
`CustomUser.is_company_wide` in `home/models.py` — and every view
(`_visible_tasks_for`, `_assignable_employees_for` in `home/views.py`)
reuses those two checks, so dashboard stats, "View Tasks", "Task Assign"
and the CSV export always agree with each other.

A `Team` is auto-assigned at registration based on the Designation chosen
(see `DESIGNATION_TEAM_MAP` in `home/models.py`) — e.g. Software Developer
→ Development team, Testing Engineer → Testing team, etc.

## Pages

- `/` — Dashboard (stats + recent activity, scoped to role)
- `/tasks/assign/` — Team roster, only visible to reporting-person roles
- `/tasks/assign/<id>/` — Assign one or more tasks to a teammate
- `/tasks/view/` — Read-only list of every task in your scope, with search/filter + CSV export
- `/tasks/mine/` — Your own tasks, with one-click status update
