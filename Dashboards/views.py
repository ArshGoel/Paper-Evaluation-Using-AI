from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from Accounts.models import Class, User, Student, Teacher, Course
from Exams.models import Exam, Submission
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from Exams.models import Evaluation, QuestionEvaluation
# Dashboard
@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('slogin')

    student = request.user.student_profile
    subjects = Course.objects.all()
    exams = Exam.objects.filter(class_assigned__year=student.year)
    submissions = Submission.objects.filter(student=request.user)
    attendance = student.attendance
    cgpa = student.cgpa
    total_exams = exams.count()
    branch = student.branch
    submitted_count = submissions.count()

    context = {
        "student": student,
        "subjects": subjects,
        "exams": exams,
        "submissions": submissions,
        "attendance_pct": attendance,
        "cgpa": cgpa,
        "branch": branch,
        "total_exams": total_exams,
        "submitted_count": submitted_count,
    }

    return render(request, "student/student_dashboard.html", context)

@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        return redirect('tlogin')

    teacher = request.user.teacher_profile
    courses = teacher.courses.all()
    classes = teacher.classes.all()
    exams = Exam.objects.filter()
    total_exams = exams.count() 

    context = {
        "teacher": teacher,
        "courses": courses,
        "classes": classes,
        "exams": exams,
        "total_exams": total_exams,
    }

    return render(request, 'teacher/teacher_dashboard.html', context)

from django.db.models import Avg

@login_required
@login_required
def admin_dashboard(request):
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_exams = Exam.objects.count()

    total_submissions = Submission.objects.count()
    evaluated_submissions = Evaluation.objects.filter(evaluated=True).count()

    avg_score = Evaluation.objects.aggregate(avg=Avg('total_score'))['avg']

    context = {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_exams": total_exams,
        "total_submissions": total_submissions,
        "evaluated_submissions": evaluated_submissions,
        "pending_evaluations": total_submissions - evaluated_submissions,
        "avg_score": round(avg_score, 2) if avg_score else 0,
    }

    return render(request, "admin/admin_dashboard.html", context)
# Dashboard

# Admin Management
def add_student(request):
    if request.method == "POST":
        # USER DATA
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")

        first_name = request.POST.get("firstname")
        last_name = request.POST.get("lastname")
        # STUDENT DATA
        roll_number = request.POST.get("roll_number")
        branch = request.POST.get("branch")
        year = request.POST.get("year")
        dob = request.POST.get("dob")
        student_class_id = request.POST.get("student_class")

        profile_image = request.FILES.get("profile_image")

        # 🔥 Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role="student",
            phone=phone,
            first_name=first_name,
            last_name=last_name
        )

        # 🔥 Create Student Profile
        Student.objects.create(
            user=user,
            roll_number=roll_number,
            branch=branch,
            year=year,
            dob=dob,
            student_class_id=student_class_id,
            profile_image=profile_image if profile_image else "profile/student.png"
        )

        messages.success(request, "Student added successfully!")
        return redirect("manage_students")

    return render(request, "admin/manage_students/add_student.html", {
        "classes": Class.objects.all()
    })

def add_teacher(request):
    if request.method == "POST":
        # USER DATA
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")

        # TEACHER DATA
        department = request.POST.get("department")
        profile_image = request.FILES.get("profile_image")

        courses = request.POST.getlist("courses")
        classes = request.POST.getlist("classes")

        # 🔥 Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role="teacher",
            phone=phone
        )

        # 🔥 Create Teacher Profile
        teacher = Teacher.objects.create(
            user=user,
            department=department,
            profile_image=profile_image if profile_image else "profile/teacher.png"
        )

        # 🔥 Many-to-Many
        teacher.courses.set(courses)
        teacher.classes.set(classes)

        messages.success(request, "Teacher added successfully!")
        return redirect("manage_teachers")

    return render(request, "admin/manage_teachers/add_teacher.html", {
        "courses": Course.objects.all(),
        "classes": Class.objects.all()
    })

def manage_students(request):
    students = Student.objects.select_related('user').all()
    return render(request, "admin/manage_students/manage_students.html", {"students": students})

def edit_student(request, id):
    student = get_object_or_404(Student, id=id)
    user = student.user

    if request.method == "POST":
        # User fields
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.phone = request.POST.get("phone")

        user.first_name = request.POST.get("firstname")
        user.last_name = request.POST.get("lastname")
        # Student fields
        student.roll_number = request.POST.get("roll_number")
        student.branch = request.POST.get("branch")
        student.year = request.POST.get("year")

        if request.FILES.get("profile_image"):
            student.profile_image = request.FILES.get("profile_image")

        user.save()
        student.save()
        messages.success(request, "Student updated successfully!")
        return redirect("manage_students")

    return render(request, "admin/manage_students/edit_student.html", {
        "student": student
    })

def delete_student(request, id):
    student = get_object_or_404(Student, id=id)
    student.user.delete()

    return redirect("manage_students")

