from django.db import models
from django.core.files.storage import FileSystemStorage
from Accounts.models import User, Teacher, Student
from Accounts.models import Course, Class
import os
import os
from django.db import models
import os
import json
from django.conf import settings
from django.utils.text import slugify

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name

def question_paper_upload(instance, filename):
    ext = filename.split('.')[-1]

    title = instance.title.replace(" ", "_")
    class_name = instance.class_assigned.name.replace(" ", "_")
    year = instance.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    return f"exams/{folder}/question_paper.{ext}"

def answer_key_upload(instance, filename):
    ext = filename.split('.')[-1]

    title = instance.title.replace(" ", "_")
    class_name = instance.class_assigned.name.replace(" ", "_")
    year = instance.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    return f"exams/{folder}/answer_key.{ext}"

class Exam(models.Model):
    title = models.CharField(max_length=200)

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)

    total_marks = models.IntegerField()
    date = models.DateTimeField()

    question_paper = models.FileField(
        upload_to=question_paper_upload,
        null=True,
        blank=True
    )

    answer_key = models.FileField(
        upload_to=answer_key_upload,
        null=True,
        blank=True
    )
    instructions = models.TextField(blank=True)

    def __str__(self):
        return self.title

#Questions
def question_image_upload(instance, filename):
    ext = filename.split('.')[-1]

    # ✅ correct chain
    question = instance.question
    exam = question.exam

    title = exam.title.replace(" ", "_")
    class_name = exam.class_assigned.name.replace(" ", "_")
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    # avoid None issue
    count = question.images.count() + 1

    return f"exams/{folder}/q{question.question_number}_{count}.{ext}"

class Question(models.Model):
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='questions'
    )

    question_number = models.IntegerField()   # 🔥 IMPORTANT
    text = models.TextField()
    marks = models.IntegerField()
    answer_key = models.TextField(blank=True)
    part = models.CharField(max_length=10, blank=True)  # Part A / B

    def __str__(self):
        return f"Q{self.question_number} - {self.exam.title}"
    class Meta:
        unique_together = ('exam', 'question_number')

class QuestionImage(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=question_image_upload)

    def __str__(self):
        return f"Image for Q{self.question.question_number}"
#Questions

#SubQuestions
def subquestion_image_upload(instance, filename):
    ext = filename.split('.')[-1]

    sub_q = instance.sub_question
    question = sub_q.question
    exam = question.exam

    title = exam.title.replace(" ", "_")
    class_name = exam.class_assigned.name.replace(" ", "_")
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    count = sub_q.images.count() + 1

    return f"exams/{folder}/q{question.question_number}_{sub_q.label}_{count}.{ext}"

class SubQuestion(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='sub_questions'
    )
    label = models.CharField(max_length=10)  # a, b, i, ii
    text = models.TextField()
    marks = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.question} ({self.label})"

class SubQuestionImage(models.Model):
    sub_question = models.ForeignKey(SubQuestion, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=subquestion_image_upload)
#SubQuestions

def submission_upload_path(instance, filename):
    ext = filename.split('.')[-1]

    exam = instance.exam
    student = instance.student

    title = exam.title.replace(" ", "_")
    class_name = exam.class_assigned.name.replace(" ", "_")
    year = exam.class_assigned.year
    username = student.username.replace(" ", "_")

    folder = f"{class_name}_{year}_{title}"

    return f"submissions/{folder}/{username}.{ext}"

class Submission(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    # Answer Sheet Upload
    file = models.FileField(
        upload_to=submission_upload_path,
    )
    
    submitted_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.student} - {self.exam}"
    
    class Meta:
        unique_together = ('student', 'exam')

class Evaluation(models.Model):
    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name='evaluation'
    )

    total_score = models.FloatField(null=True, blank=True)
    evaluated = models.BooleanField(default=False)

    ai_raw_response = models.TextField(blank=True)

    checked_by_teacher = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation - {self.submission}"

class QuestionEvaluation(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name='question_evaluations'
    )

    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    score = models.FloatField()
    feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.question} - {self.score}"
    
def extract_upload_path(instance, filename):
    submission = instance.submission
    exam = submission.exam
    student = submission.student

    title = slugify(exam.title)

    # ✅ FIXED
    class_name = slugify(exam.class_assigned.name)
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    return f"extract/{folder}/student_{student.id}/{filename}"

class StudentSheetExtractVersion(models.Model):
    submission = models.ForeignKey(
        'Submission',
        on_delete=models.CASCADE,
        related_name='extract_versions'
    )

    version_number = models.PositiveIntegerField()

    raw_markdown = models.TextField()
    structured_json = models.JSONField(null=True, blank=True)

    json_file = models.FileField(upload_to=extract_upload_path, null=True, blank=True)

    primary_language = models.CharField(max_length=50, null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    is_best = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    model_used = models.CharField(max_length=100, blank=True, null=True)
    processing_time_ms = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('processing', 'Processing')
        ],
        default='success'
    )

    class Meta:
        unique_together = ('submission', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"Submission {self.submission.id} - v{self.version_number}"

    @staticmethod
    def update_best_version(submission):
        versions = submission.extract_versions.all()

        if not versions.exists():
            return None

        # ignore null confidence
        versions = versions.exclude(confidence_score__isnull=True)

        if not versions.exists():
            return None

        best = versions.order_by('-confidence_score', '-version_number').first()

        # 🔥 Reset all in ONE query
        submission.extract_versions.update(is_best=False)

        # 🔥 Set best in ONE query (NO save issues)
        StudentSheetExtractVersion.objects.filter(id=best.id).update(is_best=True)

        return best

    @staticmethod
    def get_next_version(submission):
        last = submission.extract_versions.order_by('-version_number').first()
        return last.version_number + 1 if last else 1
    
class ExtractedQuestionAnswer(models.Model):
    extract_version = models.ForeignKey(
        'StudentSheetExtractVersion',
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_number = models.CharField(max_length=20)  
    answer_text = models.TextField()

    contains_math = models.BooleanField(default=False)
    contains_diagram = models.BooleanField(default=False)
    contains_code = models.BooleanField(default=False)

    class Meta:
        ordering = ['question_number']

    def __str__(self):
        return f"Q{self.question_number} (v{self.extract_version.version_number})"