from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model


class OrganizationEmailBackend(BaseBackend):
    def authenticate(
        self,
        request,
        organization_slug=None,
        email=None,
        password=None,
        **kwargs,
    ):
        if not organization_slug or not email or not password:
            return None

        user_model = get_user_model()
        email = user_model.objects.normalize_email(email)
        user = user_model.objects.filter(
            organization__slug=organization_slug,
            email=email,
        ).first()

        if user is None:
            user_model().set_password(password)
            return None

        if user.check_password(password) and user.is_active:
            return user

        return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
        return user if user.is_active else None