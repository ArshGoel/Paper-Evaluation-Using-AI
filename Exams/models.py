from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage
from Accounts.models import User, Course, Class
from django.utils.text import slugify

# 🔥 Cloudinary storage instance
cloudinary_storage = MediaCloudinaryStorage()


# ================== UPLOAD PATHS ==================

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


# ================== EXAM ==================

class Exam(models.Model):
    title = models.CharField(max_length=200)

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)

    total_marks = models.IntegerField()
    date = models.DateTimeField()

    question_paper = models.FileField(
        upload_to=question_paper_upload,
        storage=cloudinary_storage,
        null=True,
        blank=True
    )

    answer_key = models.FileField(
        upload_to=answer_key_upload,
        storage=cloudinary_storage,
        null=True,
        blank=True
    )

    instructions = models.TextField(blank=True)

    def __str__(self):
        return self.title


# ================== QUESTIONS ==================

def question_image_upload(instance, filename):
    ext = filename.split('.')[-1]

    exam = instance.question.exam

    title = exam.title.replace(" ", "_")
    class_name = exam.class_assigned.name.replace(" ", "_")
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"
    count = instance.question.images.count() + 1

    return f"exams/{folder}/q{instance.question.question_number}_{count}.{ext}"


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')

    question_number = models.IntegerField()
    text = models.TextField()
    marks = models.IntegerField()
    answer_key = models.TextField(blank=True)
    part = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ('exam', 'question_number')

    def __str__(self):
        return f"Q{self.question_number} - {self.exam.title}"


class QuestionImage(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='images')

    image = models.ImageField(
        upload_to=question_image_upload,
        storage=cloudinary_storage
    )

    def __str__(self):
        return f"Image for Q{self.question.question_number}"


# ================== SUB QUESTIONS ==================

def subquestion_image_upload(instance, filename):
    ext = filename.split('.')[-1]

    exam = instance.sub_question.question.exam

    title = exam.title.replace(" ", "_")
    class_name = exam.class_assigned.name.replace(" ", "_")
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"
    count = instance.sub_question.images.count() + 1

    return f"exams/{folder}/q{instance.sub_question.question.question_number}_{instance.sub_question.label}_{count}.{ext}"


class SubQuestion(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='sub_questions')

    label = models.CharField(max_length=10)
    text = models.TextField()
    marks = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.question} ({self.label})"


class SubQuestionImage(models.Model):
    sub_question = models.ForeignKey(SubQuestion, on_delete=models.CASCADE, related_name='images')

    image = models.ImageField(
        upload_to=subquestion_image_upload,
        storage=cloudinary_storage
    )


# ================== SUBMISSIONS ==================

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
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    file = models.FileField(
        upload_to=submission_upload_path,
        storage=cloudinary_storage
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'exam')

    def __str__(self):
        return f"{self.student} - {self.exam}"


# ================== EVALUATION ==================

class Evaluation(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='evaluation')

    total_score = models.FloatField(null=True, blank=True)
    evaluated = models.BooleanField(default=False)

    ai_raw_response = models.TextField(blank=True)
    checked_by_teacher = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation - {self.submission}"


class QuestionEvaluation(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='question_evaluations')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    score = models.FloatField()
    feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.question} - {self.score}"


# ================== EXTRACT ==================

def extract_upload_path(instance, filename):
    exam = instance.submission.exam
    student = instance.submission.student

    title = slugify(exam.title)
    class_name = slugify(exam.class_assigned.name)
    year = exam.class_assigned.year

    folder = f"{class_name}_{year}_{title}"

    return f"extract/{folder}/student_{student.id}/{filename}"


class StudentSheetExtractVersion(models.Model):
    submission = models.ForeignKey('Submission', on_delete=models.CASCADE, related_name='extract_versions')

    version_number = models.PositiveIntegerField()

    raw_markdown = models.TextField()
    structured_json = models.JSONField(null=True, blank=True)

    json_file = models.FileField(
        upload_to=extract_upload_path,
        storage=cloudinary_storage,
        null=True,
        blank=True
    )

    confidence_score = models.FloatField(null=True, blank=True)
    is_best = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('submission', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"Submission {self.submission.id} - v{self.version_number}"


class ExtractedQuestionAnswer(models.Model):
    extract_version = models.ForeignKey('StudentSheetExtractVersion', on_delete=models.CASCADE, related_name='questions')

    question_number = models.CharField(max_length=20)
    answer_text = models.TextField()

    def __str__(self):
        return f"Q{self.question_number} (v{self.extract_version.version_number})"