def edit_teacher(request, id):
    teacher = get_object_or_404(Teacher, id=id)
    user = teacher.user

    if request.method == "POST":
        # User fields
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.phone = request.POST.get("phone")

        # Teacher fields
        teacher.department = request.POST.get("department")

        # Profile Image
        if request.FILES.get("profile_image"):
            teacher.profile_image = request.FILES.get("profile_image")

        # Many-to-Many (Courses & Classes)
        teacher.courses.set(request.POST.getlist("courses"))
        teacher.classes.set(request.POST.getlist("classes"))

        user.save()
        teacher.save()
        messages.success(request, "Teacher updated successfully!")
        return redirect("manage_teachers")

    return render(request, "admin/manage_teachers/edit_teacher.html", {
        "teacher": teacher,
        "courses": Course.objects.all(),
        "classes": Class.objects.all(),
    })

def delete_teacher(request, id):
    teacher = get_object_or_404(Teacher, id=id)

    if request.method == "POST":
        teacher.user.delete()  # deletes teacher + user (CASCADE)

    return redirect("manage_teachers")

def manage_teachers(request):
    teachers = Teacher.objects.select_related('user').all()
    return render(request, "admin/manage_teachers/manage_teachers.html", {"teachers": teachers})

def manage_exams(request):
    exams = Exam.objects.all()
    return render(request, "admin/manage_exams/manage_exams.html", {"exams": exams})

def add_exam(request):
    if request.method == "POST":
        title = request.POST.get("title")
        course_id = request.POST.get("course")
        class_id = request.POST.get("class_assigned")
        total_marks = request.POST.get("total_marks")
        date = request.POST.get("date")
        Exam.objects.create(
            title=title,
            course_id=course_id,
            class_assigned_id=class_id,
            total_marks=total_marks,
            date=date,
        )
        messages.success(request, "Exam created successfully!")
        return redirect("manage_exams")
    return render(request, "admin/manage_exams/add_exam.html", {
        "courses": Course.objects.all(),
        "classes": Class.objects.all(),
    })

def edit_exam(request, id):
    exam = Exam.objects.get(id=id)

    if request.method == "POST":
        exam.title = request.POST.get('title')
        exam.course_id = request.POST.get('course')
        exam.class_assigned_id = request.POST.get('class_assigned')
        exam.total_marks = request.POST.get('total_marks')
        exam.date = request.POST.get('date')

        exam.save()
        return redirect('manage_exams')

    teachers = Teacher.objects.all()
    courses = Course.objects.all()
    classes = Class.objects.all()

    return render(request, 'admin/manage_exams/edit_exam.html', {
        'exam': exam,
        'teachers': teachers,
        'courses': courses,
        'classes': classes
    })

def delete_exam(request, id):
    exam = get_object_or_404(Exam, id=id)
    exam.delete()
    return redirect("manage_exams")

def manage_courses(request):
    courses = Course.objects.all()
    return render(request, "admin/manage_courses/manage_courses.html", {"courses": courses})

def add_course(request):
    if request.method == "POST":
        name = request.POST.get("name")
        code = request.POST.get("code")

        Course.objects.create(name=name, code=code)

        messages.success(request, "Course added successfully!")
        return redirect("manage_courses")

    return render(request, "admin/manage_courses/add_course.html")

def edit_course(request, id):
    course = get_object_or_404(Course, id=id)

    if request.method == "POST":
        course.name = request.POST.get("name")
        course.code = request.POST.get("code")
        course.save()

        return redirect("manage_courses")

    return render(request, "admin/manage_courses/edit_course.html", {"course": course})

def delete_course(request, id):
    course = get_object_or_404(Course, id=id)
    course.delete()
    return redirect("manage_courses")

def manage_classes(request):
    classes = Class.objects.all()
    return render(request, "admin/manage_classes/manage_classes.html", {"classes": classes})

def add_class(request):
    if request.method == "POST":
        name = request.POST.get("name")
        year = request.POST.get("year")

        Class.objects.create(name=name, year=year)

        return redirect("manage_classes")

    return render(request, "admin/manage_classes/add_class.html")

def edit_class(request, id):
    cls = get_object_or_404(Class, id=id)

    if request.method == "POST":
        cls.name = request.POST.get("name")
        cls.year = request.POST.get("year")
        cls.save()

        return redirect("manage_classes")

    return render(request, "admin/manage_classes/edit_class.html", {"cls": cls})

def delete_class(request, id):
    cls = get_object_or_404(Class, id=id)
    cls.delete()
    return redirect("manage_classes")

def view_results(request):
    submissions = Submission.objects.select_related(
        'student', 'exam', 'evaluation'
    ).all()

    return render(request, "admin/view_results.html", {
        "submissions": submissions
    })
# Admin Management


def student_view_evaluation(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    # optional: restrict access
    if submission.student != request.user:
        return redirect('dashboard')

    evaluation = getattr(submission, 'evaluation', None)

    if not evaluation or not evaluation.evaluated:
        messages.warning(request, "Evaluation not available yet")
        return redirect('student_dashboard')

    question_evals = evaluation.question_evaluations.select_related('question')

    return render(request, 'student/view_evaluation.html', {
        'submission': submission,
        'evaluation': evaluation,
        'question_evals': question_evals
    })

def student_exams(request):
    submissions = Submission.objects.filter(student=request.user).select_related('exam')

    return render(request, 'student/student_exams.html', {
        'submissions': submissions
    })