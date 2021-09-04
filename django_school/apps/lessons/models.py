from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from django_school.apps.classes.models import Class

TWO_LESSONS_AT_THE_SAME_TIME_MESSAGE = (
    "The teacher can't have two lessons at the same time."
)
TEACHER_NOT_IN_TEACHERS_GROUP_MESSAGE = "Given teacher is not in teachers group."
STUDENT_CLASS_IS_NOT_LESSON_SESSION_CLASS_MESSAGE = (
    "Student is not in lesson session class."
)


class Subject(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(**kwargs)


class LessonQuerySet(models.QuerySet):
    def with_nested_resources(self):
        return self.select_related("subject", "teacher", "school_class")


class Lesson(models.Model):
    LESSONS_TIMES = [
        ("1", "7:00 - 7:45"),
        ("2", "7:50 - 8:35"),
        ("3", "8:45 - 9:30"),
        ("4", "9:40 - 10:25"),
        ("5", "10:45 - 11:30"),
        ("6", "11:40 - 12:25"),
        ("7", "12:35 - 13:20"),
        ("8", "13:30 - 14:15"),
        ("9", "14:25 - 15:10"),
        ("10", "15:20 - 16:05"),
        ("11", "16:15 - 17:00"),
    ]

    WEEKDAYS = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]

    time = models.CharField(max_length=16, choices=LESSONS_TIMES)
    weekday = models.CharField(max_length=16, choices=WEEKDAYS)
    classroom = models.PositiveIntegerField()
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lessons"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lessons"
    )
    school_class = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="lessons"
    )

    objects = LessonQuerySet.as_manager()

    def __str__(self):
        return f"{self.school_class}: {self.subject.name}, {self.weekday}: {self.time}"

    def clean(self):
        super().clean()

        if Lesson.objects.filter(
            time=self.time, weekday=self.weekday, teacher=self.teacher
        ).exists():
            raise ValidationError(TWO_LESSONS_AT_THE_SAME_TIME_MESSAGE)

        if not self.teacher.is_teacher:
            raise ValidationError(TEACHER_NOT_IN_TEACHERS_GROUP_MESSAGE)


class LessonSessionQuerySet(models.QuerySet):
    def with_nested_resources(self):
        return self.select_related(
            "lesson__teacher",
            "lesson__school_class",
            "lesson__subject",
        )


class LessonSession(models.Model):
    topic = models.CharField(max_length=128, blank=True, null=True)
    date = models.DateField(auto_now_add=True)

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="sessions"
    )
    presences = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Presence")

    objects = LessonSessionQuerySet.as_manager()

    def __str__(self):
        return (
            f"{self.lesson.subject.name} {self.lesson.school_class.number}, {self.date}"
        )

    def get_absolute_url(self):
        return reverse("lessons:session_detail", args=[self.pk])


class Presence(models.Model):
    PRESENCE_STATUSES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("exempt", "Exempt"),
        ("excused", "Excused"),
        ("none", "None"),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson_session = models.ForeignKey(LessonSession, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=PRESENCE_STATUSES, default="none")

    def clean(self):
        super().clean()

        if self.student.school_class != self.lesson_session.lesson.school_class:
            raise ValidationError(STUDENT_CLASS_IS_NOT_LESSON_SESSION_CLASS_MESSAGE)
