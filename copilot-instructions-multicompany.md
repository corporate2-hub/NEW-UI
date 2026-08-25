

````md
# Copilot Instructions for Skill Training SaaS Conversion

You are working on an existing Django 4.2 project named `skilltraining`.

The goal is to convert the current single-company training platform into a simple SaaS/multi-company platform with minimum changes.

## Main Rule

Use simple FK-based multi-tenancy.

Do NOT use `django-tenants` or schema-based tenancy now.

Super admin can access all data.

Company admin/instructor/student can access only data belonging to their own company.

---

## Existing Apps

The project has these apps:

- accounts
- core
- courses
- enrollments
- classes
- attendance
- dashboard

Existing custom user model:

```python
AUTH_USER_MODEL = 'accounts.CustomUser'
````

---

## Required SaaS Model Design

Add a `Company` model in `accounts/models.py`.

```python
class Company(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_company'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name
```

---

## Update CustomUser

Add company relation to `CustomUser`.

```python
company = models.ForeignKey(
    Company,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='users'
)
```

Rules:

* Superuser may have `company = None`.
* Normal admin/instructor/student must have a company.
* Company admin means `role='admin'` but not superuser.

---

## Models That Must Get Company Field

Add `company` directly only to top-level tenant-owned models.

Required:

### courses.models.Course

```python
company = models.ForeignKey(
    'accounts.Company',
    on_delete=models.CASCADE,
    related_name='courses'
)
```

### enrollments.models.Batch

```python
company = models.ForeignKey(
    'accounts.Company',
    on_delete=models.CASCADE,
    related_name='batches'
)
```

Optional but recommended:

### core.models.Category

```python
company = models.ForeignKey(
    'accounts.Company',
    on_delete=models.CASCADE,
    related_name='categories',
    null=True,
    blank=True
)
```

Why category can be nullable:

* Super admin may create global categories.
* Company admin may create company-specific categories.

Do NOT add company field to:

* Section
* Lesson
* Requirement
* Benefit
* FAQ
* CourseAudience
* ClassSession
* ClassResource
* Enrollment
* Attendance

Because they can be filtered through Course or Batch.

---

## Fix CourseMedia Model

In current `courses/models.py`, `CourseMedia` is incorrectly nested inside `Benefit`.

Move `CourseMedia` outside `Benefit`.

Correct structure:

```python
class Benefit(models.Model):
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
```

---

## Slug Rule

Course slug is currently globally unique.

For SaaS, change Course slug to:

```python
slug = models.SlugField(blank=True)
```

Then add:

```python
unique_together = ('company', 'slug')
```

Company A and Company B should both be able to have course slug `python-basic`.

Do the same for Category if category is company-specific.

---

## Admin Multi-Tenant Behavior

Create reusable admin mixins.

Create file:

```txt
accounts/admin_mixins.py
```

Add:

```python
class CompanyAdminMixin:
    company_field = 'company'

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not request.user.company_id:
            return qs.none()

        return qs.filter(**{self.company_field: request.user.company})

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(obj, self.company_field):
            if not getattr(obj, f"{self.company_field}_id", None):
                setattr(obj, self.company_field, request.user.company)

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser and self.company_field not in readonly:
            readonly.append(self.company_field)

        return readonly
```

---

## Admin Filtering For Related Models

For models without direct company field, filter through relationship.

Examples:

### SectionAdmin

```python
class SectionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course" and not request.user.is_superuser:
            kwargs["queryset"] = Course.objects.filter(company=request.user.company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

### LessonAdmin

```python
class LessonAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(section__course__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "section" and not request.user.is_superuser:
            kwargs["queryset"] = Section.objects.filter(course__company=request.user.company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

### ClassSessionAdmin

```python
class ClassSessionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(batch__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "batch" and not request.user.is_superuser:
            kwargs["queryset"] = Batch.objects.filter(company=request.user.company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

### EnrollmentAdmin

```python
class EnrollmentAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(batch__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "batch" and not request.user.is_superuser:
            kwargs["queryset"] = Batch.objects.filter(company=request.user.company)

        if db_field.name == "student" and not request.user.is_superuser:
            kwargs["queryset"] = CustomUser.objects.filter(
                company=request.user.company,
                role='student'
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

### AttendanceAdmin

```python
class AttendanceAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(class_session__batch__company=request.user.company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "class_session" and not request.user.is_superuser:
            kwargs["queryset"] = ClassSession.objects.filter(
                batch__company=request.user.company
            )

        if db_field.name == "student" and not request.user.is_superuser:
            kwargs["queryset"] = CustomUser.objects.filter(
                company=request.user.company,
                role='student'
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

---

## CourseAdmin Requirement

In `courses/admin.py`, CourseAdmin must:

* filter by company
* auto assign company
* hide company from non-superusers
* restrict instructors dropdown
* restrict category dropdown
* restrict tools only if tools become company-specific

Example:

```python
@admin.register(Course)
class CourseAdmin(CompanyAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'company', 'category', 'status', 'price', 'created_at']
    list_filter = ['company', 'status', 'level', 'category']
    search_fields = ['title', 'description']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category" and not request.user.is_superuser:
            kwargs["queryset"] = Category.objects.filter(
                models.Q(company=request.user.company) | models.Q(company__isnull=True)
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "instructors" and not request.user.is_superuser:
            kwargs["queryset"] = CustomUser.objects.filter(
                company=request.user.company,
                role='instructor'
            )

        return super().formfield_for_manytomany(db_field, request, **kwargs)
```

Remember to import:

```python
from django.db import models
from accounts.admin_mixins import CompanyAdminMixin
from accounts.models import CustomUser
from core.models import Category
```

---

## BatchAdmin Requirement

```python
@admin.register(Batch)
class BatchAdmin(CompanyAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'company', 'course', 'instructor', 'status', 'start_date', 'end_date']
    list_filter = ['company', 'status', 'start_date']
    search_fields = ['name', 'course__title', 'instructor__username']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "course":
                kwargs["queryset"] = Course.objects.filter(company=request.user.company)

            if db_field.name == "instructor":
                kwargs["queryset"] = CustomUser.objects.filter(
                    company=request.user.company,
                    role='instructor'
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

---

## CustomUserAdmin Requirement

Company admin should only see users from their company.

Super admin sees all users.

In `accounts/admin.py`:

```python
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {
            'fields': ('role', 'company', 'phone', 'bio', 'profile_image', 'is_verified')
        }),
    )

    list_display = ['username', 'email', 'role', 'company', 'is_staff', 'is_active']
    list_filter = ['role', 'company', 'is_staff', 'is_active']

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(company=request.user.company)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company = request.user.company

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser:
            readonly.append('company')
            readonly.append('is_superuser')

        return readonly
```

---

## DRF Multi-Tenant Rules

Any DRF queryset must follow this pattern:

```python
def get_queryset(self):
    user = self.request.user

    if user.is_superuser:
        return Model.objects.all()

    return Model.objects.filter(company=user.company)
```

For indirect models:

```python
Section.objects.filter(course__company=user.company)
Lesson.objects.filter(section__course__company=user.company)
ClassSession.objects.filter(batch__company=user.company)
Enrollment.objects.filter(batch__company=user.company)
Attendance.objects.filter(class_session__batch__company=user.company)
```

---

## Useful Query Rules

Use these filters:

```python
Course.objects.filter(company=request.user.company)

Batch.objects.filter(company=request.user.company)

Section.objects.filter(course__company=request.user.company)

Lesson.objects.filter(section__course__company=request.user.company)

ClassSession.objects.filter(batch__company=request.user.company)

ClassResource.objects.filter(class_session__batch__company=request.user.company)

Enrollment.objects.filter(batch__company=request.user.company)

Attendance.objects.filter(class_session__batch__company=request.user.company)
```

---

## Prevent Cross-Company Data Leakage

When creating related objects, always validate parent ownership.

Example:

```python
if course.company != request.user.company and not request.user.is_superuser:
    raise PermissionDenied("You do not have permission for this course.")
```

Never trust frontend-selected IDs.

Always filter dropdowns and querysets by company.

---

## Migration Plan

After code changes, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

Because existing data has no company, company fields may need temporary nullable migration.

Recommended safe approach:

1. Add company fields with `null=True, blank=True`
2. Run migrations
3. Create default company
4. Assign existing courses/batches/users to default company
5. Later make company required if needed

Example data migration can be manual in shell:

```bash
python manage.py shell
```

```python
from accounts.models import Company, CustomUser
from courses.models import Course
from enrollments.models import Batch

company, _ = Company.objects.get_or_create(
    slug='default',
    defaults={'name': 'Default Company'}
)

CustomUser.objects.filter(company__isnull=True, is_superuser=False).update(company=company)
Course.objects.filter(company__isnull=True).update(company=company)
Batch.objects.filter(company__isnull=True).update(company=company)
```

---

## Admin Access Rules

Superuser:

```python
request.user.is_superuser == True
```

Can see and manage all data.

Company admin:

```python
request.user.role == 'admin'
request.user.company is not None
request.user.is_superuser == False
```

Can see only own company data.

Instructor:

```python
request.user.role == 'instructor'
```

Can see only own company data.

Student:

```python
request.user.role == 'student'
```

Can see only own company data or own personal data.

---

## Minimum Models To Update First

Start with these files:

```txt
accounts/models.py
courses/models.py
enrollments/models.py
accounts/admin.py
courses/admin.py
enrollments/admin.py
classes/admin.py
attendance/admin.py
dashboard/admin.py
core/admin.py
```

---

## Important Notes

Do not break existing model names or table names.

Do not rename apps.

Do not remove existing fields.

Do not change authentication system.

Do not add schema-based tenancy.

Do not use subdomains yet.

Do not add billing/subscription now.

Focus only on:

* Company model
* User-company relation
* Course-company relation
* Batch-company relation
* Admin filtering
* API queryset filtering

---

## Final Expected Result

After implementation:

* Super admin can create companies.
* Super admin can create company admins.
* Company admin logs in to Django admin.
* Company admin can create courses.
* Created courses automatically belong to that company.
* Company admin only sees own company courses.
* Company admin only sees own batches, enrollments, classes, attendance.
* Company admin cannot select another company’s course/user/batch from dropdown.
* Super admin can still see and manage everything.

````

Then tell Copilot:

```txt
Read .github/copilot-instructions.md and refactor this Django project step by step. 
First implement the Company model, then add company relation to CustomUser, Course, and Batch. 
Then update all Django admin classes for tenant filtering. 
Do not use django-tenants. Keep changes minimal.
````


Good news: your Copilot instruction file is already very solid. But since you said **“add or modify if needed”**, I’ll refine it with **critical SaaS improvements** specifically for your use case:

👉 **Global learners + company-owned courses (marketplace model)**

---

# 🔥 Key Improvements You MUST Add

I’ll show only **what to ADD / MODIFY**, not repeat everything.

---

# ✅ 1. IMPORTANT: Learner is GLOBAL (NEW RULE)

Add this section:

```md
## Learner Model (IMPORTANT CHANGE)

Learners (students) are GLOBAL users.

They are NOT tied to a specific company.

So:

- A student can enroll in courses from multiple companies
- Do NOT restrict students by company in queries
- Only instructors/admins are company-scoped

Modify logic:

CustomUser:
- role = 'student' → can have company = NULL
- role = 'admin' or 'instructor' → must have company

Important:

Never filter students like:
CustomUser.objects.filter(company=request.user.company, role='student')

Instead:

CustomUser.objects.filter(role='student')
```

---

# ⚠️ 2. FIX EnrollmentAdmin (VERY IMPORTANT BUG)

Your current instruction wrongly filters students by company ❌

Replace this:

```python
kwargs["queryset"] = CustomUser.objects.filter(
    company=request.user.company,
    role='student'
)
```

---

### ✅ Correct version:

```python
kwargs["queryset"] = CustomUser.objects.filter(role='student')
```

---

# ⚠️ 3. FIX AttendanceAdmin (same issue)

Replace:

```python
kwargs["queryset"] = CustomUser.objects.filter(
    company=request.user.company,
    role='student'
)
```

---

### ✅ Correct:

```python
kwargs["queryset"] = CustomUser.objects.filter(role='student')
```

---

# ✅ 4. ADD Enrollment Safety Rule (VERY IMPORTANT)

Add this section:

```md
## Enrollment Security Rule

When creating enrollment:

- A student can enroll in any company's course
- But admin/instructor must NOT create enrollment for another company's batch

Validation:

if not request.user.is_superuser:
    if request.user.role in ['admin', 'instructor']:
        if batch.company != request.user.company:
            raise PermissionDenied("Invalid batch selection")
```

---

# ✅ 5. ADD PUBLIC COURSE RULE (Marketplace)

Your current CourseListView is public — good.

Add this rule:

```md
## Public Course Marketplace Rule

Course listing and detail pages are PUBLIC.

Users can browse courses from all companies.

Filter:

Course.objects.filter(
    status='published',
    company__is_active=True
)
```

---

# ⚠️ 6. CATEGORY FIX (MULTI-TENANT SAFE)

Replace:

```python
Category.objects.all()
```

---

### ✅ With:

```python
Category.objects.filter(
    Q(company__isnull=True) | Q(company__is_active=True)
)
```

---

# ⚠️ 7. SLUG CONFLICT (CRITICAL DECISION)

Your instruction says:

```python
unique_together = ('company', 'slug')
```

👉 Good, but your current view:

```python
slug_url_kwarg = 'slug'
```

This will BREAK ❌

---

# ✅ ADD THIS RULE:

```md
## Course URL Rule (IMPORTANT)

Option 1 (Simple - recommended for now):
Keep slug globally unique.

Do NOT use unique_together yet.

Option 2 (Advanced SaaS):
Use URL pattern:

/courses/<company_slug>/<course_slug>/

Then fetch:

Course.objects.get(
    company__slug=company_slug,
    slug=course_slug
)
```

---

# ✅ 8. ADD HELPER PROPERTY (VERY USEFUL)

Add this:

```python
class Enrollment(models.Model):

    @property
    def company(self):
        return self.batch.course.company
```

---

# ✅ 9. ADD GLOBAL QUERY RULES

Add this section:

```md
## Global Query Rules (IMPORTANT)

For PUBLIC (student side):

Courses:
Course.objects.filter(status='published', company__is_active=True)

Enrollments:
Enrollment.objects.filter(student=request.user)

For ADMIN:

Courses:
Course.objects.filter(company=request.user.company)

Enrollments:
Enrollment.objects.filter(batch__company=request.user.company)
```

---

# ✅ 10. ADD DATA LEAK PREVENTION RULE (CRITICAL)

Add:

```md
## Data Isolation Rule (CRITICAL)

Admin and instructors must NEVER access another company's data.

Always validate:

if obj.company != request.user.company and not request.user.is_superuser:
    raise PermissionDenied()
```

---

# 🔥 FINAL RESULT (AFTER THESE FIXES)

Your SaaS becomes:

| Feature               | Status |
| --------------------- | ------ |
| Multi-company courses | ✅      |
| Shared learners       | ✅      |
| Secure admin panel    | ✅      |
| Marketplace browsing  | ✅      |
| No data leakage       | ✅      |

---

# 💥 Biggest Mistake You Avoided

If you didn’t fix student filtering:

👉 Students would be limited to one company ❌
👉 Your marketplace would break ❌

---

# 🚀 If you want next level

I can help you build:

* 🧾 Multi-company revenue tracking
* 💳 Payment split per company
* 🏢 Company public page (like Udemy instructors)
* 📊 Company analytics dashboard

Just tell me 👍
