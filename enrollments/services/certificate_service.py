import io
import qrcode
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from courses.models import CertificateTemplate


def mm_value(value):
    return value * mm


def get_student_display_name(student):
    full_name = f'{student.first_name} {student.last_name}'.strip()
    return full_name or getattr(student, 'username', None) or getattr(student, 'email', None)


def build_certificate_number(enrollment):
    """
    Example:
    CERT-2026-000123
    """
    year = timezone.now().year
    return f'CERT-{year}-{enrollment.id:06d}'


def auto_fill_certificate_data(enrollment):
    """
    Auto-fill certificate data from batch dates and UUID.
    
    Sets:
    - certificate_registration_no: UUID (verification ID)
    - certificate_start_period: "Month Year" (e.g., "January 2026")
    - certificate_end_period: "Month Year" (e.g., "March 2026")
    - certificate_total_months: "X Months" (e.g., "3 Months")
    """
    batch = enrollment.batch
    
    # Registration number = Verification ID
    if not enrollment.certificate_registration_no:
        enrollment.certificate_registration_no = str(enrollment.certificate_uuid)
    
    # Start period: "Month Year"
    if not enrollment.certificate_start_period:
        start_str = batch.start_date.strftime('%B %Y')  # e.g., "January 2026"
        enrollment.certificate_start_period = start_str
    
    # End period: "Month Year"
    if not enrollment.certificate_end_period:
        end_str = batch.end_date.strftime('%B %Y')  # e.g., "March 2026"
        enrollment.certificate_end_period = end_str
    
    # Total months
    if not enrollment.certificate_total_months:
        # Calculate months between start and end date
        delta = relativedelta(batch.end_date, batch.start_date)
        total_months = delta.months + (delta.years * 12)
        # Ensure at least 1 month if same day
        if total_months == 0:
            total_months = 1
        month_text = f'{total_months} Month{"s" if total_months > 1 else ""}'
        enrollment.certificate_total_months = month_text


def get_certificate_public_url(request, enrollment):
    """
    Public verification URL.
    Example:
    https://example.com/certificate/verify/uuid/
    """
    path = reverse(
        'enrollments:certificate_public',
        kwargs={'uuid': enrollment.certificate_uuid}
    )

    if request is not None:
        return request.build_absolute_uri(path)

    site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{site_url}{path}'


def get_default_certificate_template(enrollment):
    """
    Get default certificate template for the enrollment course.
    """
    course = enrollment.batch.course

    template = CertificateTemplate.objects.filter(
        course=course,
        is_default=True
    ).first()

    if template:
        return template

    return CertificateTemplate.objects.filter(course=course).first()


