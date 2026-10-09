import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Organization, User


class IdentityModelTests(TestCase):
    def test_custom_user_model_is_configured(self):
        self.assertIs(get_user_model(), User)

    def test_organization_and_user_use_uuid_ids(self):
        organization = Organization.objects.create(name="Example", slug="example")
        user = User.objects.create_user(
            email="person@example.com",
            password="correct-horse-battery-staple",
            organization=organization,
        )

        self.assertIsInstance(organization.id, uuid.UUID)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.organization, organization)

    def test_inactive_status_disables_authentication(self):
        organization = Organization.objects.create(name="Example", slug="example")
        user = User.objects.create_user(
            email="person@example.com",
            password="correct-horse-battery-staple",
            organization=organization,
            status=User.Status.INACTIVE,
        )

        self.assertFalse(user.is_active)

    def test_password_is_hashed(self):
        organization = Organization.objects.create(name="Example", slug="example")
        user = User.objects.create_user(
            email="person@example.com",
            password="correct-horse-battery-staple",
            organization=organization,
        )

        self.assertNotEqual(user.password, "correct-horse-battery-staple")
        self.assertTrue(user.check_password("correct-horse-battery-staple"))

    def test_same_email_can_belong_to_users_in_different_organizations(self):
        first_organization = Organization.objects.create(name="First", slug="first")
        second_organization = Organization.objects.create(name="Second", slug="second")

        first_user = User.objects.create_user(
            email="person@example.com",
            password="first-password",
            organization=first_organization,
        )
        second_user = User.objects.create_user(
            email="person@example.com",
            password="second-password",
            organization=second_organization,
        )

        self.assertNotEqual(first_user.id, second_user.id)
        self.assertEqual(
            User.objects.filter(organization=first_organization).get(),
            first_user,
        )
        self.assertEqual(
            User.objects.filter(organization=second_organization).get(),
            second_user,
        )

    def test_email_must_be_unique_within_an_organization(self):
        organization = Organization.objects.create(name="Example", slug="example")
        User.objects.create_user(
            email="person@example.com",
            password="first-password",
            organization=organization,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="person@example.com",
                    password="second-password",
                    organization=organization,
                )