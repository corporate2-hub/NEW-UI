# Quick Start Guide

## Getting Started in 5 Minutes

### 1. Start the Development Server
```bash
python manage.py runserver
```

### 2. Access the Application
- **Homepage**: http://localhost:8000/
- **Login**: http://localhost:8000/auth/login/
- **Register**: http://localhost:8000/auth/register/
- **Admin Panel**: http://localhost:8000/admin/

### 3. Test Accounts

**Admin/Superuser**
- Username: (created with `createsuperuser`)
- Access: `/admin/`

**Instructor**
- Username: `john_instructor`
- Password: `password123`
- Access: `/dashboard/instructor/`

**Students**
- Username: `student1`, `student2`, `student3`
- Password: `password123`
- Access: `/dashboard/student/`

### 4. Sample Data Included
- ✅ 4 Categories (Web Dev, Data Science, Mobile, DevOps)
- ✅ 2 Courses (Django REST, Python for Data Science)
- ✅ 2 Batches per course
- ✅ Multiple sections and lessons
- ✅ Benefits, requirements, and FAQs for each course
- ✅ 5 class sessions per batch

### 5. Common Tasks

**Browse Courses**
1. Go to `/courses/`
2. Use filters: category, level, search
3. Click course to see details

**Enroll in a Course**
1. View course detail
2. Select a batch
3. Click "Enroll Now"
4. Admin approves via `/admin/` → Enrollments

**Mark Attendance**
1. Login as instructor
2. Go to class
3. Mark attendance for students
4. View attendance summary

**Check Dashboard**
1. Login as student
2. View my enrollments
3. See upcoming classes
4. Check attendance statistics

### 6. Database Access

**SQLite (Development)**
- File location: `db.sqlite3`
- No setup needed

**PostgreSQL (Production)**
1. Install PostgreSQL
2. Create database: `createdb skilltraining`
3. Update settings.py with credentials
4. Run migrations: `python manage.py migrate`

### 7. Add New Content

**Create a New Course**
1. Go to `/admin/courses/course/add/`
2. Fill course details
3. Add instructor
4. Set status to "Published"
5. Students can now see it

**Create Sections & Lessons**
1. Go to `/admin/courses/section/add/`
2. Select course
3. Add lessons with content
4. Set lesson order

**Create and Manage Batches**
1. Go to `/admin/enrollments/batch/add/`
2. Select course and instructor
3. Set start/end dates and max students
4. Students can now request enrollment

**Schedule Classes**
1. Go to `/admin/classes/classsession/add/`
2. Select batch
3. Add title, topic, date, time
4. Add Google Meet link (required)
5. Recording link can be added later

### 8. Customizations

**Change Brand Name**
- Edit base.html: Search for "Skill.jobs"
- Update site name in admin: https://localhost:8000/admin/sites/site/1/

**Change Color Scheme**
- Edit tailwindcss config in base.html
- Modify `dark` color palette
- Update CSS classes in templates

**Add Email Support**
- Configure email in settings.py
- Uncomment email sending in views
- Update email templates

**Enable API**
- Create `api/` app
- Add serializers for models
- Register API routes

### 9. Useful Django Commands

```bash
# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Create migrations for new models
python manage.py makemigrations

# Populate sample data
python manage.py populate_sample_data

# Enter Django shell
python manage.py shell

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic

# Check for issues
python manage.py check

# Show database state
python manage.py dbshell
```

### 10. File Structure Reference

```
f:\newtraining\
├── manage.py                 # CLI entry point
├── db.sqlite3               # Development database
├── skilltraining/           # Main project
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI server config
├── accounts/                # User management
├── core/                    # Public pages
├── courses/                 # Course management
├── enrollments/             # Batch & enrollments
├── classes/                 # Class sessions
├── attendance/              # Attendance tracking
├── dashboard/               # User dashboards
├── templates/               # HTML templates
├── static/                  # CSS, JS, images
└── media/                   # User uploads (profiles, course images)
```

### 11. Next Steps

1. **Customize Styling**
   - Modify templates/base.html
   - Update Tailwind config
   - Add custom CSS

2. **Add More Features**
   - Payment integration (Stripe)
   - Email notifications
   - Video streaming
   - Discussion forums
   - Assignments and quizzes

3. **Prepare for Production**
   - Switch to PostgreSQL
   - Configure email
   - Set DEBUG = False
   - Configure allowed hosts
   - Set up SSL/HTTPS
   - Deploy to server (Heroku, AWS, DigitalOcean)

4. **Monitor and Optimize**
   - Enable logging
   - Set up error tracking (Sentry)
   - Optimize database queries
   - Add caching
   - Performance testing

### 12. Useful Links

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Tailwind CSS: https://tailwindcss.com/
- Alpine.js: https://alpinejs.dev/

---

**Need Help?** Check the README.md for comprehensive documentation.
