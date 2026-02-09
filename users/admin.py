from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("OCP", {"fields": ("role", "speciality")}),
    )
    list_display = ("username", "email", "role", "speciality", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser")
