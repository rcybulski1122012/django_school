from django.core.exceptions import ValidationError
from django.test import TestCase

from django_school.apps.classes.models import Class
from tests.utils import ClassesMixin, LessonsMixin, UsersMixin


class ClassModelTestCase(UsersMixin, ClassesMixin, TestCase):
    def test_save_slugify_if_slug_not_given(self):
        school_class = self.create_class(number="4 cm")

        self.assertEqual(school_class.slug, "4-cm")

    def test_save_does_not_slugify_if_slug_given(self):
        school_class = self.create_class(number="4cm", slug="cm4")

        self.assertEqual(school_class.slug, "cm4")

    def test_clean_raises_ValidationError_when_tutor_is_not_a_teacher(
        self,
    ):
        student = self.create_student()
        with self.assertRaises(ValidationError):
            self.create_class(number="4cm", tutor=student).clean()


class ClassQuerySetTestCase(UsersMixin, ClassesMixin, LessonsMixin, TestCase):
    def test_visible_to_user_selects_user_class_if_student(self):
        school_class = self.create_class()
        self.create_class(number="2c")
        student = self.create_student(school_class=school_class)

        queryset = Class.objects.visible_to_user(student)
        self.assertQuerysetEqual(queryset, [school_class])

    def test_visible_to_user_select_classes_which_are_taught_by_teacher(self):
        teacher = self.create_teacher()
        school_class = self.create_class()
        self.create_class(number="2c")
        subject = self.create_subject()
        self.create_lesson(subject, teacher, school_class)

        queryset = Class.objects.visible_to_user(teacher)
        self.assertQuerysetEqual(queryset, [school_class])
