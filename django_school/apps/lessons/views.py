import datetime
import os

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from django_school.apps.classes.models import Class
from django_school.apps.common.utils import IsTeacherMixin, teacher_view
from django_school.apps.lessons.forms import LessonSessionForm, PresenceFormSet
from django_school.apps.lessons.models import (
    AttachedFile,
    Lesson,
    LessonSession,
    Subject,
)

User = get_user_model()


class TimetableContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lessons_times"] = Lesson.LESSONS_TIMES
        context["weekdays"] = Lesson.WEEKDAYS

        return context


class ClassTimetableView(TimetableContextMixin, DetailView):
    model = Class
    slug_url_kwarg = "class_slug"
    context_object_name = "school_class"
    template_name = "lessons/class_timetable.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("lessons__subject", "lessons__teacher")
        )


class TeacherTimetableView(TimetableContextMixin, DetailView):
    model = User
    slug_url_kwarg = "teacher_slug"
    context_object_name = "teacher"
    template_name = "lessons/teacher_timetable.html"

    def get_object(self, queryset=None):
        user = super().get_object()

        if not user.is_teacher:
            raise Http404

        return user

    def get_queryset(self):
        return self.model.objects.select_related("address", "teacher_class")


def timetables_list_view(request):
    teachers = User.teachers.order_by("first_name")
    school_classes = Class.objects.order_by("number")

    return render(
        request,
        "lessons/timetable_list.html",
        {"teachers": teachers, "school_classes": school_classes},
    )


class TeacherLessonSessionsListView(LoginRequiredMixin, IsTeacherMixin, ListView):
    model = LessonSession
    template_name = "lessons/teacher_lesson_session_list.html"
    context_object_name = "lesson_sessions"

    def get_queryset(self):
        date = self.request.GET.get("date", datetime.date.today())

        qs = (
            super()
            .get_queryset()
            .select_related(
                "lesson__teacher",
                "lesson__school_class",
                "lesson__subject",
            )
            .filter(lesson__teacher=self.request.user, date=date)
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["date"] = self.request.GET.get("date")

        return context


@login_required
@teacher_view
def lesson_session_detail_view(request, session_pk):
    lesson_session = get_object_or_404(
        LessonSession.objects.select_related(
            "lesson__teacher",
            "lesson__school_class",
            "lesson__subject",
        ).prefetch_related("attached_files"),
        pk=session_pk,
    )

    if request.user != lesson_session.lesson.teacher:
        raise PermissionDenied()

    lesson_session_form = LessonSessionForm(
        request.POST or None, request.FILES or None, instance=lesson_session
    )
    presences_formset = PresenceFormSet(request.POST or None, instance=lesson_session)

    if request.method == "POST":
        if lesson_session_form.is_valid() and presences_formset.is_valid():
            lesson_session_form.save(request_files=request.FILES)
            presences_formset.save()
            messages.success(
                request, "The lesson session has been updated successfully."
            )
            return redirect("lessons:session_list")

    return render(
        request,
        "lessons/lesson_session_detail.html",
        {
            "lesson_session_form": lesson_session_form,
            "lesson_session": lesson_session,
            "presences_formset": presences_formset,
        },
    )


class ClassSubjectListView(LoginRequiredMixin, IsTeacherMixin, ListView):
    model = Subject
    template_name = "lessons/class_subject_list.html"
    context_object_name = "subjects"

    school_class = None

    def dispatch(self, request, *args, **kwargs):
        self.school_class = get_object_or_404(Class, slug=self.kwargs["class_slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .with_does_the_teacher_teach_the_subject_to_the_class(
                teacher=self.request.user, school_class=self.school_class
            )
            .filter(lessons__school_class=self.school_class)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school_class"] = self.school_class

        return context


@login_required
@teacher_view
def attached_file_delete_view(request, pk):
    attached_file = get_object_or_404(
        AttachedFile.objects.select_related("lesson_session__lesson__teacher"), pk=pk
    )

    if attached_file.lesson_session.lesson.teacher != request.user:
        raise PermissionDenied

    if request.method == "POST":
        path = attached_file.file.path
        attached_file.delete()
        os.remove(path)

    return HttpResponse()


@login_required
def student_attendance_summary_view(request, student_slug):
    subject_name = request.GET.get("subject", None)
    subject = (
        get_object_or_404(Subject, name__iexact=subject_name) if subject_name else None
    )
    if subject:
        attendance_params = {"presence__lesson_session__lesson__subject": subject}
    else:
        attendance_params = {}

    student = get_object_or_404(
        User.students.visible_to_user(request.user).with_attendance(
            **attendance_params
        ),
        slug=student_slug,
    )
    subjects = Subject.objects.filter(
        lessons__school_class__students=student
    ).values_list("name", flat=True)

    ctx = {
        "student": student,
        "subject": subject,
        "subjects": subjects,
    }

    return render(request, "lessons/student_attendance.html", ctx)


@login_required
@teacher_view
def class_attendance_summary_view(request, class_slug):
    school_class = get_object_or_404(
        Class.objects.visible_to_user(request.user), slug=class_slug
    )

    students = User.students.filter(school_class=school_class).with_attendance()

    ctx = {
        "students": students,
        "school_class": school_class,
    }

    return render(request, "lessons/class_attendance.html", ctx)
