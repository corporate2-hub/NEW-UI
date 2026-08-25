from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import Http404
from enrollments.models import Enrollment, Batch
from classes.models import ClassSession
from attendance.models import Attendance
from .models import StudentDashboardAccessLog


class StudentDashboardView(TemplateView):
    """Student dashboard showing enrollments, classes, and attendance."""
    template_name = 'dashboard/student_dashboard.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'student' and not request.user.is_staff:
            raise Http404('You are not authorized to view this page.')
        
        # Log access
        StudentDashboardAccessLog.objects.create(
            student=request.user,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # current company (set by middleware)
        company = getattr(self.request, 'company', None)
        
        # Get enrollments scoped to current company
        if company:
            enrollments = Enrollment.objects.filter(student=user, batch__course__company=company).select_related('batch__course', 'coupon')
        else:
            enrollments = Enrollment.objects.none()
        approved_enrollments = enrollments.filter(status='approved')
        pending_enrollments = enrollments.filter(status='pending')
        
        # Get all approved batches
        approved_batches = [e.batch for e in approved_enrollments]
        if approved_batches:
            upcoming_classes = ClassSession.objects.filter(
                batch__in=approved_batches
            ).order_by('scheduled_date', 'scheduled_time')[:5]
        else:
            upcoming_classes = []
        
        # Calculate attendance statistics
        attendance_stats = {}
        for batch in approved_batches:
            attendance_stats[batch.id] = Attendance.get_attendance_summary(user, batch)
        
        # Get exam attempts
        from exams.models import ExamAttempt
        exam_attempts = ExamAttempt.objects.filter(user=user).select_related('exam').order_by('-completed_at')
        
        context['enrollments'] = enrollments
        context['approved_enrollments'] = approved_enrollments
        context['pending_enrollments'] = pending_enrollments
        context['upcoming_classes'] = upcoming_classes
        context['attendance_stats'] = attendance_stats
        context['exam_attempts'] = exam_attempts

        # Company-level stats (for sidebar/overview)
        from courses.models import Course
        if company:
            context['company_total_courses'] = Course.objects.filter(company=company, status='published').count()
            context['company_total_batches'] = Batch.objects.filter(course__company=company).count()
            context['company_total_enrollments'] = Enrollment.objects.filter(batch__course__company=company).count()
        else:
            context['company_total_courses'] = 0
            context['company_total_batches'] = 0
            context['company_total_enrollments'] = 0
        
        return context


class InstructorDashboardView(TemplateView):
    """Instructor dashboard showing assigned batches and classes."""
    template_name = 'dashboard/instructor_dashboard.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'instructor' and not request.user.is_staff:
            raise Http404('You are not authorized to view this page.')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instructor = self.request.user
        
        # Get assigned batches
        batches = Batch.objects.filter(instructor=instructor)
        
        # Get upcoming classes
        from django.utils import timezone
        upcoming_classes = ClassSession.objects.filter(
            batch__in=batches,
            scheduled_date__gte=timezone.now().date()
        ).order_by('scheduled_date', 'scheduled_time')
        
        context['batches'] = batches
        context['upcoming_classes'] = upcoming_classes
        
        return context


class AdminDashboardView(TemplateView):
    """Admin dashboard for managing the platform."""
    template_name = 'dashboard/admin_dashboard.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404('You are not authorized to view this page.')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        from courses.models import Course
        from accounts.models import CustomUser
        from exams.models import Exam, ExamAttempt
        
        context['total_courses'] = Course.objects.count()
        context['active_batches'] = Batch.objects.filter(status='running').count()
        context['pending_enrollments'] = Enrollment.objects.filter(status='pending').count()
        context['total_students'] = CustomUser.objects.filter(role='student').count()
        context['total_instructors'] = CustomUser.objects.filter(role='instructor').count()
        
        # Exam stats
        context['total_exams'] = Exam.objects.count()
        context['total_exam_attempts'] = ExamAttempt.objects.count()
        
        # Get recent enrollments awaiting approval
        context['pending_approvals'] = Enrollment.objects.filter(
            status='pending'
        ).select_related('student', 'batch__course').order_by('-request_date')[:10]
        
        # Get recent exam attempts
        context['recent_attempts'] = ExamAttempt.objects.select_related('user', 'exam').order_by('-completed_at')[:5]
        
        return context
