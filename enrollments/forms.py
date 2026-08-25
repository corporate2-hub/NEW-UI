from django import forms
from enrollments.models import Enrollment, Batch


class EnrollmentRequestForm(forms.Form):
    """Form for students to request enrollment into a batch."""
    
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.filter(status='upcoming'),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-dark-500'
        })
    )
    coupon_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-dark-500',
            'placeholder': 'Optional Coupon Code'
        })
    )
