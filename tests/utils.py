from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.text import slugify

from django_school.apps.classes.models import Class
from django_school.apps.common.models import Address
from django_school.apps.grades.models import Grade, GradeCategory
from django_school.apps.lessons.models import Lesson, LessonSession, Presence, Subject

User = get_user_model()


class UsersMixin:
    fixtures = ["groups.json"]
    DEFAULT_USERNAME = "username"
    DEFAULT_PASSWORD = "password"
    TEACHER_USERNAME = "teacher"
    STUDENT_USERNAME = "student"

    @classmethod
    def create_user(cls, username=DEFAULT_USERNAME, **kwargs):
        if "slug" not in kwargs:
            kwargs["slug"] = slugify(username)

        return User.objects.create_user(
            username=username,
            password=cls.DEFAULT_PASSWORD,
            **kwargs,
        )

    def login(self, user):
        return self.client.login(username=user.username, password=self.DEFAULT_PASSWORD)

    def logout(self):
        self.client.logout()

    @staticmethod
    def add_user_to_group(user, group_name):
        group = Group.objects.get(name=group_name)
        user.groups.add(group)

    @classmethod
    def create_teacher(cls, username=TEACHER_USERNAME, **kwargs):
        teacher = cls.create_user(username, **kwargs)
        cls.add_user_to_group(teacher, "teachers")

        return teacher

    @classmethod
    def create_student(cls, username=STUDENT_USERNAME, **kwargs):
        student = cls.create_user(username, **kwargs)
        cls.add_user_to_group(student, "students")

        return student


class ClassesMixin:
    DEFAULT_NUMBER = "1a"

    @staticmethod
    def create_class(number=DEFAULT_NUMBER, tutor=None, **kwargs):
        return Class.objects.create(number=number, tutor=tutor, **kwargs)


class CommonMixin:
    DEFAULT_STREET = "street"
    DEFAULT_BUILDING_NUMBER = "1"
    DEFAULT_APARTMENT_NUMBER = "2"
    DEFAULT_CITY = "city"
    DEFAULT_COUNTRY = "country"

    @staticmethod
    def create_address(
        street=DEFAULT_STREET,
        building_number=DEFAULT_BUILDING_NUMBER,
        apartment_number=DEFAULT_APARTMENT_NUMBER,
        city=DEFAULT_CITY,
        country=DEFAULT_COUNTRY,
        **kwargs,
    ):
        return Address.objects.create(
            street=street,
            building_number=building_number,
            apartment_number=apartment_number,
            city=city,
            country=country,
            **kwargs,
        )


class LessonsMixin:
    DEFAULT_SUBJECT_NAME = "subject"
    DEFAULT_TIME = ("1", "7:00 - 7:45")
    DEFAULT_WEEKDAY = ("mon", "Monday")
    DEFAULT_CLASSROOM = 123

    @staticmethod
    def create_subject(name=DEFAULT_SUBJECT_NAME, **kwargs):
        return Subject.objects.create(name=name, **kwargs)

    @staticmethod
    def create_lesson(
        subject,
        teacher,
        school_class,
        time=DEFAULT_TIME,
        weekday=DEFAULT_WEEKDAY,
        classroom=DEFAULT_CLASSROOM,
        **kwargs,
    ):
        return Lesson.objects.create(
            subject=subject,
            teacher=teacher,
            school_class=school_class,
            time=time,
            weekday=weekday,
            classroom=classroom,
            **kwargs,
        )

    @staticmethod
    def create_lesson_session(lesson, date=None, **kwargs):
        if date:
            lesson_session = LessonSession.objects.create(lesson=lesson, **kwargs)
            lesson_session.date = date
            lesson_session.save()
        else:
            lesson_session = LessonSession.objects.create(lesson=lesson, **kwargs)

        return lesson_session

    @staticmethod
    def create_presences(lesson_session, students):
        presences = [
            Presence(lesson_session=lesson_session, student=student)
            for student in students
        ]

        with transaction.atomic():
            Presence.objects.bulk_create(presences)
            return Presence.objects.order_by("-id")[: len(presences)]


class GradesMixin:
    DEFAULT_GRADE_CATEGORY_NAME = "Exam"

    DEFAULT_GRADE = "3"
    DEFAULT_WEIGHT = "1"

    @staticmethod
    def create_grade_category(
        subject, school_class, name=DEFAULT_GRADE_CATEGORY_NAME, **kwargs
    ):
        return GradeCategory.objects.create(
            subject=subject, school_class=school_class, name=name, **kwargs
        )

    @staticmethod
    def create_grade(
        category,
        subject,
        student,
        teacher,
        grade=DEFAULT_GRADE,
        weight=DEFAULT_WEIGHT,
        **kwargs,
    ):
        return Grade.objects.create(
            category=category,
            subject=subject,
            student=student,
            teacher=teacher,
            grade=grade,
            weight=weight,
            **kwargs,
        )


class LoginRequiredTestMixin:
    def get_url(self):
        raise NotImplementedError("get_url must be overridden")

    def test_redirects_to_login_page_when_user_is_not_logged_in(self):
        expected_url = f"{settings.LOGIN_URL}?next={self.get_url()}"

        response = self.client.get(self.get_url())

        self.assertRedirects(response, expected_url)


class TeacherViewTestMixin(LoginRequiredTestMixin):
    def test_returns_403_when_user_is_not_in_teachers_group(self):
        self.login(self.student)

        response = self.client.get(self.get_url())

        self.assertEqual(response.status_code, 403)

    def test_returns_200_when_user_is_in_teachers_group(self):
        self.login(self.teacher)

        response = self.client.get(self.get_url())

        self.assertEqual(response.status_code, 200)


class ResourceViewTestMixin:
    def get_nonexistent_resource_url(self):
        raise NotImplementedError("get_nonexistent_resource_url must be overridden")

    def test_returns_404_if_object_does_not_exist(self):
        mro = super().__self_class__.__mro__

        if TeacherViewTestMixin in mro:
            self.login(self.teacher)
        elif LoginRequiredTestMixin in mro:
            self.login(self.student)

        response = self.client.get(self.get_nonexistent_resource_url())

        self.assertEqual(response.status_code, 404)
