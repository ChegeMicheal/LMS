from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import SetPasswordForm

User = get_user_model()

class RequestOTPForm(forms.Form):
    email = forms.EmailField(label="Enter your account email")

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(max_length=6, label="Enter OTP")

class ResetPasswordForm(SetPasswordForm):
    # inherits new_password1 and new_password2
    pass

User = get_user_model()

class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'autofocus': True})
    )

    def clean(self):
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Try to get user by username or email
            user = None
            if User.objects.filter(username=username_or_email).exists():
                user = authenticate(
                    self.request,
                    username=username_or_email,
                    password=password
                )
            elif User.objects.filter(email=username_or_email).exists():
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(
                    self.request,
                    username=user_obj.username,  # authenticate by username
                    password=password
                )

            if user is None:
                raise forms.ValidationError("Invalid username/email or password.")
            else:
                self.user_cache = user

        return self.cleaned_data
    
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class StudentSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
        return user
    
from django.contrib.auth import password_validation

class CustomPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Old Password"
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="New Password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm New Password"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Old password is incorrect.")
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("New passwords do not match.")

            if old_password and new_password1 == old_password:
                raise forms.ValidationError("New password must be different from old password.")

            password_validation.validate_password(new_password1, self.user)

        return cleaned_data