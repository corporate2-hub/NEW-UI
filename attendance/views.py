from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.http import Http404, JsonResponse
from django.contrib import messages
from .models import Attendance
from classes.models import ClassSession
from enrollments.models import Batch, Enrollment


class MarkAttendanceView(View):
    """Mark attendance for a class session."""
    
    @method_decorator(login_required)
    def get(self, request, class_id):
        class_session = get_object_or_404(ClassSession, id=class_id)
        batch = class_session.batch
        
        # Check if user is instructor for this batch
        if not batch.instructors.filter(id=request.user.id).exists() and not request.user.is_staff:
            raise Http404('You are not authorized to mark attendance for this batch.')
        
        # Get all approved students in the batch
        approved_students = Enrollment.objects.filter(
            batch=batch,
            status='approved'
        ).select_related('student')
        
        # Get existing attendance records
        attendance_records = Attendance.objects.filter(class_session=class_session)
        
        context = {
            'class_session': class_session,
            'batch': batch,
            'rows': [
                {
                    'enrollment': en,
                    'student': en.student,
                    'existing': next((ar for ar in attendance_records if ar.student_id == en.student_id), None),
                }
                for en in approved_students
            ],
        }
        
        return render(request, 'attendance/mark_attendance.html', context)
    
    @method_decorator(login_required)
    def post(self, request, class_id):
        class_session = get_object_or_404(ClassSession, id=class_id)
        batch = class_session.batch
        
        # Check authorization
        if not batch.instructors.filter(id=request.user.id).exists() and not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Get approved students
        approved_enrollments = Enrollment.objects.filter(
            batch=batch,
            status='approved'
        ).values_list('student_id', flat=True)
        
        # Process attendance data
        for student_id in approved_enrollments:
            status = request.POST.get(f'status_{student_id}')
            remarks = request.POST.get(f'remarks_{student_id}', '')
            
            if status in ['present', 'absent', 'late']:
                Attendance.objects.update_or_create(
                    class_session=class_session,
                    student_id=student_id,
                    defaults={
                        'status': status,
                        'remarks': remarks,
                        'recorded_by': request.user,
                    }
                )
        
        messages.success(request, 'Attendance marked successfully.')
        return redirect('attendance:attendance_summary', batch_id=batch.id)


class AttendanceSummaryView(TemplateView):
    """View attendance summary for a batch."""
    template_name = 'attendance/attendance_summary.html'
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.batch = get_object_or_404(Batch, id=self.kwargs['batch_id'])
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batch = self.batch
        
        # Get all approved students
        approvals = Enrollment.objects.filter(
            batch=batch,
            status='approved'
        ).select_related('student')
        
        # Prepare attendance summary for each student
        summary_data = []
        for enrollment in approvals:
            att_summary = Attendance.get_attendance_summary(enrollment.student, batch)
            summary_data.append({
                'student': enrollment.student,
                'summary': att_summary,
            })
        
        context['batch'] = batch
        context['summary_data'] = summary_data
        return context
