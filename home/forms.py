from django import forms
from django.forms import formset_factory


class TaskForm(forms.Form):
    task = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 2,
            "class": "log-input",
            "placeholder": "Describe the task in detail...",
        })
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "log-input"})
    )
    due_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "log-input"})
    )


# prefix="tasks" is applied wherever this formset is instantiated in views.py,
# to match the "tasks-TOTAL_FORMS" style field names used in the template JS.
TaskFormSet = formset_factory(TaskForm, extra=1)