def make_qr_image(url):
    """
    Create QR image in memory.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return buffer


def draw_centered_text(c, text, x_mm, y_mm, font_name, font_size, color):
    """
    Draw centered text using mm coordinates.
    """
    c.setFont(font_name, font_size)
    c.setFillColor(HexColor(color))

    x = mm_value(x_mm)
    y = mm_value(y_mm)

    c.drawCentredString(x, y, text)


def draw_left_text(c, text, x_mm, y_mm, font_name, font_size, color):
    """
    Draw left-aligned text using mm coordinates.
    """
    c.setFont(font_name, font_size)
    c.setFillColor(HexColor(color))

    x = mm_value(x_mm)
    y = mm_value(y_mm)

    c.drawString(x, y, text)


def generate_certificate_pdf(enrollment, request=None, force=False):
    """
    Generate certificate PDF for an enrollment.

    Behavior:
    - If PDF already exists and force=False, return existing PDF.
    - If admin has not allowed certificate, raise PermissionError.
    - If template missing, raise ValueError.
    - Store generated PDF on enrollment.certificate_pdf.
    """

    if not enrollment.certificate_allowed:
        raise PermissionError('Certificate is not allowed for this enrollment.')

    if enrollment.certificate_pdf and not force:
        return enrollment.certificate_pdf

    template = get_default_certificate_template(enrollment)

    if not template:
        raise ValueError('No certificate template found for this course.')

    if not enrollment.certificate_number:
        enrollment.certificate_number = build_certificate_number(enrollment)

    # Auto-fill certificate data from batch dates
    auto_fill_certificate_data(enrollment)

    public_url = get_certificate_public_url(request, enrollment)

    student = enrollment.student
    batch = enrollment.batch
    course = batch.course

    student_name = get_student_display_name(student)
    course_title = course.title
    issue_date = timezone.localtime(timezone.now()).strftime('%d %B, %Y')
    certificate_number = enrollment.certificate_number

    width = mm_value(template.width_mm)
    height = mm_value(template.height_mm)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))

    # Draw background image
    if template.background_image:
        try:
            bg_path = template.background_image.path

            c.drawImage(
                bg_path,
                0,
                0,
                width=width,
                height=height,
                preserveAspectRatio=False,
                mask='auto'
            )
        except Exception:
            pass

    # Student name
    draw_centered_text(
        c=c,
        text=student_name,
        x_mm=template.student_name_x,
        y_mm=template.student_name_y,
        font_name='Helvetica-Bold',
        font_size=template.student_name_font_size,
        color=template.primary_text_color,
    )

    # Course title
    draw_centered_text(
        c=c,
        text=course_title,
        x_mm=template.course_title_x,
        y_mm=template.course_title_y,
        font_name='Helvetica-Bold',
        font_size=template.course_title_font_size,
        color=template.primary_text_color,
    )

    # Issue date
    draw_left_text(
        c=c,
        text=f'{issue_date}',
        x_mm=template.date_issued_x,
        y_mm=template.date_issued_y,
        font_name='Helvetica',
        font_size=template.date_issued_font_size,
        color=template.secondary_text_color,
    )

    # Certificate number
    draw_left_text(
        c=c,
        text=f'{certificate_number}',
        x_mm=template.certificate_no_x,
        y_mm=template.certificate_no_y,
        font_name='Helvetica',
        font_size=template.certificate_no_font_size,
        color=template.secondary_text_color,
    )

    # Registration number (if provided)
    if enrollment.certificate_registration_no:
        draw_left_text(
            c=c,
            text=f'{enrollment.certificate_registration_no}',
            x_mm=template.registration_no_x,
            y_mm=template.registration_no_y,
            font_name='Helvetica',
            font_size=template.registration_no_font_size,
            color=template.secondary_text_color,
        )

    # Total months (if provided)
    if enrollment.certificate_total_months:
        draw_left_text(
            c=c,
            text=f'{enrollment.certificate_total_months}',
            x_mm=template.total_months_x,
            y_mm=template.total_months_y,
            font_name='Helvetica',
            font_size=template.total_months_font_size,
            color=template.secondary_text_color,
        )

    # Start period (if provided)
    if enrollment.certificate_start_period:
        draw_left_text(
            c=c,
            text=f'{enrollment.certificate_start_period}',
            x_mm=template.start_period_x,
            y_mm=template.start_period_y,
            font_name='Helvetica',
            font_size=template.start_period_font_size,
            color=template.secondary_text_color,
        )

    # End period (if provided)
    if enrollment.certificate_end_period:
        draw_left_text(
            c=c,
            text=f'{enrollment.certificate_end_period}',
            x_mm=template.end_period_x,
            y_mm=template.end_period_y,
            font_name='Helvetica',
            font_size=template.end_period_font_size,
            color=template.secondary_text_color,
        )

    # Custom text (if provided)
    if template.custom_text_content:
        draw_left_text(
            c=c,
            text=template.custom_text_content,
            x_mm=template.custom_text_x,
            y_mm=template.custom_text_y,
            font_name='Helvetica',
            font_size=template.custom_text_font_size,
            color=template.secondary_text_color,
        )

    # QR code
    qr_buffer = make_qr_image(public_url)
    qr_reader = ImageReader(qr_buffer)

    c.drawImage(
        qr_reader,
        mm_value(template.qr_code_x),
        mm_value(template.qr_code_y),
        width=mm_value(template.qr_code_size),
        height=mm_value(template.qr_code_size),
        mask='auto'
    )

    c.showPage()
    c.save()

    pdf_buffer.seek(0)

    filename = f'certificate_{enrollment.certificate_uuid}.pdf'

    enrollment.certificate_pdf.save(
        filename,
        ContentFile(pdf_buffer.read()),
        save=False
    )

    enrollment.certificate_given = True
    enrollment.certificate_generated_at = timezone.now()

    enrollment.save(
        update_fields=[
            'certificate_pdf',
            'certificate_given',
            'certificate_generated_at',
            'certificate_number',
            'certificate_registration_no',
            'certificate_start_period',
            'certificate_end_period',
            'certificate_total_months',
        ]
    )

    return enrollment.certificate_pdf


def generate_sample_certificate_pdf(template):
    """
    Generate a sample/preview certificate PDF from a CertificateTemplate.
    
    Used by admin to preview how the certificate will look.
    Returns a BytesIO object containing the PDF.
    """
    
    if not template:
        raise ValueError('Certificate template is required.')

    # Sample data
    student_name = 'Sample Student Name'
    course_title = template.course.title
    issue_date = timezone.localtime(timezone.now()).strftime('%d %B, %Y')
    certificate_number = f'CERT-{timezone.now().year}-000001'
    
    width = mm_value(template.width_mm)
    height = mm_value(template.height_mm)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))

    # Draw background image
    if template.background_image:
        try:
            bg_path = template.background_image.path

            c.drawImage(
                bg_path,
                0,
                0,
                width=width,
                height=height,
                preserveAspectRatio=False,
                mask='auto'
            )
        except Exception:
            pass

    # Student name
    draw_centered_text(
        c=c,
        text=student_name,
        x_mm=template.student_name_x,
        y_mm=template.student_name_y,
        font_name='Helvetica-Bold',
        font_size=template.student_name_font_size,
        color=template.primary_text_color,
    )

    # Course title
    draw_centered_text(
        c=c,
        text=course_title,
        x_mm=template.course_title_x,
        y_mm=template.course_title_y,
        font_name='Helvetica-Bold',
        font_size=template.course_title_font_size,
        color=template.primary_text_color,
    )

    # Issue date
    draw_left_text(
        c=c,
        text=f'{issue_date}',
        x_mm=template.date_issued_x,
        y_mm=template.date_issued_y,
        font_name='Helvetica',
        font_size=template.date_issued_font_size,
        color=template.secondary_text_color,
    )

    # Certificate number
    draw_left_text(
        c=c,
        text=f'{certificate_number}',
        x_mm=template.certificate_no_x,
        y_mm=template.certificate_no_y,
        font_name='Helvetica',
        font_size=template.certificate_no_font_size,
        color=template.secondary_text_color,
    )

    # Registration number (sample)
    draw_left_text(
        c=c,
        text='REG-2026-000001',
        x_mm=template.registration_no_x,
        y_mm=template.registration_no_y,
        font_name='Helvetica',
        font_size=template.registration_no_font_size,
        color=template.secondary_text_color,
    )

    # Total months (sample)
    draw_left_text(
        c=c,
        text='3 Months',
        x_mm=template.total_months_x,
        y_mm=template.total_months_y,
        font_name='Helvetica',
        font_size=template.total_months_font_size,
        color=template.secondary_text_color,
    )

    # Start period (sample)
    draw_left_text(
        c=c,
        text='January 2026',
        x_mm=template.start_period_x,
        y_mm=template.start_period_y,
        font_name='Helvetica',
        font_size=template.start_period_font_size,
        color=template.secondary_text_color,
    )

    # End period (sample)
    draw_left_text(
        c=c,
        text='March 2026',
        x_mm=template.end_period_x,
        y_mm=template.end_period_y,
        font_name='Helvetica',
        font_size=template.end_period_font_size,
        color=template.secondary_text_color,
    )

    # Custom text (if provided)
    if template.custom_text_content:
        draw_left_text(
            c=c,
            text=template.custom_text_content,
            x_mm=template.custom_text_x,
            y_mm=template.custom_text_y,
            font_name='Helvetica',
            font_size=template.custom_text_font_size,
            color=template.secondary_text_color,
        )

    # QR code (sample verification URL)
    sample_url = 'https://example.com/certificate/verify/sample-uuid/'
    qr_buffer = make_qr_image(sample_url)
    qr_reader = ImageReader(qr_buffer)

    c.drawImage(
        qr_reader,
        mm_value(template.qr_code_x),
        mm_value(template.qr_code_y),
        width=mm_value(template.qr_code_size),
        height=mm_value(template.qr_code_size),
        mask='auto'
    )

    c.showPage()
    c.save()

    pdf_buffer.seek(0)
    return pdf_buffer
