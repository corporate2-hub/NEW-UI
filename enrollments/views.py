from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from decimal import Decimal
from .models import Enrollment, Batch, Coupon
from .forms import EnrollmentRequestForm
from django.views.generic import DetailView
from django.http import FileResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from .services.certificate_service import generate_certificate_pdf
from .services.email_service import send_company_email
from django.urls import reverse
import datetime

def get_company_admin_email(company):
    admin_email = getattr(company, 'contact_email', None)
    if admin_email:
        return admin_email
    admin_user = company.users.filter(role='admin').exclude(email='').first()
    if admin_user:
        return admin_user.email
    return None


class CertificatePublicView(DetailView):
    """
    Public certificate verification page.

    First visit:
    - If admin allowed certificate
    - Generate PDF if not generated
    - Show certificate public page

    Next visits:
    - Existing PDF is reused
    """

    model = Enrollment
    template_name = 'enrollments/certificates/public_certificate.html'
    context_object_name = 'enrollment'
    slug_field = 'certificate_uuid'
    slug_url_kwarg = 'uuid'

    def get_queryset(self):
        return Enrollment.objects.select_related(
            'student',
            'batch',
            'batch__course',
            'batch__company',
        ).filter(
            certificate_allowed=True,
            status='approved',
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()

        obj = get_object_or_404(
            queryset,
            certificate_uuid=self.kwargs.get('uuid')
        )

        # Generate PDF on first public/student click
        if not obj.certificate_pdf:
            generate_certificate_pdf(obj, request=self.request, force=False)

            # Refresh object after save
            obj.refresh_from_db()

        return obj


class CertificatePDFView(View):
    """
    Public PDF file response.
    Serves PDF inline in browser or as downloadable attachment.
    
    Exempt from X-Frame-Options to allow iframe display in certificate verification page.
    """
    
    @method_decorator(xframe_options_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, uuid, *args, **kwargs):
        enrollment = get_object_or_404(
            Enrollment.objects.select_related(
                'student',
                'batch',
                'batch__course',
            ),
            certificate_uuid=uuid,
            certificate_allowed=True,
            status='approved',
        )

        if not enrollment.certificate_pdf:
            generate_certificate_pdf(enrollment, request=request, force=False)
            enrollment.refresh_from_db()

        if not enrollment.certificate_pdf:
            raise Http404('Certificate PDF not found.')

        # Check if download parameter is present
        download = request.GET.get('download', 'false').lower() == 'true'
        
        response = FileResponse(
            enrollment.certificate_pdf.open('rb'),
            content_type='application/pdf'
        )
        
        filename = f'{enrollment.certificate_number or enrollment.certificate_uuid}.pdf'
        
        if download:
            # Force download
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            # Display inline in browser
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['X-Content-Type-Options'] = 'nosniff'
        
        return response


class StudentCertificateRedirectView(LoginRequiredMixin, View):
    """
    Student clicks certificate from dashboard/enrollment list.

    Security:
    - Student can only access own enrollment.
    - Admin/staff can access any enrollment.
    """

    def get(self, request, enrollment_id, *args, **kwargs):
        queryset = Enrollment.objects.select_related(
            'student',
            'batch',
            'batch__course',
        ).filter(
            pk=enrollment_id,
            certificate_allowed=True,
            status='approved',
        )

        if not request.user.is_staff:
            queryset = queryset.filter(student=request.user)

        enrollment = get_object_or_404(queryset)

        if not enrollment.certificate_pdf:
            generate_certificate_pdf(enrollment, request=request, force=False)

        return redirect(
            'enrollments:certificate_public',
            uuid=enrollment.certificate_uuid
        )


class EnrollmentRequestView(View):
    """Submit enrollment request for a batch."""
    
    @method_decorator(login_required)
    def post(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Check if already enrolled
        if Enrollment.objects.filter(student=request.user, batch=batch).exists():
            messages.warning(request, 'You have already requested enrollment for this batch.')
            return redirect('courses:course_detail', slug=batch.course.slug)
        
        # Check if batch is full
        if batch.is_full():
            messages.error(request, 'This batch is full.')
            return redirect('courses:course_detail', slug=batch.course.slug)
            
        coupon_code = request.POST.get('coupon_code', '').strip()
        coupon = None
        course_fee = batch.course.price
        applied_discount = Decimal('0.00')
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, company=batch.company)
                if not coupon.is_valid(batch):
                    messages.error(request, 'Invalid or expired coupon code.')
                    return redirect('courses:course_detail', slug=batch.course.slug)
                
                # Calculate discount
                if coupon.discount_type == 'percentage':
                    applied_discount = (course_fee * coupon.discount_amount) / 100
                else:
                    applied_discount = min(coupon.discount_amount, course_fee)
                
                # Increment used count
                coupon.used_count += 1
                coupon.save()
            except Coupon.DoesNotExist:
                messages.error(request, 'Invalid coupon code.')
                return redirect('courses:course_detail', slug=batch.course.slug)
        
        total_due = max(course_fee - applied_discount, Decimal('0.00'))
        payment_status = 'waived' if total_due == 0 else 'unpaid'
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            student=request.user,
            batch=batch,
            status='pending',
            coupon=coupon,
            course_fee=course_fee,
            applied_discount=applied_discount,
            total_due=total_due,
            payment_status=payment_status,
        )
        
        # Send Email Alerts
        company = batch.company
        protocol = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        
        # Context for student email
        student_context = {
            'student_name': request.user.get_full_name() or request.user.username,
            'course_name': batch.course.title,
            'batch_name': batch.name,
            'request_date': datetime.datetime.now().strftime("%B %d, %Y"),
            'dashboard_url': f"{protocol}://{domain}{reverse('enrollments:my_enrollments')}",
            'company_name': company.name,
            'current_year': datetime.datetime.now().year,
        }
        
        # Context for admin email
        admin_context = {
            'student_name': request.user.get_full_name() or request.user.username,
            'student_email': request.user.email,
            'course_name': batch.course.title,
            'batch_name': batch.name,
            'request_date': datetime.datetime.now().strftime("%B %d, %Y"),
            'admin_url': f"{protocol}://{domain}/admin/",  # Change this to actual admin dashboard url if needed
            'company_name': company.name,
            'current_year': datetime.datetime.now().year,
        }
        
        admin_email = get_company_admin_email(company)

        # Send to student (CC company admin)
        if request.user.email:
            send_company_email(
                company=company,
                subject=f"Enrollment Request Received - {batch.course.title}",
                template_name='emails/enrollment_request_student.html',
                context=student_context,
                recipient_list=[request.user.email],
                cc_list=[admin_email] if admin_email else None,
            )
            
        # Send to company admin
        if admin_email:
            send_company_email(
                company=company,
                subject=f"New Enrollment Request - {batch.course.title}",
                template_name='emails/enrollment_request_admin.html',
                context=admin_context,
                recipient_list=[admin_email]
            )
        
        messages.success(request, 'Enrollment request submitted. Please wait for admin approval.')
        return redirect('enrollments:my_enrollments')


class MyEnrollmentsView(ListView):
    """List user's enrollments."""
    model = Enrollment
    template_name = 'enrollments/my_enrollments.html'
    context_object_name = 'enrollments'
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return Enrollment.objects.filter(
            student=self.request.user,
            batch__course__company=self.request.company
        ).select_related('batch__course', 'coupon').order_by('-request_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  
        context['approved_enrollments'] = self.get_queryset().filter(status='approved')
        context['pending_enrollments'] = self.get_queryset().filter(status='pending')
        context['rejected_enrollments'] = self.get_queryset().filter(status='rejected')
        return context
