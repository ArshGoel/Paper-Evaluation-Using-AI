from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage

cloudinary_storage = MediaCloudinaryStorage()

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    def __str__(self):
        return f"{self.username} - {self.role}"
    
class Class(models.Model):
    name = models.CharField(max_length=50)  # e.g., CSE-A
    year = models.IntegerField()
    def __str__(self):
        return f"{self.name} - Year {self.year}"
    
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=20)
    profile_image = models.ImageField(
        upload_to='profile/',
        storage=cloudinary_storage,
        blank=True,
        null=True
    )
    student_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True) 
    course = models.CharField(max_length=50, default="BTECH")
    branch = models.CharField(max_length=50)
    YEAR_CHOICES = [
        (1, "1st Year"),
        (2, "2nd Year"),
        (3, "3rd Year"),
        (4, "4th Year"),
    ]
    year = models.IntegerField(choices=YEAR_CHOICES)
    # Personal Info
    dob = models.DateField()
    # Performance
    attendance = models.FloatField(default=88.0)
    cgpa = models.FloatField(default=8.8)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.user.username} ({self.roll_number})"
      
class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    def __str__(self):
        return self.name
     
class Teacher(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='teacher_profile'
    )
    profile_image = models.ImageField(
        upload_to='profile/',
        storage=cloudinary_storage,
        blank=True,
        null=True
    )
    department = models.CharField(max_length=100)
    courses = models.ManyToManyField(Course, related_name='teachers')
    classes = models.ManyToManyField(Class, related_name='teachers')

    def __str__(self):
        return self.user.username
 