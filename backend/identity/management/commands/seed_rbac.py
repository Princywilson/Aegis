from django.core.management.base import BaseCommand
from django.db import transaction

from identity.models import Organization
from identity.rbac import seed_organization_roles


class Command(BaseCommand):
    help = "Create the AEGIS permission catalogue and standard roles per organization."

    @transaction.atomic
    def handle(self, *args, **options):
        organizations = Organization.objects.order_by("id")
        for organization in organizations.iterator():
            seed_organization_roles(organization)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded standard AEGIS roles for {organizations.count()} organizations."
            )
        )
