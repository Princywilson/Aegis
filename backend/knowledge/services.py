import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from accountability.models import AuditRecord
from identity.models import User

from .file_uploads import validate_uploaded_file
from .models import (
    Content,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .storage import StorageService, UploadTooLarge


class ContentArchiveConflict(APIException):
    status_code = 409
    default_detail = "Content is already archived."
    default_code = "INVALID_STATE"


class ContentVersionConflict(APIException):
    status_code = 409
    default_detail = "The content version cannot be changed in its current state."
    default_code = "INVALID_STATE"


class ProgramAssignmentConflict(APIException):
    status_code = 409
    default_detail = "The content cannot be assigned in the program's current state."
    default_code = "INVALID_STATE"


class ProgramAccessGrantConflict(APIException):
    status_code = 409
    default_detail = "The program access grant conflicts with its current state."
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
        AuditRecord.objects.create(
            organization_id=organization_id,
            actor_user=actor,
            action=AuditRecord.Action.CONTENT_VERSION_CREATED,
            resource_type="content_version",
            resource_id=version.id,
            new_values={
                "content_id": str(content.id),
                "version_number": version.version_number,
                "status": version.status,
            },
        )
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


@transaction.atomic
def set_program_status(*, program_id, organization_id, status, actor):
    program = Program.objects.select_for_update().get(
        pk=program_id,
        organization_id=organization_id,
    )
    if status not in Program.Status.values:
        raise ValueError("Unsupported program status.")
    if program.status != status:
        old_status = program.status
        program.status = status
        program.save(update_fields=["status", "updated_at"])
        AuditRecord.objects.create(
            organization_id=organization_id,
            actor_user=actor,
            action=(
                AuditRecord.Action.PROGRAM_ACTIVATED
                if status == Program.Status.ACTIVE
                else AuditRecord.Action.PROGRAM_DEACTIVATED
            ),
            resource_type="program",
            resource_id=program.id,
            old_values={"status": old_status},
            new_values={"status": program.status},
        )
    return program


@transaction.atomic
def create_content_assignment(
    *,
    program_id,
    content_id,
    organization_id,
    actor,
):
    program = Program.objects.select_for_update().get(
        pk=program_id,
        organization_id=organization_id,
    )
    if program.status != Program.Status.ACTIVE:
        raise ProgramAssignmentConflict(
            "Content cannot be assigned to an inactive program."
        )
    content = Content.objects.get(
        pk=content_id,
        organization_id=organization_id,
    )
    if ContentAssignment.objects.filter(
        organization_id=organization_id,
        program=program,
        content=content,
    ).exists():
        raise ProgramAssignmentConflict("The content is already assigned.")
    assignment = ContentAssignment.objects.create(
        organization_id=organization_id,
        program=program,
        content=content,
        created_by=actor,
    )
    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.CONTENT_ASSIGNED,
        resource_type="content_assignment",
        resource_id=assignment.id,
        new_values={
            "program_id": str(program.id),
            "content_id": str(content.id),
        },
    )
    return assignment


@transaction.atomic
def remove_content_assignment(
    *,
    program_id,
    content_id,
    organization_id,
    actor,
):
    program = Program.objects.get(
        pk=program_id,
        organization_id=organization_id,
    )
    content = Content.objects.get(
        pk=content_id,
        organization_id=organization_id,
    )
    assignment = ContentAssignment.objects.get(
        organization_id=organization_id,
        program=program,
        content=content,
    )
    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.CONTENT_UNASSIGNED,
        resource_type="content_assignment",
        resource_id=assignment.id,
        old_values={
            "program_id": str(program.id),
            "content_id": str(content.id),
        },
    )
    assignment.delete()


@transaction.atomic
def grant_program_access(
    *,
    user_id,
    program_id,
    organization_id,
    actor,
    expires_at=None,
):
    user = User.objects.select_for_update().filter(
        pk=user_id,
        organization_id=organization_id,
        status=User.Status.ACTIVE,
    ).first()
    if user is None:
        raise User.DoesNotExist
    role_codes = set(user.user_roles.values_list("role__code", flat=True))
    if "content_consumer" not in role_codes:
        raise ValidationError(
            {"user_id": ["Program access can only be granted to a Content Consumer."]}
        )

    program = Program.objects.select_for_update().filter(
        pk=program_id,
        organization_id=organization_id,
    ).first()
    if program is None:
        raise Program.DoesNotExist
    if program.status != Program.Status.ACTIVE:
        raise ProgramAssignmentConflict(
            "Access cannot be granted for an inactive program."
        )

    now = timezone.now()
    if expires_at is not None and expires_at <= now:
        raise ValidationError(
            {"expires_at": ["The expiration time must be in the future."]}
        )

    previous_active = ProgramAccessGrant.objects.select_for_update().filter(
        organization_id=organization_id,
        user=user,
        program=program,
        status=ProgramAccessGrant.Status.ACTIVE,
    ).first()
    if previous_active:
        if previous_active.expires_at is None or previous_active.expires_at > now:
            raise ProgramAccessGrantConflict("An active grant already exists.")
        previous_active.status = ProgramAccessGrant.Status.EXPIRED
        previous_active.save(update_fields=["status"])

    grant = ProgramAccessGrant(
        organization_id=organization_id,
        user=user,
        program=program,
        granted_by=actor,
        expires_at=expires_at,
    )
    try:
        with transaction.atomic():
            grant.save()
    except IntegrityError as exc:
        raise ProgramAccessGrantConflict("An active grant already exists.") from exc

    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.PROGRAM_ACCESS_GRANTED,
        resource_type="program_access_grant",
        resource_id=grant.id,
        new_values={
            "user_id": str(user.id),
            "program_id": str(program.id),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "status": grant.status,
        },
    )
    return grant


@transaction.atomic
def revoke_program_access(*, grant_id, organization_id, actor):
    grant = ProgramAccessGrant.objects.select_for_update().filter(
        pk=grant_id,
        organization_id=organization_id,
    ).first()
    if grant is None:
        raise ProgramAccessGrant.DoesNotExist
    now = timezone.now()
    if grant.status != ProgramAccessGrant.Status.ACTIVE:
        raise ProgramAccessGrantConflict("The grant is no longer active.")
    if grant.expires_at is not None and grant.expires_at <= now:
        grant.status = ProgramAccessGrant.Status.EXPIRED
        grant.save(update_fields=["status"])
        return grant

    grant.status = ProgramAccessGrant.Status.REVOKED
    grant.revoked_at = now
    grant.revoked_by = actor
    grant.save(update_fields=["status", "revoked_at", "revoked_by"])
    AuditRecord.objects.create(
        organization_id=organization_id,
        actor_user=actor,
        action=AuditRecord.Action.PROGRAM_ACCESS_REVOKED,
        resource_type="program_access_grant",
        resource_id=grant.id,
        old_values={"status": ProgramAccessGrant.Status.ACTIVE},
        new_values={"status": ProgramAccessGrant.Status.REVOKED},
    )
    return grant
