from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UsernameOrEmailAuthenticationForm
from courses.models import Enrollment  
from django.utils import timezone
from django.core.mail import send_mail
from .models import PasswordResetOTP
from .forms import RequestOTPForm, VerifyOTPForm, ResetPasswordForm
from django.contrib.auth import get_user_model
import random

def user_login(request):
    if request.method == "POST":
        form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Redirect based on role or group
            if user.groups.filter(name="Instructor").exists():
                # Instructors go to admin panel
                return redirect("/admin/")
            else:
                # Students go to home page
                return redirect("home")
        else:
            messages.error(request, "Invalid username/email or password.")
    else:
        form = UsernameOrEmailAuthenticationForm()

    return render(request, "login.html", {"form": form})

User = get_user_model()

@login_required
def my_profile(request):
    user = request.user
    # Fetch enrolled courses correctly
    enrolled_courses = Enrollment.objects.filter(student=user).select_related('course')
    
    context = {
        'user': user,
        'enrolled_courses': enrolled_courses,
    }
    return render(request, 'profile.html', context)

from .forms import StudentSignUpForm

def register(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. You can now log in.")
            return redirect('accounts:login')
    else:
        form = StudentSignUpForm()
    
    return render(request, 'register.html', {'form': form})

User = get_user_model()

# Step 1: Request OTP
def forgot_password(request):
    if request.method == "POST":
        form = RequestOTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                otp_code = str(random.randint(100000, 999999))
                
                # Save OTP
                PasswordResetOTP.objects.create(user=user, otp=otp_code)

                # Send email (configure EMAIL_BACKEND in settings.py)
                send_mail(
                    'Your OTP for password reset',
                    f'Hello {user.username},\n\nYour OTP is {otp_code}. It expires in 10 minutes.',
                    'no-reply@example.com',
                    [user.email],
                    fail_silently=False,
                )
                request.session['reset_user_id'] = user.id
                return redirect('accounts:verify_otp')
            except User.DoesNotExist:
                messages.error(request, "No user found with that email.")
    else:
        form = RequestOTPForm()
    return render(request, 'forgot_password.html', {'form': form})

# Step 2: Verify OTP
def verify_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('accounts:forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp_input, is_used=False).first()
            if otp_obj and not otp_obj.is_expired():
                otp_obj.is_used = True
                otp_obj.save()
                request.session['otp_verified'] = True
                return redirect('accounts:reset_password')
            else:
                messages.error(request, "Invalid or expired OTP.")
    else:
        form = VerifyOTPForm()
    return render(request, 'verify_otp.html', {'form': form})

# Step 3: Reset Password
def reset_password(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified', False)
    if not user_id or not otp_verified:
        return redirect('accounts:forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = ResetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password reset successful. You can now log in.")
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)
            return redirect('accounts:login')
    else:
        form = ResetPasswordForm(user=user)

    return render(request, 'reset_password.html', {'form': form})

from .forms import CustomPasswordChangeForm
from django.contrib.auth import update_session_auth_hash



@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            update_session_auth_hash(request, request.user)

            messages.success(request, "Password changed successfully. Please log in again.")
            return redirect('accounts:login')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'change_password.html', {'form': form})