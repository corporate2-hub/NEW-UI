from django import forms
from core.models import Category
from .models import Question

class QuestionImportForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=True,
        help_text="Select category for imported questions"
    )
    excel_file = forms.FileField(
        required=True,
        help_text="Upload .xlsx file (max 30 questions)"
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['category'].queryset = Category.objects.filter(company=company)
        else:
            self.fields['category'].queryset = Category.objects.all()
