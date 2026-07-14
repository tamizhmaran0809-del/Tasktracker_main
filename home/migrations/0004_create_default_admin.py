from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_default_admin(apps, schema_editor):

    CustomUser = apps.get_model("home", "CustomUser")

    if not CustomUser.objects.filter(employee_id="E2E-015").exists():

        CustomUser.objects.create(
            employee_id="E2E-015",
            employee_name="Senthil Pandi",
            role="ADMIN",
            designation="manager",
            password=make_password("Senthil@123"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
            is_approved=True,
        )


def delete_default_admin(apps, schema_editor):

    CustomUser = apps.get_model("home", "CustomUser")

    CustomUser.objects.filter(
        employee_id="E2E-015"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0002_alter_customuser_designation"),
    ]

    operations = [
        migrations.RunPython(
            create_default_admin,
            delete_default_admin
        ),
    ]