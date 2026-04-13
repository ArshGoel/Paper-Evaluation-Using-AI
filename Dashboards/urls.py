from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),

    path('admin/students/', views.manage_students, name='manage_students'),
    path('admin/teachers/', views.manage_teachers, name='manage_teachers'),
    path('admin/courses/', views.manage_courses, name='manage_courses'),
    path('admin/exams/', views.manage_exams, name='manage_exams'),
    path('admin/results/', views.view_results, name='view_results'),
    
    path('students/edit/<int:id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:id>/', views.delete_student, name='delete_student'),

    path('teachers/edit/<int:id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:id>/', views.delete_teacher, name='delete_teacher'),

    path('students/add/', views.add_student, name='add_student'),
    path('teachers/add/', views.add_teacher, name='add_teacher'),

    path('exams/add/', views.add_exam, name='add_exam'),
    path('exams/edit/<int:id>/', views.edit_exam, name='edit_exam'),
    path('exams/delete/<int:id>/', views.delete_exam, name='delete_exam'),

    path('courses/add/', views.add_course, name='add_course'),
    path('courses/edit/<int:id>/', views.edit_course, name='edit_course'),
    path('courses/delete/<int:id>/', views.delete_course, name='delete_course'),

    path('classes/', views.manage_classes, name='manage_classes'),
    path('classes/add/', views.add_class, name='add_class'),
    path('classes/edit/<int:id>/', views.edit_class, name='edit_class'),
    path('classes/delete/<int:id>/', views.delete_class, name='delete_class'),

    path(
        'student/evaluation/<int:submission_id>/',
        views.student_view_evaluation,
        name='student_view_evaluation'
    ),
    path('student/exams/', views.student_exams, name='student_exams')
]
if settings.ENVIRONMENT == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)