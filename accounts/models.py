from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True)  # <- enforce unique at DB level

    def __str__(self):
        return self.username

# ----------------------------
# Auto-assign to Student group
# ----------------------------
@receiver(post_save, sender=User)
def assign_student_group(sender, instance, created, **kwargs):
    if created and instance.role == 'student':
        try:
            student_group = Group.objects.get(name='Student')
            instance.groups.add(student_group)
        except Group.DoesNotExist:
            pass
        
User = get_user_model()

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.username}: {self.otp}"
    
