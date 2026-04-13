from django.contrib import admin
from .models import (
    Exam, Question, QuestionImage,
    SubQuestion, SubQuestionImage,
    Submission, Evaluation, QuestionEvaluation,
    StudentSheetExtractVersion, ExtractedQuestionAnswer
)


# =======================
# 🔹 Question Images Inline
# =======================
class QuestionImageInline(admin.TabularInline):
    model = QuestionImage
    extra = 1


class SubQuestionImageInline(admin.TabularInline):
    model = SubQuestionImage
    extra = 1


# =======================
# 🔹 Questions
# =======================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_number', 'exam', 'marks')
    list_filter = ('exam',)
    search_fields = ('text',)
    inlines = [QuestionImageInline]


# =======================
# 🔹 Sub Questions
# =======================
@admin.register(SubQuestion)
class SubQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'label', 'marks')
    inlines = [SubQuestionImageInline]


# =======================
# 🔹 Exam
# =======================
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'class_assigned', 'date')
    search_fields = ('title',)


# =======================
# 🔹 Submission
# =======================
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'submitted_at')
    list_filter = ('exam',)
    search_fields = ('student__username',)


# =======================
# 🔹 Evaluation
# =======================
class QuestionEvaluationInline(admin.TabularInline):
    model = QuestionEvaluation
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('submission', 'total_score', 'evaluated', 'checked_by_teacher')
    list_filter = ('evaluated', 'checked_by_teacher')
    inlines = [QuestionEvaluationInline]


# =======================
# 🔹 Extracted Answers Inline
# =======================
class ExtractedAnswerInline(admin.TabularInline):
    model = ExtractedQuestionAnswer
    extra = 0
    readonly_fields = ('question_number', 'answer_text')
    can_delete = False


# =======================
# 🔹 Extract Version
# =======================
@admin.register(StudentSheetExtractVersion)
class ExtractVersionAdmin(admin.ModelAdmin):
    list_display = ('submission', 'version_number', 'confidence_score', 'is_best', 'status')
    list_filter = ('is_best', 'status')
    inlines = [ExtractedAnswerInline]


# =======================
# 🔹 Extracted Question Answers
# =======================
@admin.register(ExtractedQuestionAnswer)
class ExtractedAnswerAdmin(admin.ModelAdmin):
    list_display = ('extract_version', 'question_number', 'contains_diagram')
    list_filter = ('contains_diagram', 'contains_math', 'contains_code')
    search_fields = ('answer_text',)


# =======================
# 🔹 Question Evaluation
# =======================
@admin.register(QuestionEvaluation)
class QuestionEvaluationAdmin(admin.ModelAdmin):
    list_display = ('evaluation', 'question', 'score')
    list_filter = ('question',)