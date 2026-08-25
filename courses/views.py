from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Course, Category


class CourseListView(ListView):
    """List all published courses with filtering and search."""
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Course.objects.filter(status='published')
        # restrict to current company to enforce tenant isolation
        company = getattr(self.request, 'company', None)
        if company:
            queryset = queryset.filter(company=company)
        else:
            # no company resolved for this request — return empty queryset
            return Course.objects.none()
        
        # Search by title or description
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Filter by level
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)

        # Filter by course type — default to 'default' so I2I never leaks into /courses/
        course_type = self.request.GET.get('type')
        if course_type == 'i2i':
            queryset = queryset.filter(course_type='i2i')
        else:
            queryset = queryset.filter(course_type='default')

        # Sort
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, 'company', None)
        # only show categories that have courses for this company
        if company:
            context['categories'] = Category.objects.filter(courses__company=company).distinct()
        else:
            context['categories'] = Category.objects.none()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_level'] = self.request.GET.get('level', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['level_choices'] = Course._meta.get_field('level').choices
        return context


class CourseDetailView(DetailView):
    """Detailed course view with sections, lessons, and enrollment."""
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        # restrict to published courses for the current company only
        company = getattr(self.request, 'company', None)
        qs = Course.objects.filter(status='published')
        if company:
            qs = qs.filter(company=company)
        else:
            return Course.objects.none()
        return qs.prefetch_related('instructors')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
        context['sections'] = course.sections.all()
        context['benefits'] = course.benefits.all()
        context['requirements'] = course.requirements.all()
        context['faqs'] = course.faqs.all()
        context['batches'] = course.batches.filter(status='upcoming') if hasattr(course, 'batches') else []
        # include tools (ManyToMany) and group them by category for template consumption
        tools_qs = course.tools.all()
        context['tools'] = tools_qs
        # group tools by category (preserve order by category name)
        tools_by_cat = {}
        for t in tools_qs:
            cat = t.category or 'Other'
            tools_by_cat.setdefault(cat, []).append(t)
        # also provide ordered list of (category, tools) for easier template iteration
        context['tools_by_category'] = tools_by_cat
        context['tools_by_category_items'] = sorted(tools_by_cat.items(), key=lambda x: x[0])

        instructors_qs = course.instructors.all()
        context['instructors'] = instructors_qs
        context['instructor'] = instructors_qs.first() if instructors_qs.exists() else None
        
        # Calculate total lessons across all sections
        total_lessons = sum(section.lessons.count() for section in context['sections'])
        context['total_lessons'] = total_lessons
        
        # Check if user is enrolled
        if self.request.user.is_authenticated:
            from enrollments.models import Enrollment
            context['user_enrollment'] = Enrollment.objects.filter(
                student=self.request.user,
                batch__course=course
            ).first()
        
        return context
