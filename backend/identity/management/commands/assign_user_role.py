from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from identity.models import Organization, Role, User
from identity.rbac import assign_role_from_trusted_command


class Command(BaseCommand):
    help = "Assign a seeded organization role to a user."

    def add_arguments(self, parser):
        parser.add_argument("organization_slug")
        parser.add_argument("email")
        parser.add_argument("role_code")

    def handle(self, *args, **options):
        organization = Organization.objects.filter(
            slug=options["organization_slug"]
        ).first()
        if organization is None:
            raise CommandError("The organization does not exist.")
        user = User.objects.filter(
            organization=organization,
            email=User.objects.normalize_email(options["email"]),
        ).first()
        if user is None:
            raise CommandError("The user does not belong to that organization.")
        role = Role.objects.filter(
            organization=organization,
            code=options["role_code"],
        ).first()
        if role is None:
            raise CommandError("The role does not exist in that organization.")
        try:
            assign_role_from_trusted_command(user, role)
        except ValidationError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {role.name} to {user.email} in {organization.slug}."
            )
        )
