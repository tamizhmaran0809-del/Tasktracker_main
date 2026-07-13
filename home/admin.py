from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Task, Team


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ("employee_id",)
    list_display = ("employee_id", "employee_name", "role", "designation", "team", "is_active")
    list_filter = ("role", "designation", "team")
    search_fields = ("employee_id", "employee_name")

    fieldsets = (
        (None, {"fields": ("employee_id", "password")}),
        ("Personal info", {"fields": ("employee_name", "role", "designation", "team")}),
        ("Status", {"fields": ("is_approved", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("employee_id", "employee_name", "role", "designation", "team", "password1", "password2"),
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "assigned_by", "team", "status", "due_date")
    list_filter = ("status", "team")
    search_fields = ("title",)
