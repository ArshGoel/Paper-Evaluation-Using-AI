from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Student, Teacher, Course, Class,
)


class UserAdmin(BaseUserAdmin):

    # Fields when editing
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone')}),
    )

    # 🔥 Fields when adding user (NO password2)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'password',   # ✅ single password field
                'role',
                'phone',
                'email',
                'first_name',
                'last_name',
            ),
        }),
    )

    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')

    # 🔥 THIS IS THE KEY (no form needed)
    def save_model(self, request, obj, form, change):
        if not change:  # when creating new user
            obj.set_password(obj.password)  # hash password
        super().save_model(request, obj, form, change)


admin.site.register(User, UserAdmin)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'branch', 'year', 'attendance')
    search_fields = ('user__username', 'roll_number', 'branch')
    list_filter = ('branch', 'year')

admin.site.register(Student, StudentAdmin)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    filter_horizontal = ('courses', 'classes')

admin.site.register(Teacher, TeacherAdmin)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

admin.site.register(Course, CourseAdmin)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'year')
