from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LessonMedia, Enrollment,Quiz, Question, QuizAttempt
from datetime import timedelta
from django.utils import timezone

from django.db.models import Count

def home(request):
    # Recently added courses (latest 6)
    recent_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:6]

    # Most enrolled courses (annotate with count)
    most_enrolled_courses = Course.objects.filter(is_published=True) \
        .annotate(enrollment_count=Count('enrollment')) \
        .order_by('-enrollment_count')[:6]

    context = {
        'recent_courses': recent_courses,
        'most_enrolled_courses': most_enrolled_courses,
    }
    return render(request, 'home.html', context)

@login_required
def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, 'course_list.html', {'courses': courses})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_published=True)

    # -----------------------------
    # Auto-enroll student if not enrolled
    # -----------------------------
    if request.user.role == 'student':
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'duration_days': 30}
        )
        # Optional: update enrolled_at if already exists
        if not created and enrollment.expires_at < timezone.now():
            enrollment.enrolled_at = timezone.now()
            enrollment.save()

    lessons = course.lesson_set.all()
    return render(request, 'course_detail.html', {
        'course': course,
        'lessons': lessons,
        'enrolled': request.user.role=='student' and Enrollment.objects.filter(student=request.user, course=course, enrolled_at__lte=timezone.now()).exists()
    })
    
from urllib.parse import urlparse, parse_qs
from cloudinary.utils import cloudinary_url

@login_required
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(course.lesson_set, id=lesson_id)

    # Check enrollment
    if request.user.role == 'student':
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        if not enrollment or not enrollment.is_active:
            return redirect('courses:course_detail', course_id=course.id)

    # Prepare quizzes with status
    quizzes_with_status = []

    try:
        quiz = lesson.quiz  # OneToOneField access
        status = "Not Attempted"
        status_class = "not-attempted"

        if request.user.role == 'student':
            attempt = quiz.attempts.filter(student=request.user).first()

            if attempt:
                if attempt.submitted_at:
                    status = "Attempted"
                    status_class = "attempted"
                else:
                    status = "In Progress"
                    status_class = "in-progress"

        quizzes_with_status.append({
            'quiz': quiz,
            'status': status,
            'status_class': status_class
        })

    except Quiz.DoesNotExist:
        # No quiz for this lesson
        pass
        
    # Categorized media lists
    youtube_videos = []
    uploaded_videos = []
    pdf_files = []
    images = []

    for media in lesson.media.all():
        file_url = getattr(media.file, 'url', None)
        signed_url = None

        # Sign Cloudinary video if needed
        if media.media_type == 'video' and file_url:
            signed_url, _ = cloudinary_url(
                media.file.public_id,
                resource_type='video',
                sign=True
            )

        external_url = media.external_url or None

        # Detect YouTube
        is_youtube = False
        youtube_id = None
        embed_url = None
        if external_url:
            parsed = urlparse(external_url)
            if "youtu.be" in parsed.netloc:
                is_youtube = True
                youtube_id = parsed.path.strip("/")
            elif "youtube.com" in parsed.netloc:
                is_youtube = True
                if parsed.path == "/watch":
                    youtube_id = parse_qs(parsed.query).get("v", [None])[0]
                elif "/embed/" in parsed.path:
                    youtube_id = parsed.path.split("/embed/")[-1]
            if youtube_id:
                youtube_id = youtube_id.split("?")[0].split("&")[0]
                site_origin = request.build_absolute_uri("/")[:-1]
                embed_url = f"https://www.youtube.com/embed/{youtube_id}?rel=0&modestbranding=1&origin={site_origin}"

        # Detect direct MP4 link
        is_direct_video = external_url and external_url.lower().endswith(".mp4")

        media_dict = {
            'id': media.id,
            'file_url': signed_url or file_url,
            'external_url': external_url,
            'display_name': getattr(media, 'display_name', file_url.split("/")[-1] if file_url else "File"),
            'is_youtube': is_youtube,
            'youtube_embed_url': embed_url,
            'is_direct_video': is_direct_video,
        }

        # Categorize
        if media.media_type == 'video':
            if is_youtube and embed_url:
                youtube_videos.append(media_dict)
            else:
                uploaded_videos.append(media_dict)
        elif media.media_type == 'pdf':
            pdf_files.append(media_dict)
        elif media.media_type == 'image':
            images.append(media_dict)

    return render(request, 'lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'youtube_videos': youtube_videos,
        'uploaded_videos': uploaded_videos,
        'pdf_files': pdf_files,
        'images': images,        
        'enrolled': request.user.role == 'student' and enrollment is not None,
        'quizzes_with_status': quizzes_with_status
    })
    
