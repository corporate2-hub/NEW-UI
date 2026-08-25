from django.db import models
import uuid
from django.db.models import F, Value, CharField
from django.db.models.functions import Coalesce, NullIf, Trim, Concat
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from accounts.models import CustomUser
from courses.models import Course


class Batch(models.Model):
    """Batch (section) of a course."""
    
    BATCH_STATUS = (
        ('upcoming', 'Upcoming'),
        ('running', 'Running'),
        ('completed', 'Completed'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=100, help_text="e.g., Batch-A, Cohort-2024")
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='batches'
    )
    instructors = models.ManyToManyField(CustomUser, related_name='batches_instructing', blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    max_students = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=BATCH_STATUS, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollments_batch'
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'
        ordering = ['-start_date']
        unique_together = ('course', 'name')
    
    def __str__(self):
        return f"{self.course.title} - {self.name}"
    
    def get_enrolled_count(self):
        return self.enrollments.filter(status='approved').count()
    
    def is_full(self):
        return self.get_enrolled_count() >= self.max_students


class Enrollment(models.Model):
    """Student enrollment in a batch."""
    
    ENROLLMENT_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='enrollments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_enrollments')
    rejection_reason = models.TextField(blank=True, null=True)

    # ======================
    # CERTIFICATE
    # ======================

    certificate_allowed = models.BooleanField(
        default=False,
        help_text='Admin must enable this before student can view/generate certificate.'
    )

    certificate_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text='Public unique ID for certificate verification URL.'
    )

    certificate_given = models.BooleanField(
        default=False,
        help_text='True after certificate PDF has been generated first time.'
    )

    certificate_pdf = models.FileField(
        upload_to='certificates/issued/%Y/%m/',
        null=True,
        blank=True,
        help_text='Generated certificate PDF. Created on first student click.'
    )

    certificate_generated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    certificate_number = models.CharField(
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text='Human-readable certificate number.'
    )
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    course_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Snapshot of course price at enrollment time")
    applied_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="course_fee minus applied_discount")
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
            ('waived', 'Waived'),
        ],
        default='unpaid',
    )
    payment_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Transaction ID / payment gateway reference for future use",
    )

    # Certificate-specific fields
    certificate_registration_no = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Registration number to display on certificate. If empty, uses certificate_number.'
    )
    certificate_total_months = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Total months/duration to display on certificate (e.g., "3 months", "6 Months")'
    )
    certificate_start_period = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Start period to display on certificate (e.g., "January 2024", "01-01-2024")'
    )
    certificate_end_period = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='End period to display on certificate (e.g., "March 2024", "31-03-2024")'
    )
    
    class Meta:
        db_table = 'enrollments_enrollment'
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        ordering = ['-request_date']
        unique_together = ('student', 'batch')
    
    def __str__(self):
        return f"{self.student.username} - {self.batch.name} ({self.status})"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        # Always keep total_due in sync with payment_status.
        # paid / waived → nothing left to collect.
        # unpaid        → what remains after any discount.
        if self.payment_status in ('paid', 'waived'):
            self.total_due = Decimal('0.00')
        else:
            self.total_due = max(
                self.course_fee - self.applied_discount,
                Decimal('0.00'),
            )
        super().save(*args, **kwargs)


class SalesRecordManager(models.Manager):
    """
    Custom manager for SalesRecord (proxy of Enrollment).
    Annotates each Enrollment row with flat fields from related models so the
    admin and any view can access student_name, course_title, etc. directly.
    Works with any database – no SQL view required.
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('student', 'batch__course', 'batch__company')
            .annotate(
                student_name=Coalesce(
                    NullIf(
                        Trim(Concat(
                            'student__first_name',
                            Value(' '),
                            'student__last_name',
                            output_field=CharField(),
                        )),
                        Value(''),
                    ),
                    F('student__username'),
                    output_field=CharField(),
                ),
                student_email=F('student__email'),
                course_title=F('batch__course__title'),
                course_price=F('batch__course__price'),
                batch_name=F('batch__name'),
                company_id=F('batch__company_id'),
                company_name=F('batch__company__name'),
            )
        )


class SalesRecord(Enrollment):
    """
    Read-only proxy model over Enrollment.

    Exposes all Enrollment fields plus annotated flat fields
    (student_name, course_title, batch_name, company_name, etc.) via
    SalesRecordManager – no database view needed, works on any DB engine.

    The cached_property definitions below satisfy Django's admin system check.
    When the queryset provides annotations those values are stored in the
    instance __dict__ and take precedence over these fallback properties.
    """

    objects = SalesRecordManager()

    # ── Fallback properties (used when instance is not from SalesRecordManager)
    # ── Annotations from SalesRecordManager shadow these at query time. ────────

    @cached_property
    def student_name(self):
        name = f"{self.student.first_name} {self.student.last_name}".strip()
        return name or self.student.username

    @cached_property
    def student_email(self):
        return self.student.email

    @cached_property
    def course_title(self):
        return self.batch.course.title

    @cached_property
    def batch_name(self):
        return self.batch.name

    class Meta:
        proxy = True
        verbose_name = 'Sales Record'
        verbose_name_plural = 'Sales Records'
        ordering = ['-request_date']

    def __str__(self):
        name = getattr(self, 'student_name', None) or self.student.username
        title = getattr(self, 'course_title', None) or self.batch.course.title
        return f"{name} – {title} ({self.status})"


class Coupon(models.Model):
    """Coupon for discounts on enrollments."""
    
    DISCOUNT_TYPES = (
        ('flat', 'Flat Discount'),
        ('percentage', 'Percentage Discount'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='coupons'
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE, 
        related_name='coupons', 
        null=True, 
        blank=True, 
        help_text="Leave blank to apply to all batches in the company"
    )
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage (e.g. 10 for 10%) or Flat Amount")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_limit = models.IntegerField(null=True, blank=True, help_text="Maximum number of uses")
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'enrollments_coupon'
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.code} - {self.company.name}"
        
    def is_valid(self, batch):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        if self.max_limit is not None and self.used_count >= self.max_limit:
            return False
        if self.company_id != batch.company_id:
            return False
        if self.batch_id and self.batch_id != batch.id:
            return False
        return True
