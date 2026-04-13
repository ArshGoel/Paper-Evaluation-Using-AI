from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Class, User, Student, Teacher, Course
from Exams.models import Exam, Submission
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login as auth_login
from .models import User, Student
from django.contrib.auth.decorators import login_required

def slogin(request):
    
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "login":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()

            if not username or not password:
                messages.error(request, "Please fill all fields")
                return render(request, "student.html")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.role != "student":
                    messages.error(request, "Please login using Teacher login")
                    return redirect('tlogin')

                auth_login(request, user)
                messages.success(request, "Login successful")
                return redirect('student_dashboard')

            else:
                messages.error(request, "Invalid username or password")
        elif form_type == "signup":
            username = request.POST.get("username", "").strip()
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            password = request.POST.get("password", "").strip()
            email = request.POST.get("email", "").strip()
            if not username or not password:
                messages.error(request, "Username and password are required")
                return render(request, "student.html")

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return render(request, "student.html", {
                    "username": username,
                    "email": email
                })

            # ✅ Create user
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='student'
            )
            user.set_password(password)
            user.save()

            # 🔥 Auto create student profile
            Student.objects.create(
                user=user,
                roll_number=f"STU{user.id}",   # better than TEMP
                branch="CSE",
                year=1,
                dob="2000-01-01"
            )

            auth_login(request, user)
            messages.success(request, "Registration successful")
            return redirect('student_dashboard')

    return render(request, "student.html")

def tlogin(request):
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        # 🔐 LOGIN
        if form_type == "login":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()

            if not username or not password:
                messages.error(request, "Please fill all fields")
                return render(request, "teacher.html")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.role != "teacher":
                    messages.error(request, "Please login using Student login")
                    return redirect('slogin')

                auth_login(request, user)
                messages.success(request, "Login successful")
                return redirect('teacher_dashboard')

            else:
                messages.error(request, "Invalid username or password")

        # 📝 REGISTER
        elif form_type == "signup":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()
            email = request.POST.get("email", "").strip()

            # 🔥 Validation
            if not username or not password:
                messages.error(request, "Username and password are required")
                return render(request, "teacher.html")

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return render(request, "teacher.html", {
                    "username": username,
                    "email": email
                })

            # ✅ Create user
            user = User.objects.create(
                username=username,
                email=email,
                role='teacher'
            )
            user.set_password(password)
            user.save()

            # 🔥 Auto create teacher profile
            Teacher.objects.create(
                user=user,
                department="CSE"
            )

            auth_login(request, user)
            messages.success(request, "Registration successful")
            return redirect('teacher_dashboard')

    return render(request, "teacher.html")

def adminlogin(request):
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "login":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()

            if not username or not password:
                messages.error(request, "Please fill all fields")
                return render(request, "admin.html")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.role == "teacher":
                    messages.error(request, "Please login using Teacher login")
                    return redirect('tlogin')
                elif user.role == "student":
                    messages.error(request, "Please login using Student login")
                    return redirect('slogin')
                auth_login(request, user)
                messages.success(request, "Login successful")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid username or password")
                return render(request, "admin.html")

    return render(request, "admin.html")

def logout_user(request):
    logout(request)
    return redirect("slogin")
