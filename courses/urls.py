from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/quiz/', views.start_quiz, name='start_quiz'),
    path('quiz/<int:attempt_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<int:attempt_id>/view/', views.view_quiz, name='view_quiz'),
]
