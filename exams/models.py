from django.db import models
from django.conf import settings
from core.models import Category
from accounts.models import Company

class Question(models.Model):
    OPTION_CHOICES = (
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exams_question'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"{self.question_text[:50]}..."

class Exam(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    categories = models.ManyToManyField(Category, related_name='exams')
    total_questions = models.PositiveIntegerField(help_text="Number of random questions to pick from selected categories")
    marks_per_question = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    time_limit_mins = models.PositiveIntegerField(help_text="Time limit in minutes")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exams_exam'
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'

    def __str__(self):
        return self.title

class ExamAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    score = models.DecimalField(max_digits=7, decimal_places=2, default=0.0)
    total_correct = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    answers_snapshot = models.JSONField(default=list, blank=True, help_text="Snapshot of questions and student answers at submission time")
    
    class Meta:
        db_table = 'exams_examattempt'
        verbose_name = 'Exam Attempt'
        verbose_name_plural = 'Exam Attempts'

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.score}"

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, choices=Question.OPTION_CHOICES)
    is_correct = models.BooleanField()

    class Meta:
        db_table = 'exams_studentanswer'
        verbose_name = 'Student Answer'
        verbose_name_plural = 'Student Answers'

    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.id}"
