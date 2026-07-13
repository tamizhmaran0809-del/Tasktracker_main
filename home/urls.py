from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),

    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.register, name="register"),

    path("tasks/assign/", views.task_assign_list, name="task_assign_list"),
    path("tasks/assign/<int:emp_id>/", views.task_assign_form, name="task_assign_form"),
    path("tasks/view/", views.view_tasks, name="view_tasks"),
    path("tasks/mine/", views.my_tasks, name="my_tasks"),
    path("tasks/<int:task_id>/status/", views.update_task_status, name="update_task_status"),
    path("tasks/export/csv/", views.export_tasks_csv, name="export_tasks_csv"),
]
