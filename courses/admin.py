from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth import get_user_model

from .models import Course, Lesson, LessonMedia, Enrollment, Quiz, Question, QuizAttempt


# Custom admin site titles
admin.site.site_header = "LMS Admin"
admin.site.site_title = "LMS Portal"
admin.site.index_title = "Welcome to LMS Admin"

User = get_user_model()


# ==========================================
# LESSON MEDIA INLINE (Cleaner Admin UX)
# ==========================================

class LessonMediaInline(admin.TabularInline):
    model = LessonMedia
    extra = 1
    fields = ('media_type', 'file', 'external_url', 'media_preview')
    readonly_fields = ('media_preview',)

    def media_preview(self, obj):
        url = obj.external_url if obj.external_url else getattr(obj.file, 'url', None)
        if not url:
            return "-"

        # Preview based on type
        if obj.media_type == "image":
            return format_html('<img src="{}" style="height:60px; border-radius:6px;" />', url)

        if obj.media_type == "video":
            return format_html(
                '<video width="150" height="90" controls style="border-radius:6px;">'
                '<source src="{}">'
                '</video>',
                url
            )

        if obj.media_type == "pdf":
            return format_html('<a href="{}" target="_blank">View PDF</a>', url)

        return format_html('<a href="{}" target="_blank">View File</a>', url)

    media_preview.short_description = "Preview"


# ==========================================
# COURSE ADMIN
# ==========================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'instructor',
        'is_published',
        'created_at',
        'thumbnail_preview'
    )
    list_filter = ('is_published', 'instructor')
    search_fields = ('title',)
    readonly_fields = ('thumbnail_preview',)
    ordering = ('-created_at',)

    # 🔒 Instructors only see their courses
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(name="Instructor").exists():
            return qs.filter(instructor=request.user)
        return qs.none()

    # 🔒 Auto-assign instructor
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if request.user.groups.filter(name="Instructor").exists():
                obj.instructor = request.user
        super().save_model(request, obj, form, change)

    # 🔒 Restrict instructor dropdown
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instructor":
            if request.user.is_superuser:
                kwargs["queryset"] = User.objects.filter(groups__name="Instructor")
            else:
                kwargs["queryset"] = User.objects.filter(id=request.user.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 🖼 Cloudinary Thumbnail Preview
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:80px; border-radius:8px; object-fit:cover;" />',
                obj.thumbnail.url
            )
        return "-"
    thumbnail_preview.short_description = "Thumbnail"


# ==========================================
# LESSON ADMIN
# ==========================================

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    ordering = ('course', 'order')
    inlines = [LessonMediaInline]

    # 🔒 Instructors only see lessons of their courses
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(name="Instructor").exists():
            return qs.filter(course__instructor=request.user)
        return qs.none()

    # 🔒 Prevent editing other instructors' lessons
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and obj.course.instructor != request.user:
            return False
        return True


# ==========================================
# ENROLLMENT ADMIN
# ==========================================

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'enrolled_at',
        'duration_days',
        'is_active_status'
    )
    list_filter = ('course',)
    search_fields = ('student__username', 'course__title')
    ordering = ('-enrolled_at',)

    # 🔒 Students cannot access admin
    def has_module_permission(self, request):
        if request.user.groups.filter(name="Student").exists():
            return False
        return True

    def is_active_status(self, obj):
        if obj.is_active:
            return "Active"
        return "Expired"

    is_active_status.short_description = "Status"

from django.utils.html import format_html

# -------------------
# Quiz Admin
# -------------------

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'duration_minutes', 'created_at')
    inlines = [QuestionInline]

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'graded', 'submitted_at')
    search_fields = ('student__username', 'quiz__title')
    readonly_fields = ('score', 'answers', 'graded', 'submitted_at')
    ordering = ('-submitted_at',)