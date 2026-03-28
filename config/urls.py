from django.contrib import admin
from django.urls import path, include
from courses import views as course_views  # ✅ imported correctly
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views

urlpatterns = [
    path('', course_views.home, name='home'),  # Home page
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('courses/', include('courses.urls', namespace='courses')),
    path('accounts/login/', accounts_views.user_login, name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/accounts/login/'), name='logout'),
]
