# Skill Training repository instructions

## Commands

The repository includes a checked-in Windows virtualenv at `venv\`. Unless it is already activated, prefer running Django commands through `.\venv\Scripts\python.exe`.

### Development

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py collectstatic --noinput
```

### Tests

This project uses Django's built-in test runner with per-app `tests.py` files.

```powershell
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py test accounts.tests
.\venv\Scripts\python.exe manage.py test accounts.tests.SomeTestCase.test_method
```

## High-level architecture

- This is a Django 4.2 monolith. `skilltraining\settings.py` registers seven local apps: `accounts`, `core`, `courses`, `enrollments`, `classes`, `attendance`, and `dashboard`. `skilltraining\urls.py` mounts each app under its own route prefix.
- The codebase is company-aware / domain-aware. `accounts.models.Company` holds branding, SEO, scripts, and tenant metadata. `core.middleware.CompanyMiddleware` resolves `request.company` from the host, and `core.context_processors.company_context` injects `company` into every template.
- Public pages are server-rendered Django templates. `templates\base.html` and `templates\core\index.html` read heavily from `company` for logos, meta tags, CTA text, custom CSS, and header/footer scripts, so branding changes usually belong on `Company`, not in templates.
- Content flows through a course hierarchy: `Company -> Course -> Section -> Lesson`, with additional child content on `Course` for `Requirement`, `Benefit`, `FAQ`, `Tool`, `CourseAudience`, and `CourseMedia`.
- Delivery and learner activity flow through `Batch -> ClassSession`, with `Enrollment` connecting students to batches and `Attendance` tracking one record per `(class_session, student)`.
- Dashboards aggregate from the same relational chain instead of separate read models: student dashboards read enrollments, sessions, and attendance; instructor/admin dashboards query batches and approvals directly.

## Key conventions

- Preserve company scoping in all new queries. Public course views (`courses\views.py`) filter by `request.company`; when no company is resolved they intentionally return `Course.objects.none()` instead of showing cross-tenant data.
- Preserve company scoping in admin. `accounts\admin_mixins.py` is the shared pattern: non-superusers only see their own company's records, and `save_model` auto-assigns the company when possible.
- `Course.slug` is only unique within a company (`unique_together = ('company', 'slug')`). Any slug lookup must stay inside a company-filtered queryset.
- Students are treated as global learners and may have `company=None`; instructors and admins are expected to be company-bound. Existing permission checks mix `request.user.role` with Django `is_staff` / `is_superuser`, so follow that pattern instead of replacing it with a new permission style in one area.
- The admin uses `django-unfold`, and course management is inline-heavy. If you change course structure, also check `courses\admin.py` because sections, benefits, requirements, FAQs, and audience items are edited inline there.
- The UI stack is template-first: Tailwind is loaded from the CDN in `templates\base.html`, Alpine.js is used directly in templates, and many forms define widget classes in Python (`accounts\forms.py`) instead of a separate frontend build step.
- The repository docs describe the older single-tenant shape in a few places. Before changing docs, seed data, or URLs, trust the current models, middleware, views, and admin classes over README-era assumptions.
- `core\management\commands\populate_sample_data.py` exists, but it still references older model fields. If you need sample data, update that command together with the current `Course` / `Batch` model shape instead of assuming it is already in sync.

## Admin Company Scoping Implementation (May 2026)

All Django admin pages are now fully company-scoped. Company admins (staff users with a company FK) can only view and manage their own company's data.

### Company-Scoped Admin Classes

**Courses App** (`courses/admin.py`):
- `CourseAdmin`: Uses `CompanyAdminMixin`; filters courses, categories, tools, instructors by company
- `SectionAdmin`, `LessonAdmin`, `RequirementAdmin`, `BenefitAdmin`, `FAQAdmin`, `CourseAudienceAdmin`, `CourseMediaAdmin`: All implement `get_queryset()` with course__company filter and `formfield_for_foreignkey()` to restrict FK dropdowns
- `ToolAdmin`: Uses `CompanyAdminMixin`; allows each company to maintain independent tool lists via `unique_together = ('company', 'name')`

**Enrollments App** (`enrollments/admin.py`):
- `BatchAdmin`: Uses `CompanyAdminMixin`; added company field to fieldsets with explicit `save_model()` to auto-assign
- `EnrollmentAdmin`: Implements `has_add_permission=False` (only superusers can add); company admins can only change status/approval fields via `get_readonly_fields()`; uses `get_list_filter()` to hide cross-company course filters

**Classes App** (`classes/admin.py`):
- `ClassSessionAdmin`: Filters by batch__company; implements `get_list_filter()` to prevent sidebar leakage of cross-company courses

**Attendance App** (`attendance/admin.py`):
- `AttendanceAdmin`: Filters by class_session__batch__company; restricts class_session FK to company's batches

**Dashboard App** (`dashboard/admin.py`):
- `StudentDashboardAccessLogAdmin`: Scoped via student__enrollments__batch__company; disabled add/change permissions (read-only view)

**Core App** (`core/admin.py`):
- `CategoryAdmin`: Uses `CompanyAdminMixin`; allows each company independent categories via `unique_together = ('company', 'name')`
- Dynamic site header: Patches `admin.site.each_context()` to show company name for logged-in company admins

### Key Scoping Patterns

1. **get_queryset()**: Filter to company for non-superusers, return `.none()` if user has no company
2. **formfield_for_foreignkey()/formfield_for_manytomany()**: Restrict dropdown/multi-select to user's company resources
3. **get_list_filter()**: Conditionally return different filters; non-superusers don't see company/course filters that leak cross-company data
4. **Fieldsets**: Include company field (will be readonly via CompanyAdminMixin)
5. **Permission methods**: Override `has_add_permission()`, `has_change_permission()` to enforce role-based restrictions

### Models with Company Field

- `courses.Tool`: `company` FK, `unique_together = ('company', 'name')`
- `core.Category`: `company` FK, `unique_together = ('company', 'name')`
- All other models (Course, Batch, Enrollment, ClassSession, Attendance) already scoped

### Admin UI Improvements

- Site header dynamically shows company name instead of generic "Skill Jobs Training SaaS"
- List filters prevent sidebar leakage of cross-company categorical data
- FK/M2M dropdowns only show relevant company resources
- Read-only models (StudentDashboardAccessLog) prevent accidental modifications
