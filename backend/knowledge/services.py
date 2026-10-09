from django.db import transaction
from rest_framework.exceptions import APIException

from accountability.models import AuditRecord

from .models import Content


class ContentArchiveConflict(APIException):
    status_code = 409
    default_detail = "Content is already archived."
    default_code = "INVALID_STATE"


@transaction.atomic
def archive_content(*, content_id, organization_id, actor):
    content = Content.objects.select_for_update().get(
        pk=content_id,
        organization_id=organization_id,
    )
    if content.status == Content.Status.ARCHIVED:
        raise ContentArchiveConflict()

    old_status = content.status
    content.status = Content.Status.ARCHIVED
    content.save(update_fields=["status", "updated_at"])

    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.CONTENT_ARCHIVED,
        resource_type="content",
        resource_id=content.id,
        old_values={"status": old_status},
        new_values={"status": content.status},
    )
    return content
