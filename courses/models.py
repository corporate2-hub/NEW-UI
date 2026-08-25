

# ━━━━━━━━━━━━━━━━ Course Audience Model ━━━━━━━━━━━━━━━━

from django.db import models
from django.utils.text import slugify
from urllib.parse import parse_qs, urlparse
from accounts.models import CustomUser
from core.models import Category


class Course(models.Model):
    """Main course model."""
    
    LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )

    COURSE_TYPE_CHOICES = (
        ('default', 'Default (Regular Course)'),
        ('i2i', 'Intern to Industry (I2I)'),
    )
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='courses'
    )
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    instructors = models.ManyToManyField(
        CustomUser,
        related_name='courses_teaching',
        blank=True,
    )
    banner_image = models.ImageField(upload_to='course_banners/', blank=True, null=True)
    sample_certificate = models.ImageField(upload_to='course_certificates/', blank=True, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    registration_start = models.DateTimeField(null=True, blank=True, help_text="When registrations open")
    registration_end = models.DateTimeField(null=True, blank=True, help_text="When registrations close")
    start_date = models.DateField(null=True, blank=True, help_text="Course start date")
    tools = models.ManyToManyField('Tool', blank=True, related_name='courses')
    duration_hours = models.IntegerField(help_text="Total hours of course")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES, default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses_course'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['-created_at']
        unique_together = ('company', 'slug')
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Section(models.Model):
    """Course sections/modules."""
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='course_sections/', blank=True, null=True)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses_section'
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
        ordering = ['order']
        unique_together = ('course', 'order')
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    """Course lessons within sections."""
    
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField()
    thumbnail = models.ImageField(upload_to='lesson_thumbnails/', blank=True, null=True)
    order = models.IntegerField(default=1)
    is_free = models.BooleanField(default=False)
    video_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses_lesson'
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'
        ordering = ['order']
        unique_together = ('section', 'order')
    
    def __str__(self):
        return f"{self.section.title} - {self.title}"

    @property
    def embed_video_url(self):
        """Return iframe-safe embed URL for known providers."""
        if not self.video_url:
            return ""

        raw = self.video_url.strip()
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").strip("/")
        query = parse_qs(parsed.query or "")

        # YouTube support: watch URL, short URL, already-embed URL
        if "youtube.com" in host or "youtu.be" in host:
            video_id = ""
            if "youtu.be" in host:
                video_id = path.split("/")[0] if path else ""
            elif path.startswith("embed/"):
                video_id = path.split("/", 1)[1] if "/" in path else ""
            else:
                video_id = (query.get("v") or [""])[0]

            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"

        # Vimeo support
        if "vimeo.com" in host:
            video_id = path.split("/")[0] if path else ""
            if video_id.isdigit():
                return f"https://player.vimeo.com/video/{video_id}"

        # Fallback to the original URL for providers that allow iframe
        return raw


class Requirement(models.Model):
    """Course requirements."""
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='requirements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'courses_requirement'
        verbose_name = 'Requirement'
        verbose_name_plural = 'Requirements'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Benefit(models.Model):
    """Course benefits/learning outcomes."""
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='benefits')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='benefits/', blank=True, null=True)
    order = models.IntegerField(default=1)
    class Meta:
        db_table = 'courses_benefit'
        verbose_name = 'Benefit'
        verbose_name_plural = 'Benefits'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseMedia(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='media')
    image = models.ImageField(upload_to='course_gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'courses_coursemedia'
        verbose_name = 'Course Media'
        verbose_name_plural = 'Course Media'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.course.title} Media {self.id}"


class FAQ(models.Model):
    """Course FAQs."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'courses_faq'
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.question[:50]}"


class Tool(models.Model):
    """Technology/tools used in the course."""
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='tools',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    icon_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'courses_tool'
        verbose_name = 'Tool'
        verbose_name_plural = 'Tools'
        ordering = ['name']
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class CourseAudience(models.Model):
    course = models.ForeignKey('Course', related_name='audiences', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon_svg = models.TextField(blank=True, help_text="Optional SVG icon markup for this audience.")
    icon_bg = models.CharField(max_length=255, blank=True, help_text="Optional CSS background for icon (e.g. 'linear-gradient(...)')")
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Course Audience'
        verbose_name_plural = 'Course Audiences'

    def __str__(self):
        return f"{self.title} ({self.course})"


class CertificateTemplate(models.Model):
    """
    Course-specific certificate template.

    One course can have multiple templates, but only one should usually be default.
    The background image should already include branding, signature, decorative border, etc.
    Dynamic fields such as student name, course title, certificate number, date, and QR code
    will be drawn on top of the background.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificate_templates'
    )

    name = models.CharField(max_length=150)

    background_image = models.ImageField(
        upload_to='certificates/templates/',
        help_text='Upload certificate background image. Recommended: landscape A4 design.'
    )

    is_default = models.BooleanField(default=False)

    # A4 landscape by default
    width_mm = models.PositiveIntegerField(default=297)
    height_mm = models.PositiveIntegerField(default=210)

    # Student name position
    student_name_x = models.PositiveIntegerField(default=132)
    student_name_y = models.PositiveIntegerField(default=109)
    student_name_font_size = models.PositiveIntegerField(default=32)

    # Course title position
    course_title_x = models.PositiveIntegerField(default=132)
    course_title_y = models.PositiveIntegerField(default=135)
    course_title_font_size = models.PositiveIntegerField(default=20)

    # Issue date position
    date_issued_x = models.PositiveIntegerField(default=53)
    date_issued_y = models.PositiveIntegerField(default=22)
    date_issued_font_size = models.PositiveIntegerField(default=11)

    # Certificate number position
    certificate_no_x = models.PositiveIntegerField(default=180)
    certificate_no_y = models.PositiveIntegerField(default=175)
    certificate_no_font_size = models.PositiveIntegerField(default=10)

    # Registration number position
    registration_no_x = models.PositiveIntegerField(default=65)
    registration_no_y = models.PositiveIntegerField(default=175)
    registration_no_font_size = models.PositiveIntegerField(default=10)

    # Total months position
    total_months_x = models.PositiveIntegerField(default=165)
    total_months_y = models.PositiveIntegerField(default=77)
    total_months_font_size = models.PositiveIntegerField(default=11)

    # Start period position
    start_period_x = models.PositiveIntegerField(default=103)
    start_period_y = models.PositiveIntegerField(default=70)
    start_period_font_size = models.PositiveIntegerField(default=11)

    # End period position
    end_period_x = models.PositiveIntegerField(default=137)
    end_period_y = models.PositiveIntegerField(default=70)
    end_period_font_size = models.PositiveIntegerField(default=11)

    # Custom text position
    custom_text_x = models.PositiveIntegerField(default=53)
    custom_text_y = models.PositiveIntegerField(default=130)
    custom_text_font_size = models.PositiveIntegerField(default=10)
    custom_text_content = models.TextField(blank=True, help_text='Custom text to display on certificate')

    # QR position
    qr_code_x = models.PositiveIntegerField(default=120)
    qr_code_y = models.PositiveIntegerField(default=25)
    qr_code_size = models.PositiveIntegerField(default=32)

    # Text color
    primary_text_color = models.CharField(max_length=20, default='#111827')
    secondary_text_color = models.CharField(max_length=20, default='#374151')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Certificate Template'
        verbose_name_plural = 'Certificate Templates'
        ordering = ['course', '-is_default', 'name']
        unique_together = ('course', 'name')

    def __str__(self):
        return f'{self.course.title} - {self.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Keep only one default template per course
        if self.is_default:
            CertificateTemplate.objects.filter(
                course=self.course,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
