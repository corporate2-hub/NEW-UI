from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from core.models import Category
from courses.models import Course, Section, Lesson, Benefit, Requirement, FAQ, Tool, CourseAudience
from enrollments.models import Batch

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a dummy course with sections, lessons, tools, batches and related data'

    def add_arguments(self, parser):
        parser.add_argument('--title', default='Demo Full Course', help='Course title')
        parser.add_argument('--slug', default=None, help='Optional slug for the course')
        parser.add_argument('--instructor', default='john_instructor', help='(Deprecated) Single instructor username to assign or create')
        parser.add_argument('--instructors', default=None, help='Comma-separated instructor usernames to assign or create')
        parser.add_argument('--category', default='Web Development', help='Category name')
        parser.add_argument('--price', type=float, default=0.0, help='Course price')

    def handle(self, *args, **options):
        title = options['title']
        slug = options.get('slug')
        # Support both --instructor (single) and --instructors (comma-separated)
        instructors_arg = options.get('instructors') or options.get('instructor')
        instructor_usernames = [u.strip() for u in instructors_arg.split(',')] if instructors_arg else []
        category_name = options['category']
        price = options['price']

        self.stdout.write(self.style.NOTICE('Creating dummy course data...'))

        # Instructors (create if missing)
        instructors = []
        for idx, uname in enumerate(instructor_usernames, start=1):
            if not uname:
                continue
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': f'{uname}@example.com',
                    'first_name': 'Instructor' if idx > 1 else 'John',
                    'last_name': f'Instructor{idx}' if idx > 1 else 'Instructor',
                    'role': 'instructor'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created instructor: {user.username}'))
            instructors.append(user)
        # If no instructors provided, fall back to a default single instructor
        if not instructors:
            uname = options.get('instructor') or 'john_instructor'
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': f'{uname}@example.com',
                    'first_name': 'John',
                    'last_name': 'Instructor',
                    'role': 'instructor'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created instructor: {user.username}'))
            instructors.append(user)

        # Category
        category, _ = Category.objects.get_or_create(name=category_name, defaults={'description': f'{category_name} courses'})

        # Create course
        course_defaults = {
            'description': f'A hands-on {category_name} course created for demos and testing.',
            'category': category,
            # instructors assigned after course is created
            'level': 'beginner',
            'price': price,
            'duration_hours': 20,
            'status': 'published',
            'registration_start': timezone.now(),
            'registration_end': timezone.now() + timedelta(days=60),
            'start_date': (timezone.now() + timedelta(days=14)).date(),
        }

        if slug:
            course, created = Course.objects.get_or_create(slug=slug, defaults={'title': title, **course_defaults})
            if created:
                # ensure title is set when creating by slug
                course.title = title
                course.save()
        else:
            course, created = Course.objects.get_or_create(title=title, defaults=course_defaults)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created course: {course.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Using existing course: {course.title}'))

        # Tools
        sample_tools = [
            {'name': 'Django', 'icon_url': '', 'category': 'Backend'},
            {'name': 'Django REST Framework', 'icon_url': '', 'category': 'Backend'},
            {'name': 'React', 'icon_url': '', 'category': 'Frontend'},
            {'name': 'PostgreSQL', 'icon_url': '', 'category': 'Database'},
            {'name': 'Docker', 'icon_url': '', 'category': 'DevOps'},
        ]

        tool_objs = []
        for t in sample_tools:
            obj, _ = Tool.objects.get_or_create(name=t['name'], defaults={'icon_url': t.get('icon_url', ''), 'category': t.get('category', '')})
            tool_objs.append(obj)

        if tool_objs:
            course.tools.set(tool_objs)
            self.stdout.write(self.style.SUCCESS(f'Assigned {len(tool_objs)} tools to course'))

        # Assign instructors to course (ManyToMany)
        if instructors:
            course.instructors.set(instructors)
            self.stdout.write(self.style.SUCCESS(f'Assigned {len(instructors)} instructor(s) to course'))

        # Sections and lessons
        sections_data = [
            {'title': 'Introduction', 'lessons': ['Welcome', 'Setup', 'Course Overview']},
            {'title': 'Core Concepts', 'lessons': ['Routing & Views', 'Models & Migrations', 'Forms & Validation']},
            {'title': 'Project', 'lessons': ['Project Setup', 'Building Features', 'Deployment']},
        ]

        for s_idx, sdata in enumerate(sections_data, start=1):
            section, _ = Section.objects.get_or_create(course=course, title=sdata['title'], defaults={'order': s_idx, 'description': ''})
            for l_idx, ltitle in enumerate(sdata['lessons'], start=1):
                Lesson.objects.get_or_create(
                    section=section,
                    title=ltitle,
                    defaults={'content': f'Content for {ltitle}', 'order': l_idx, 'is_free': l_idx == 1}
                )

        # Benefits
        benefits = ['Practical, project-based learning', 'Industry-relevant skills', 'Career guidance']
        for idx, b in enumerate(benefits, start=1):
            Benefit.objects.get_or_create(course=course, title=b, defaults={'description': '', 'order': idx})

        # Requirements
        requirements = ['Basic Python knowledge', 'Access to a computer', 'Willingness to learn']
        for idx, r in enumerate(requirements, start=1):
            Requirement.objects.get_or_create(course=course, title=r, defaults={'description': '', 'order': idx})

        # FAQs
        faqs = [
            {'question': 'Do I need prior experience?', 'answer': 'No — this course starts from basics.'},
            {'question': 'How long will I have access?', 'answer': 'You will have lifetime access to the course materials.'},
        ]
        for idx, f in enumerate(faqs, start=1):
            FAQ.objects.get_or_create(course=course, question=f['question'], defaults={'answer': f['answer'], 'order': idx})

        # Course Audiences (Who should enroll)
        sample_audiences = [
            {'title': 'Complete Beginners', 'description': 'No coding experience needed — we start from zero', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#06b6d4,#3b82f6)", 'order': 1},
            {'title': 'Career Switchers', 'description': 'Working professionals transitioning into tech', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#f97316,#f43f5e)", 'order': 2},
            {'title': 'Freelancers', 'description': 'Build real skills to earn independently online', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#10b981,#06b6d4)", 'order': 3},
            {'title': 'IT Students', 'description': 'Gain practical hands-on skills beyond theory', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#7c3aed,#a78bfa)", 'order': 4},
            {'title': 'Frontend/Backend Devs', 'description': 'Already know one side? Become full stack', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#06b6d4,#6366f1)", 'order': 5},
            {'title': 'Job Market Ready', 'description': 'Build portfolio projects and deploy like a pro', 'icon_svg': '', 'icon_bg': "linear-gradient(135deg,#ef4444,#fb7185)", 'order': 6},
        ]

        for a in sample_audiences:
            CourseAudience.objects.get_or_create(
                course=course,
                title=a['title'],
                defaults={
                    'description': a.get('description', ''),
                    'icon_svg': a.get('icon_svg', ''),
                    'icon_bg': a.get('icon_bg', ''),
                    'order': a.get('order', 0),
                }
            )

        self.stdout.write(self.style.SUCCESS(f'Created/ensured {course.audiences.count()} audience entries'))

        # Batch
        # Use the first instructor for the Batch.instructor FK
        batch_instructor = instructors[0] if instructors else None

        batch, _ = Batch.objects.get_or_create(
            course=course,
            name=f'Demo Batch - {course.title[:20]}',
            defaults={
                'instructor': batch_instructor,
                'start_date': timezone.now().date() + timedelta(days=14),
                'end_date': timezone.now().date() + timedelta(days=74),
                'max_students': 50,
                'status': 'upcoming'
            }
        )

        self.stdout.write(self.style.SUCCESS('Dummy course data creation complete.'))
        self.stdout.write(self.style.SUCCESS(f'Course: {course.title} (slug: {course.slug})'))
        self.stdout.write(self.style.SUCCESS(f'Sections: {course.sections.count()}, Lessons: {sum([s.lessons.count() for s in course.sections.all()])}'))
        self.stdout.write(self.style.SUCCESS(f'Tools: {course.tools.count()}, Batches: {course.batches.count()}'))
