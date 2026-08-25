from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from core.models import Category
from accounts.models import Company
from courses.models import Course, Section, Lesson, Benefit, Requirement, FAQ
from enrollments.models import Batch
from classes.models import ClassSession

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for the training platform'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create or get default company
        company, created = Company.objects.get_or_create(
            slug='default-company',
            defaults={
                'name': 'Skill Jobs Training',
                'domain': 'localhost',
                'hero_title': 'Welcome to Skill Jobs Training',
                'hero_subtitle': 'Learn skills that matter'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing company: {company.name}'))

        # Create categories
        categories = []
        category_data = [
            {'name': 'Web Development', 'description': 'Learn web development from basics to advanced'},
            {'name': 'Data Science', 'description': 'Master data science and machine learning'},
            {'name': 'Mobile Development', 'description': 'Build amazing mobile applications'},
            {'name': 'DevOps', 'description': 'Master deployment and infrastructure'},
        ]
        
        for cat in category_data:
            obj, created = Category.objects.get_or_create(
                name=cat['name'],
                defaults={'description': cat['description']}
            )
            categories.append(obj)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat["name"]}'))

        # Create users (instructor and students)
        instructor_data = {
            'username': 'john_instructor',
            'email': 'john@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'instructor',
            'company': company
        }

        instructor, created = User.objects.get_or_create(
            username=instructor_data['username'],
            defaults=instructor_data
        )
        if created:
            instructor.set_password('password123')
            instructor.save()
            self.stdout.write(self.style.SUCCESS(f'Created instructor: {instructor.username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing instructor: {instructor.username}'))

        # Create students
        for i in range(3):
            student, created = User.objects.get_or_create(
                username=f'student{i+1}',
                defaults={
                    'email': f'student{i+1}@example.com',
                    'first_name': f'Student',
                    'last_name': f'{i+1}',
                    'role': 'student',
                    'company': None  # Students can be global
                }
            )
            if created:
                student.set_password('password123')
                student.save()

        # Create courses
        courses = []
        course_data = [
            {
                'title': 'Django REST Framework Masterclass',
                'description': 'Learn to build powerful REST APIs with Django',
                'category': categories[0],
                'level': 'advanced',
                'price': 49.99,
                'duration_hours': 24
            },
            {
                'title': 'Python for Data Science',
                'description': 'Complete guide to data science with Python',
                'category': categories[1],
                'level': 'intermediate',
                'price': 39.99,
                'duration_hours': 30
            },
        ]

        for course_info in course_data:
            course, created = Course.objects.get_or_create(
                title=course_info['title'],
                company=company,
                defaults={
                    'description': course_info['description'],
                    'category': course_info['category'],
                    'level': course_info['level'],
                    'price': course_info['price'],
                    'duration_hours': course_info['duration_hours'],
                    'status': 'published'
                }
            )
            if created:
                # Add instructor via many-to-many
                course.instructors.add(instructor)
                self.stdout.write(self.style.SUCCESS(f'Created course: {course.title}'))
            courses.append(course)

            # Create sections
            section, _ = Section.objects.get_or_create(
                course=course,
                title='Introduction',
                defaults={'order': 1}
            )

            # Create lessons
            for j in range(3):
                Lesson.objects.get_or_create(
                    section=section,
                    title=f'Lesson {j+1}',
                    defaults={
                        'content': 'Lesson content here',
                        'order': j+1,
                        'is_free': j == 0
                    }
                )

            # Create benefits
            benefits = ['Master the fundamentals', 'Build real projects', 'Career advancement']
            for benefit in benefits:
                Benefit.objects.get_or_create(
                    course=course,
                    title=benefit,
                    defaults={'order': benefits.index(benefit) + 1}
                )

            # Create requirements
            requirements = ['Basic Python knowledge', 'Git basics', 'Patience and dedication']
            for req in requirements:
                Requirement.objects.get_or_create(
                    course=course,
                    title=req,
                    defaults={'order': requirements.index(req) + 1}
                )

            # Create FAQ
            faqs = [
                {'question': 'Is this for beginners?', 'answer': 'Yes, we start from basics'},
                {'question': 'What are the prerequisites?', 'answer': 'Basic programming knowledge'},
            ]
            for faq in faqs:
                FAQ.objects.get_or_create(
                    course=course,
                    question=faq['question'],
                    defaults={'answer': faq['answer']}
                )

        # Create batches
        batches = []
        for i, course in enumerate(courses):
            batch, created = Batch.objects.get_or_create(
                course=course,
                name=f'Batch-{i+1}',
                defaults={
                    'company': company,
                    'start_date': timezone.now().date() + timedelta(days=7),
                    'end_date': timezone.now().date() + timedelta(days=37),
                    'max_students': 30,
                    'status': 'upcoming'
                }
            )
            batches.append(batch)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created batch: {batch.name}'))

        # Create classes for batches
        for batch in batches:
            for j in range(5):
                ClassSession.objects.get_or_create(
                    batch=batch,
                    title=f'Class {j+1}',
                    defaults={
                        'topic': f'Topic for class {j+1}',
                        'scheduled_date': timezone.now().date() + timedelta(days=7+j),
                        'scheduled_time': timezone.now().time(),
                        'meet_link': 'https://meet.google.com/example'
                    }
                )

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
