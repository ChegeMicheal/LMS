# in views.py or signals.py
from django.contrib.auth.signals import user_logged_out
from django.contrib import messages

def logout_message(sender, request, user, **kwargs):
    messages.success(request, "Logged out successfully.")

user_logged_out.connect(logout_message)