from django.db import models
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
from cloudinary.models import CloudinaryField

# -------------------
# Courses
# -------------------
class Course(models.Model):
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(groups__name='Instructor')
    )
    title = models.CharField(max_length=200)
    description = models.TextField()

    # ✅ Cloudinary image
    thumbnail = CloudinaryField('image', folder='lms/thumbnails')

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# -------------------
# Lessons
# -------------------
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


# -------------------
# Lesson Media
# -------------------
from django.db import models
from cloudinary.models import CloudinaryField

class LessonMedia(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('image', 'Image'),
    )

    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = CloudinaryField(
        'file',
        resource_type='auto',  # auto-detect video/image/pdf
        folder='lms/lesson_media',
        type='upload',
        blank=True,
        null=True
    )
    external_url = models.URLField(
        "External URL",
        blank=True,
        null=True,
        help_text="Use for videos/PDFs hosted externally or YouTube links"
    )

    def __str__(self):
        return f"{self.lesson.title} ({self.media_type})"

    @property
    def display_name(self):
        if self.external_url:
            name = self.external_url.split("/")[-1].split("?")[0]
        elif self.file:
            name = self.file.public_id.split("/")[-1]
        else:
            name = "unknown"
        if self.media_type == 'pdf':
            return f"{name.upper()}.PDF"
        return name
# -------------------
# Student Enrollments
# -------------------
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    duration_days = models.PositiveIntegerField(default=30)

    @property
    def expires_at(self):
        return self.enrolled_at + timedelta(days=self.duration_days)

    @property
    def is_active(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"
    
# -------------------
# Quiz Models
# -------------------

class Quiz(models.Model):
    lesson = models.OneToOneField('Lesson', on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=10)  # Quiz timer in minutes
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson.title} - Quiz"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=200)
    wrong_answer_1 = models.CharField(max_length=200)
    wrong_answer_2 = models.CharField(max_length=200)
    wrong_answer_3 = models.CharField(max_length=200)

    def all_answers_shuffled(self):
        import random
        answers = [
            self.correct_answer,
            self.wrong_answer_1,
            self.wrong_answer_2,
            self.wrong_answer_3,
        ]
        random.shuffle(answers)
        return answers

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."

class QuizAttempt(models.Model):
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'student'}
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    answers = models.JSONField(default=dict)  # {'question_id': 'selected_answer'}
    score = models.FloatField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded = models.BooleanField(default=False)
    
    question_order = models.JSONField(default=list)

    # 🔥 New field to track when the quiz started
    start_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'quiz')  # Only one attempt allowed

    def is_submitted(self):
        return self.submitted_at is not None

    def grade_quiz(self):
        total = self.quiz.questions.count()
        correct = 0
        for q in self.quiz.questions.all():
            if str(q.id) in self.answers and self.answers[str(q.id)] == q.correct_answer:
                correct += 1
        self.score = round((correct / total) * 100, 2) if total > 0 else 0
        self.graded = True
        self.submitted_at = timezone.now()
        self.save()
        return self.score
    
    