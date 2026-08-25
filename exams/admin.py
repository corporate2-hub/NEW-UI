import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Question, Exam, ExamAttempt, StudentAnswer
from accounts.admin_mixins import CompanyAdminMixin
from core.models import Category
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget
from django.utils.safestring import mark_safe

@admin.register(Question)
class QuestionAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ('question_text_display', 'category', 'company', 'correct_option')
    
    # Custom action button for Unfold
    change_list_template = "admin/exams/question/change_list.html"

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('company', 'category')
        return ('category',)

    search_fields = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d')

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel), name='exams_question_import_excel'),
        ]
        return custom_urls + urls

    def import_excel(self, request):
        import openpyxl
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from .forms import QuestionImportForm
        from .models import Question
        
        company = getattr(request.user, 'company', None) or getattr(request, 'company', None)
        
        if request.method == "POST":
            form = QuestionImportForm(request.POST, request.FILES, company=company)
            if form.is_valid():
                category = form.cleaned_data['category']
                excel_file = request.FILES['excel_file']
                
                try:
                    wb = openpyxl.load_workbook(excel_file)
                    sheet = wb.active
                    rows = list(sheet.iter_rows(min_row=2, values_only=True))
                    
                    if len(rows) > 30:
                        messages.error(request, "Error: Maximum 30 questions allowed at a time.")
                    else:
                        created_count = 0
                        for row in rows:
                            # Expected columns: Text, A, B, C, D, Correct (A/B/C/D)
                            if not row[0]: continue # Skip empty rows
                            
                            Question.objects.create(
                                company=company,
                                category=category,
                                question_text=row[0],
                                option_a=row[1],
                                option_b=row[2],
                                option_c=row[3],
                                option_d=row[4],
                                correct_option=str(row[5]).strip().upper()
                            )
                            created_count += 1
                        
                        messages.success(request, f"Successfully imported {created_count} questions.")
                        return redirect("admin:exams_question_changelist")
                except Exception as e:
                    messages.error(request, f"Error processing file: {str(e)}")
        else:
            form = QuestionImportForm(company=company)

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Import Questions from Excel",
            "opts": self.model._meta,
        }
        return render(request, "admin/exams/question/import_excel.html", context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            company = getattr(request.user, 'company', None) or getattr(request, 'company', None)
            if company and not request.user.is_superuser:
                kwargs['queryset'] = Category.objects.filter(company=company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

    def question_text_display(self, obj):
        return mark_safe(obj.question_text)
    question_text_display.short_description = 'Question text'

    def save_model(self, request, obj, form, change):
        if not obj.company_id:
            company = getattr(request.user, 'company', None) or getattr(request, 'company', None)
            if company:
                obj.company = company
        super().save_model(request, obj, form, change)

@admin.register(Exam)
class ExamAdmin(CompanyAdminMixin, ModelAdmin):
    list_display = ('title', 'company', 'total_questions', 'time_limit_mins', 'is_active')
    
    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('company', 'is_active')
        return ('is_active',)

    search_fields = ('title',)
    filter_horizontal = ('categories',)

    def save_model(self, request, obj, form, change):
        if not obj.company_id:
            company = getattr(request.user, 'company', None) or getattr(request, 'company', None)
            if company:
                obj.company = company
        super().save_model(request, obj, form, change)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "categories":
            company = getattr(request.user, 'company', None) or getattr(request, 'company', None)
            if company and not request.user.is_superuser:
                kwargs["queryset"] = Category.objects.filter(company=company)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    formfield_overrides = {
        models.TextField: {
            'widget': WysiwygWidget,
        }
    }

@admin.register(ExamAttempt)
class ExamAttemptAdmin(ModelAdmin):
    list_display = ('get_student_name', 'get_student_email', 'exam', 'score', 'total_correct', 'total_questions', 'get_percentage', 'completed_at')
    readonly_fields = ('user', 'exam', 'score', 'total_correct', 'total_questions', 'started_at', 'completed_at', 'answers_snapshot')
    actions = ['export_as_csv']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('exam__company', 'exam', 'completed_at')
        return ('exam', 'completed_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'exam')
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(exam__company=request.user.company)

    @admin.display(description='Student Name', ordering='user__first_name')
    def get_student_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Email', ordering='user__email')
    def get_student_email(self, obj):
        return obj.user.email

    @admin.display(description='Percentage')
    def get_percentage(self, obj):
        if obj.total_questions:
            return f"{round(obj.total_correct / obj.total_questions * 100, 1)}%"
        return '-'

    @admin.action(description='Export selected attempts as CSV')
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        filename = f"exam_attempts_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            'Student Name', 'Email', 'Phone',
            'Exam', 'Score', 'Correct Answers', 'Total Questions', 'Percentage (%)',
            'Started At', 'Completed At',
        ])

        for attempt in queryset.select_related('user', 'exam'):
            u = attempt.user
            total_q = attempt.total_questions or 0
            pct = round(attempt.total_correct / total_q * 100, 1) if total_q else 0
            writer.writerow([
                u.get_full_name() or u.username,
                u.email,
                getattr(u, 'phone', '') or '',
                attempt.exam.title,
                attempt.score,
                attempt.total_correct,
                total_q,
                pct,
                attempt.started_at.strftime('%Y-%m-%d %H:%M') if attempt.started_at else '',
                attempt.completed_at.strftime('%Y-%m-%d %H:%M') if attempt.completed_at else '',
            ])

        return response

@admin.register(StudentAnswer)
class StudentAnswerAdmin(ModelAdmin):
    list_display = ('attempt', 'question', 'selected_option', 'is_correct')
    list_filter = ('is_correct',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, 'company_id', None):
            return qs.none()
        return qs.filter(attempt__exam__company=request.user.company)
