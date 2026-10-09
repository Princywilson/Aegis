import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from accountability.models import AuditRecord

from .file_uploads import validate_uploaded_file
from .models import Content, ContentVersion
from .storage import StorageService, UploadTooLarge


class ContentArchiveConflict(APIException):
    status_code = 409
    default_detail = "Content is already archived."
    default_code = "INVALID_STATE"


class ContentVersionConflict(APIException):
    status_code = 409
    default_detail = "The content version cannot be changed in its current state."
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


@transaction.atomic
def publish_content_version(*, content_id, version_id, organization_id, actor):
    content = Content.objects.select_for_update().get(
        pk=content_id,
        organization_id=organization_id,
    )
    if content.status == Content.Status.ARCHIVED:
        raise ContentVersionConflict("Archived content cannot be published.")

    version = ContentVersion.objects.select_for_update().get(
        pk=version_id,
        content=content,
        organization_id=organization_id,
    )
    if version.status != ContentVersion.Status.DRAFT:
        raise ContentVersionConflict()

    now = timezone.now()
    previous_version_id = content.current_version_id
    if previous_version_id is not None:
        try:
            previous_version = ContentVersion.objects.select_for_update().get(
                pk=previous_version_id,
                content=content,
                organization_id=organization_id,
                status=ContentVersion.Status.PUBLISHED,
            )
        except ContentVersion.DoesNotExist as exc:
            raise ContentVersionConflict(
                "The current published version is inconsistent."
            ) from exc
        previous_version.status = ContentVersion.Status.ARCHIVED
        previous_version.archived_at = now
        previous_version.save(update_fields=["status", "archived_at"])

    old_content_status = content.status
    version.status = ContentVersion.Status.PUBLISHED
    version.published_at = now
    version.save(update_fields=["status", "published_at"])

    content.status = Content.Status.PUBLISHED
    content.current_version = version
    content.save(update_fields=["status", "current_version", "updated_at"])

    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.CONTENT_VERSION_PUBLISHED,
        resource_type="content_version",
        resource_id=version.id,
        old_values={
            "content_status": old_content_status,
            "current_version_id": (
                str(previous_version_id) if previous_version_id else None
            ),
            "version_status": ContentVersion.Status.DRAFT,
        },
        new_values={
            "content_status": Content.Status.PUBLISHED,
            "current_version_id": str(version.id),
            "version_status": ContentVersion.Status.PUBLISHED,
        },
    )
    return content, version


@transaction.atomic
def create_content_version(
    *,
    content_id,
    organization_id,
    actor,
    uploaded_file,
    version_notes="",
):
    content = Content.objects.select_for_update().get(
        pk=content_id,
        organization_id=organization_id,
    )
    if content.status == Content.Status.ARCHIVED:
        raise ContentVersionConflict("Archived content cannot receive new versions.")

    upload = validate_uploaded_file(uploaded_file)
    version_id = uuid.uuid4()
    storage_service = StorageService()
    try:
        stored_file = storage_service.store(
            organization_id=organization_id,
            content_id=content.id,
            version_id=version_id,
            uploaded_file=uploaded_file,
            max_file_size=upload.max_file_size,
        )
    except UploadTooLarge as exc:
        raise ValidationError(
            {"file": ["The file exceeds the maximum size for this format."]}
        ) from exc

    next_version_number = (
        ContentVersion.objects.filter(
            organization_id=organization_id,
            content=content,
        ).aggregate(max_version=Max("version_number"))["max_version"]
        or 0
    ) + 1
    version = ContentVersion(
        id=version_id,
        organization_id=organization_id,
        content=content,
        version_number=next_version_number,
        version_notes=version_notes,
        storage_key=stored_file.storage_key,
        original_filename=upload.filename,
        mime_type=upload.mime_type,
        file_size=stored_file.file_size,
        checksum=stored_file.checksum,
        created_by=actor,
    )
    try:
        version.save()
    except (DjangoValidationError, DatabaseError):
        storage_service.delete_file(stored_file.storage_key)
        raise
    return version


@transaction.atomic
def archive_content_version(
    *,
    content_id,
    version_id,
    organization_id,
    actor,
):
    content = Content.objects.select_for_update().get(
        pk=content_id,
        organization_id=organization_id,
    )
    version = ContentVersion.objects.select_for_update().get(
        pk=version_id,
        content=content,
        organization_id=organization_id,
    )
    if content.current_version_id == version.id:
        raise ContentVersionConflict("The current content version cannot be archived.")
    if version.status == ContentVersion.Status.ARCHIVED:
        raise ContentVersionConflict("The content version is already archived.")

    old_status = version.status
    version.status = ContentVersion.Status.ARCHIVED
    version.archived_at = timezone.now()
    version.save(update_fields=["status", "archived_at"])

    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.CONTENT_VERSION_ARCHIVED,
        resource_type="content_version",
        resource_id=version.id,
        old_values={"status": old_status},
        new_values={"status": version.status},
    )
    return version
