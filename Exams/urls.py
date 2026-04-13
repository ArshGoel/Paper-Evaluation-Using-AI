from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings

urlpatterns = [
    path('teacher/exams/', views.teacher_exams, name='teacher_exams'),
    path('teacher/exam/<int:id>/edit/', views.edit_exam_teacher, name='edit_exam_teacher'),
    path('exam/<int:exam_id>/view-pdf/<str:file_type>/', views.view_pdf, name='view_pdf'),
    path('exam/<int:exam_id>/view-pdf/<str:file_type>/<int:student_id>/',views.view_pdf,name='view_pdf_submission'),
    path('teacher/exam/<int:exam_id>/submissions/',views.teacher_view_submissions,name='view_submissions'),

    path('teacher/extract/<int:submission_id>/',views.extract_student_sheets,name='extract_student_sheets'),
    
    path('teacher/exam/<int:id>/view/', views.view_parsed_exam, name='view_parsed_exam'),
    path('upload-question-image/<int:q_id>/', views.upload_question_image, name='upload_question_image'),
    path('upload-subquestion-image/<int:sub_id>/', views.upload_subquestion_image, name='upload_subquestion_image'),

    path('admin/upload-submission/exam/<int:exam_id>/', views.admin_upload_submission_exam,name='admin_upload_submission_exam'),
    path('extract/view/<int:submission_id>/', views.view_extracted_data, name='view_extract'),
    path(
        'evaluate/<int:submission_id>/',
        views.evaluate_submission_view,
        name='evaluate_submission'
    ),
]
if settings.ENVIRONMENT == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)