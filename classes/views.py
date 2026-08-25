from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import Http404
from django.utils import timezone
from django.db.models import Subquery, OuterRef, CharField
from .models import ClassSession, ClassResource
from enrollments.models import Batch, Enrollment
from attendance.models import Attendance


class BatchClassListView(ListView):
    """List all classes for a batch."""
    model = ClassSession
    template_name = 'classes/batch_class_list.html'
    context_object_name = 'classes'
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.batch = get_object_or_404(Batch, id=self.kwargs['batch_id'])
        
        # Check if user is enrolled in this batch
        user = self.request.user
        enrollment = Enrollment.objects.filter(
            student=user,
            batch=self.batch,
            status='approved'
        ).first()

        # Allow access if any of:
        # - approved student enrollment
        # - staff/superuser
        # - instructor assigned to the batch
        # - company admin for the batch's company
        is_allowed = bool(enrollment) or user.is_staff
        if not is_allowed:
            if getattr(user, 'role', None) == 'instructor' and self.batch.instructors.filter(id=user.id).exists():
                is_allowed = True
            elif getattr(user, 'role', None) == 'admin' and user.company and self.batch.company == user.company:
                is_allowed = True

        if not is_allowed:
            raise Http404('You are not enrolled in this batch.')
        
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return ClassSession.objects.filter(batch=self.batch).order_by('-scheduled_date', '-scheduled_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['batch'] = self.batch
        upcoming = self.get_queryset().filter(scheduled_date__gte=timezone.now().date())
        past = self.get_queryset().filter(scheduled_date__lt=timezone.now().date())

        user = self.request.user
        if getattr(user, 'role', None) == 'student':
            # Attendance summary for the whole batch
            context['attendance_summary'] = Attendance.get_attendance_summary(user, self.batch)
            # Annotate each past session with the student's own attendance status
            attendance_sq = Attendance.objects.filter(
                student=user,
                class_session=OuterRef('pk'),
            ).values('status')[:1]
            past = past.annotate(my_status=Subquery(attendance_sq, output_field=CharField()))

        context['upcoming_classes'] = upcoming
        context['past_classes'] = past
        return context


@method_decorator(login_required, name='dispatch')
class ClassDetailView(DetailView):
    """Detailed class session view (SaaS safe)."""

    model = ClassSession
    template_name = 'classes/class_detail.html'
    context_object_name = 'class_session'
    pk_url_kwarg = 'class_id'

    def get_queryset(self):
        """
        Restrict queryset according to SaaS rules and avoid N+1s.
        """
        user = self.request.user
        qs = ClassSession.objects.select_related('batch__course__company')

        if user.is_superuser:
            return qs

        # Students: only approved enrollments
        if getattr(user, 'role', None) == 'student':
            return qs.filter(
                batch__enrollments__student=user,
                batch__enrollments__status='approved'
            )

        # Instructors and company admins see classes for their company
        return qs.filter(batch__company=user.company)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # Student access validation
        if getattr(user, 'role', None) == 'student':
            is_enrolled = Enrollment.objects.filter(
                student=user,
                batch=obj.batch,
                status='approved'
            ).exists()
            if not is_enrolled:
                raise Http404('You are not enrolled in this batch.')

        # Instructor validation
        elif getattr(user, 'role', None) == 'instructor':
            if not obj.batch.instructors.filter(id=user.id).exists():
                raise Http404('You are not assigned to this class.')

        # Company admin validation (non-superuser)
        elif getattr(user, 'role', None) == 'admin' and not user.is_superuser:
            if obj.batch.company != user.company:
                raise Http404('Unauthorized access.')

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['resources'] = self.object.resources.all()
        context['batch'] = self.object.batch

        user = self.request.user
        if getattr(user, 'role', None) == 'student':
            context['my_attendance'] = Attendance.objects.filter(
                student=user,
                class_session=self.object,
            ).first()

        return context
