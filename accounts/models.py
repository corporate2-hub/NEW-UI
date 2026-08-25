from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    # ======================
    # DOMAIN / ROUTING
    # ======================
    domain = models.CharField(
        max_length=255,
        unique=True,
        help_text="example.com or company.skill.jobs"
    )

    # ======================
    # BRANDING
    # ======================
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    favicon = models.ImageField(upload_to='company/', blank=True, null=True)
    partner_logo = models.ImageField(upload_to='company/', blank=True, null=True)

    # ======================
    # HERO
    # ======================
    hero_badge = models.CharField(max_length=255, blank=True)
    hero_title = models.TextField(blank=True)
    hero_subtitle = models.TextField(blank=True)

    hero_primary_text = models.CharField(max_length=100, blank=True)
    hero_primary_link = models.CharField(max_length=255, blank=True)

    hero_secondary_text = models.CharField(max_length=100, blank=True)
    hero_secondary_link = models.CharField(max_length=255, blank=True)

    # ======================
    # STATS
    # ======================
    total_students = models.CharField(max_length=50, blank=True)
    total_batches = models.CharField(max_length=50, blank=True)
    total_mentors = models.CharField(max_length=50, blank=True)

    # ======================
    # FEATURED SECTION
    # ======================
    featured_title = models.CharField(max_length=255, blank=True)
    featured_subtitle = models.TextField(blank=True)

    # ======================
    # CTA SECTION
    # ======================
    cta_title = models.CharField(max_length=255, blank=True)
    cta_subtitle = models.TextField(blank=True)
    cta_phone = models.CharField(max_length=50, blank=True)

    # ======================
    # FOOTER / CONTACT
    # ======================
    footer_text = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    facebook_url = models.URLField(blank=True, null=True)
    x_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)

    # ======================
    # SEO / META
    # ======================
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)

    # ======================
    # OPEN GRAPH (SOCIAL SHARE)
    # ======================
    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.TextField(blank=True)
    og_image = models.ImageField(upload_to='company/', blank=True, null=True)

    # ======================
    # FEATURE IMAGE (GENERAL USE)
    # ======================
    feature_image = models.ImageField(upload_to='company/', blank=True, null=True)

    # ======================
    # CUSTOMIZATION (VERY POWERFUL)
    # ======================
    custom_css = models.TextField(blank=True, help_text="Custom CSS for this company")
    # ======================
    # SSL COMMERZ SETTINGS
    # ======================
    ssl_commerce_key = models.CharField(max_length=255, blank=True, help_text="SSL Commerce Key")
    ssl_commerce_secret = models.CharField(max_length=255, blank=True, help_text="SSL Commerce Secret")
    ssl_commerce_url = models.URLField(blank=True, help_text="SSL Commerce Endpoint URL")

    header_scripts = models.TextField(
        blank=True,
        help_text="Scripts inside <head> (analytics, meta, etc)"
    )

    footer_scripts = models.TextField(
        blank=True,
        help_text="Scripts before </body>"
    )

    # ======================
    # FEATURES / PERMISSIONS
    # ======================
    allow_i2i = models.BooleanField(
        default=False,
        help_text="Allow this company to create Intern to Industry (I2I) courses"
    )

    # ======================
    # STATUS
    # ======================
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_company'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def save(self, *args, **kwargs):
        if self.domain:
            self.domain = (
                self.domain
                .replace("http://", "")
                .replace("https://", "")
                .replace(":8000", "")
                .replace("/", "")
                .strip()
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    """Custom user model with role-based access control."""
    
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='instructors/', blank=True, null=True)
    # Skill Jobs SSO fields
    skilljobs_user_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    skilljobs_uuid = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    is_sso_user = models.BooleanField(default=False)
    sso_provider = models.CharField(max_length=50, blank=True, default='')
    sso_last_synced_at = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auth_customuser'
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'
    


    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_instructor(self):
        return self.role == 'instructor'
    
    def is_admin_user(self):
        return self.role == 'admin' or self.is_staff


class PasswordResetToken(models.Model):
    """Track password reset tokens."""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='reset_token')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auth_passwordresettoken'
    
    def __str__(self):
        return f"Reset token for {self.user.email}"

class SMTPSettings(models.Model):
    company = models.OneToOneField('Company', on_delete=models.CASCADE, related_name='smtp_settings', null=True, blank=True)
    email_host = models.CharField(max_length=255, default='smtp.gmail.com')
    email_port = models.IntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    email_host_user = models.CharField(max_length=255)
    email_host_password = models.CharField(max_length=255)
    default_from_email = models.EmailField(max_length=255, help_text="e.g. Noreply <noreply@example.com>")

    class Meta:
        db_table = 'accounts_smtpsettings'
        verbose_name = 'SMTP Settings'
        verbose_name_plural = 'SMTP Settings'

    def __str__(self):
        return f"SMTP Settings for {self.company.name}"