import random
from django.utils import timezone

@login_required
def start_quiz(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not hasattr(lesson, "quiz"):
        return redirect("courses:lesson_detail",
                        course_id=lesson.course.id,
                        lesson_id=lesson.id)

    quiz = lesson.quiz

    attempt, created = QuizAttempt.objects.get_or_create(
        student=request.user,
        quiz=quiz
    )

    if attempt.graded:
        return redirect("courses:view_quiz", attempt_id=attempt.id)

    # First-time setup
    if created or not attempt.question_order:
        question_ids = list(quiz.questions.values_list("id", flat=True))
        random.shuffle(question_ids)
        attempt.question_order = question_ids
        attempt.start_time = timezone.now()
        attempt.save()

    # Server-side timer enforcement
    elapsed = (timezone.now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, quiz.duration_minutes * 60 - int(elapsed))

    # If timeout, grade immediately and redirect to lesson
    if remaining_seconds <= 0:
        attempt.grade_quiz()
        return redirect("courses:lesson_detail",
                        course_id=lesson.course.id,
                        lesson_id=lesson.id)

    # Prepare questions
    question_list = []
    saved_answers = attempt.answers or {}
    for q_id in attempt.question_order:
        q = quiz.questions.get(id=q_id)
        question_list.append({
            "id": q.id,
            "question_text": q.question_text,
            "answers": q.all_answers_shuffled(),
            "selected_answer": saved_answers.get(str(q.id), "")
        })

    return render(request, "quiz.html", {
        "quiz": quiz,
        "questions": question_list,
        "remaining_seconds": remaining_seconds,
        "attempt": attempt,
    })


@login_required
def submit_quiz(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        id=attempt_id,
        student=request.user
    )

    quiz = attempt.quiz
    lesson = quiz.lesson
    course = lesson.course

    # Already graded → redirect to lesson
    if attempt.graded:
        return redirect('courses:lesson_detail', 
                        course_id=course.id,
                        lesson_id=lesson.id)

    # Server-side time enforcement
    elapsed = (timezone.now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, quiz.duration_minutes * 60 - int(elapsed))
    timeout_submit = request.POST.get("timeout_submit") == "1"

    # Handle timeout / forced submission
    if remaining_seconds <= 0 or timeout_submit:
        # Save answers if any
        answers = {}
        for key, value in request.POST.items():
            if key.startswith("question_"):
                qid = key.split("_")[1]
                answers[qid] = value
        attempt.answers = answers
        attempt.save()
        attempt.grade_quiz()  # Auto-grade
        # Redirect back to lesson page
        return redirect('courses:lesson_detail', 
                        course_id=course.id,
                        lesson_id=lesson.id)

    # Only handle POST for regular submission / preview
    if request.method == "POST":
        # Save submitted answers
        answers = {}
        for key, value in request.POST.items():
            if key.startswith("question_"):
                qid = key.split("_")[1]
                answers[qid] = value
        attempt.answers = answers
        attempt.save()

        # Confirm & Grade button pressed
        if "confirm_submit" in request.POST:
            attempt.grade_quiz()
            return redirect('courses:lesson_detail', 
                            course_id=course.id,
                            lesson_id=lesson.id)

        # Preview / Review button pressed
        if "preview" in request.POST:
            questions = []
            for q_id in attempt.question_order:
                q = quiz.questions.get(id=q_id)
                questions.append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "answers": q.all_answers_shuffled(),
                    "selected_answer": answers.get(str(q.id), "")
                })
            return render(request, "quiz_submit_confirm.html", {
                "attempt": attempt,
                "questions": questions,
                "remaining_seconds": remaining_seconds,
            })

    # Fallback: restart quiz
    return redirect('courses:start_quiz', lesson_id=lesson.id)

@login_required
def view_quiz(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz__lesson__course')
                           .prefetch_related('quiz__questions'),
        id=attempt_id,
        student=request.user
    )

    quiz = attempt.quiz
    lesson = quiz.lesson
    course = lesson.course

    questions = []
    for q in quiz.questions.all():
        questions.append({
            'id': q.id,
            'question_text': q.question_text,
            'correct_answer': q.correct_answer,
            'student_answer': attempt.answers.get(str(q.id)),
            'answers': q.all_answers_shuffled()
        })

    return render(request, 'quiz_view.html', {
        'attempt': attempt,
        'questions': questions,
        'lesson': lesson,   # ✅ now available
        'course': course,   # ✅ now available
    })