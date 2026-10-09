import uuid

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient

from accountability.models import AuthenticationRateLimitCounter, SecurityEvent
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

    def test_authentication_requires_matching_organization_email_and_password(self):
        first_organization = Organization.objects.create(name="First", slug="first")
        second_organization = Organization.objects.create(name="Second", slug="second")
        first_user = User.objects.create_user(
            email="person@example.com",
            password="first-password",
            organization=first_organization,
        )
        User.objects.create_user(
            email="person@example.com",
            password="second-password",
            organization=second_organization,
        )

        self.assertEqual(
            authenticate(
                organization_slug="first",
                email="person@example.com",
                password="first-password",
            ),
            first_user,
        )
        self.assertIsNone(
            authenticate(
                organization_slug="first",
                email="person@example.com",
                password="second-password",
            )
        )

    def test_inactive_user_cannot_authenticate(self):
        organization = Organization.objects.create(name="Example", slug="example")
        User.objects.create_user(
            email="person@example.com",
            password="correct-password",
            organization=organization,
            status=User.Status.INACTIVE,
        )

        self.assertIsNone(
            authenticate(
                organization_slug="example",
                email="person@example.com",
                password="correct-password",
            )
        )


class AuthenticationApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Example Organization",
            slug="example",
        )
        self.user = User.objects.create_user(
            email="person@example.com",
            password="correct-password",
            organization=self.organization,
            first_name="Example",
            last_name="User",
        )
        self.login_url = "/api/v1/auth/login/"
        self.client = APIClient()

    def credentials(self, **overrides):
        values = {
            "organization_slug": "example",
            "email": "person@example.com",
            "password": "correct-password",
        }
        values.update(overrides)
        return values

    def test_login_creates_session_and_me_returns_user_context(self):
        response = self.client.post(
            self.login_url,
            self.credentials(),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["user"]["id"], str(self.user.id))
        self.assertNotIn("access_token", response.data["data"])
        self.assertTrue(response.cookies["sessionid"]["httponly"])

        current_user = self.client.get("/api/v1/auth/me/")
        self.assertEqual(current_user.status_code, 200)
        self.assertEqual(current_user.data["data"]["email"], self.user.email)
        self.assertEqual(
            current_user.data["data"]["organization"]["id"],
            str(self.organization.id),
        )
        self.assertEqual(current_user.data["data"]["roles"], [])
        self.assertEqual(current_user.data["data"]["permissions"], [])

    def test_login_failures_do_not_disclose_account_existence(self):
        wrong_password = self.client.post(
            self.login_url,
            self.credentials(password="wrong-password"),
            format="json",
        )
        unknown_organization = self.client.post(
            self.login_url,
            self.credentials(organization_slug="unknown"),
            format="json",
        )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_organization.status_code, 401)
        self.assertEqual(wrong_password.data, unknown_organization.data)

    def test_unknown_organization_failure_is_platform_scoped_and_sanitized(self):
        response = self.client.post(
            self.login_url,
            self.credentials(organization_slug="unknown"),
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        event = SecurityEvent.objects.get(event_type="LOGIN_FAILURE")
        self.assertIsNone(event.organization_id)
        self.assertIsNone(event.user_id)
        self.assertEqual(event.severity, SecurityEvent.Severity.MEDIUM)
        counter_hashes = list(
            AuthenticationRateLimitCounter.objects.values_list("key_hash", flat=True)
        )
        self.assertNotIn("person@example.com", counter_hashes)
        self.assertNotIn("correct-password", counter_hashes)
        self.assertNotIn("127.0.0.1", counter_hashes)

    def test_known_organization_failure_records_tenant_and_user(self):
        response = self.client.post(
            self.login_url,
            self.credentials(password="wrong-password"),
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        event = SecurityEvent.objects.get(event_type="LOGIN_FAILURE")
        self.assertEqual(event.organization_id, self.organization.id)
        self.assertEqual(event.user_id, self.user.id)
        self.assertEqual(event.severity, SecurityEvent.Severity.MEDIUM)

    def test_account_limit_returns_generic_429_on_fifth_failure(self):
        responses = [
            self.client.post(
                self.login_url,
                self.credentials(password="wrong-password"),
                format="json",
            )
            for _ in range(5)
        ]

        self.assertEqual([response.status_code for response in responses], [401] * 4 + [429])
        self.assertEqual(
            responses[-1].data["error"]["message"],
            "The supplied credentials are invalid or temporarily unavailable.",
        )

        correct_password = self.client.post(
            self.login_url,
            self.credentials(),
            format="json",
        )
        self.assertEqual(correct_password.status_code, 429)

    def test_ip_limit_applies_across_account_identifiers(self):
        with patch("identity.views.authenticate", return_value=None):
            responses = [
                self.client.post(
                    self.login_url,
                    self.credentials(
                        organization_slug="unknown",
                        email=f"person-{attempt}@example.com",
                    ),
                    format="json",
                    REMOTE_ADDR="192.0.2.50",
                    HTTP_X_FORWARDED_FOR="198.51.100.25",
                )
                for attempt in range(20)
            ]

        self.assertEqual(responses[-1].status_code, 429)
        self.assertTrue(
            any(event.metadata.get("rate_limit_triggered") for event in SecurityEvent.objects.all())
        )
        ip_counter = AuthenticationRateLimitCounter.objects.get(
            key_type=AuthenticationRateLimitCounter.KeyType.SOURCE_IP
        )
        self.assertEqual(len(ip_counter.failure_timestamps), 20)

    def test_inactive_user_cannot_log_in(self):
        self.user.status = User.Status.INACTIVE
        self.user.save(update_fields=["status"])

        response = self.client.post(
            self.login_url,
            self.credentials(),
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_organization_slug_selects_the_matching_email_identity(self):
        second_organization = Organization.objects.create(
            name="Second Organization",
            slug="second",
        )
        second_user = User.objects.create_user(
            email=self.user.email,
            password="second-password",
            organization=second_organization,
            first_name="Second",
            last_name="User",
        )

        response = self.client.post(
            self.login_url,
            self.credentials(
                organization_slug="second",
                password="second-password",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        current_user = self.client.get("/api/v1/auth/me/")
        self.assertEqual(current_user.data["data"]["id"], str(second_user.id))
        self.assertEqual(
            current_user.data["data"]["organization"]["id"],
            str(second_organization.id),
        )

    def test_csrf_bootstrap_allows_login_and_sets_cookie(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get("/api/v1/auth/csrf/")
        csrf_token = csrf_response.data["data"]["csrf_token"]

        self.assertEqual(csrf_response.status_code, 200)
        self.assertIn("csrftoken", csrf_response.cookies)

        response = client.post(
            self.login_url,
            self.credentials(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies["sessionid"]["httponly"])

    def test_login_rejects_missing_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            self.login_url,
            self.credentials(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "CSRF_FAILED")

    def test_logout_requires_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf_token = client.get("/api/v1/auth/csrf/").data["data"]["csrf_token"]
        login_response = client.post(
            self.login_url,
            self.credentials(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)
        csrf_token = client.get("/api/v1/auth/csrf/").data["data"]["csrf_token"]

        response = client.post("/api/v1/auth/logout/", {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "FORBIDDEN")

        logout_response = client.post(
            "/api/v1/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(logout_response.status_code, 200)

    def test_invalid_session_does_not_authenticate(self):
        self.client.cookies["sessionid"] = "invalid-session-value"

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_expired_session_does_not_authenticate(self):
        self.client.post(self.login_url, self.credentials(), format="json")
        session = self.client.session
        session.set_expiry(timezone.timedelta(seconds=-1))
        session.save()

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_login_requires_all_credentials(self):
        response = self.client.post(
            self.login_url,
            {"organization_slug": "example", "email": "person@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")

    def test_session_logout_invalidates_current_user(self):
        self.client.post(self.login_url, self.credentials(), format="json")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)

        response = self.client.post("/api/v1/auth/logout/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["message"], "Logout successful.")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)
        event = SecurityEvent.objects.get(event_type="LOGOUT")
        self.assertEqual(event.organization_id, self.organization.id)
        self.assertEqual(event.user_id, self.user.id)
        self.assertEqual(event.severity, SecurityEvent.Severity.INFO)

    def test_unauthenticated_me_returns_401(self):
        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_FAILED")