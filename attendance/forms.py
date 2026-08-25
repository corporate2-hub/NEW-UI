from django import forms
from django_select2.forms import ModelSelect2Widget

from .models import Attendance
from accounts.models import CustomUser
from classes.models import ClassSession
from enrollments.models import Enrollment


class ClassSessionCompanyWidget(ModelSelect2Widget):
    """Class session Select2 widget scoped to the current user's company."""

    model = ClassSession
    search_fields = [
        'title__icontains',
        'topic__icontains',
        'batch__name__icontains',
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        qs = super().filter_queryset(request, term, queryset=queryset, **dependent_fields)
        if not request.user.is_superuser:
            company = getattr(request.user, 'company', None)
            if company:
                qs = qs.filter(batch__company=company)
            else:
                return qs.none()
        return qs


class StudentForSessionWidget(ModelSelect2Widget):
    """
    Student Select2 widget that is dependent on the selected class_session.
    Returns only students who are *approved* enrollees of that session's batch,
    further scoped to the current user's company for non-superusers.
    """

    model = CustomUser
    search_fields = [
        'username__icontains',
        'first_name__icontains',
        'last_name__icontains',
        'email__icontains',
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        # Pop class_session before calling super() so the base doesn't try to
        # apply it as a field lookup on CustomUser (which has no such field).
        class_session_id = dependent_fields.pop('class_session', None) or ''

        # Let the base class apply search_fields filtering on the remaining kwargs
        qs = super().filter_queryset(request, term, queryset=queryset, **dependent_fields)

        # Only show student-role users
        qs = qs.filter(role='student')

        if class_session_id:
            enrolled_ids = Enrollment.objects.filter(
                batch__class_sessions__id=class_session_id,
                status='approved',
            ).values_list('student_id', flat=True)
            qs = qs.filter(id__in=enrolled_ids)
        else:
            # No session selected yet — return nothing to prevent leaking all students
            return qs.none()

        # Additional company scoping for non-superusers
        if not request.user.is_superuser:
            company = getattr(request.user, 'company', None)
            if company:
                company_enrolled_ids = Enrollment.objects.filter(
                    batch__company=company,
                    status='approved',
                ).values_list('student_id', flat=True)
                qs = qs.filter(id__in=company_enrolled_ids)
            else:
                return qs.none()

        return qs


class AttendanceAdminForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = '__all__'
        widgets = {
            'class_session': ClassSessionCompanyWidget(
                attrs={'data-placeholder': 'Search class session…'},
            ),
            'student': StudentForSessionWidget(
                dependent_fields={'class_session': 'class_session'},
                attrs={'data-placeholder': 'Select a class session first…'},
            ),
        }
