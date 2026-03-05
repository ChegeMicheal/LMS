from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),    
    path('profile/', views.my_profile, name='my_profile'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
]