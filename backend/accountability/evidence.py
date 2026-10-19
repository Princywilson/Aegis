import uuid

from rest_framework.exceptions import ValidationError

from identity.models import Permission
from identity.rbac import has_permission

from .models import AuditRecord, SecurityEvent


MAX_EVIDENCE_REFERENCES = 25
AUDIT_EVIDENCE_RESOURCE_TYPES = {
    "content",
    "content_assignment",
    "content_version",
    "program_access_grant",
}


def _parse_reference(reference):
    if not isinstance(reference, dict) or set(reference) != {"type", "id"}:
        raise ValueError
    source_type = reference["type"]
    if not isinstance(source_type, str):
        raise ValueError
    source_type = source_type.strip().lower()
    if source_type not in {"security_event", "audit_record"}:
        raise ValueError
    try:
        source_id = uuid.UUID(str(reference["id"]))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError from exc
    return source_type, source_id


def _source_queryset(source_type, organization_id, source_ids):
    if source_type == "security_event":
        return SecurityEvent.objects.filter(
            organization_id=organization_id,
            id__in=source_ids,
            event_type="ACCESS_DENIED",
            resource_type="content",
        )
    return AuditRecord.objects.filter(
        organization_id=organization_id,
        id__in=source_ids,
        resource_type__in=AUDIT_EVIDENCE_RESOURCE_TYPES,
    )


def _has_source_permission(user, organization_id, source_type):
    permission = (
        Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
        if source_type == "security_event"
        else Permission.Code.AUDIT_VIEW_ORGANIZATION
    )
    return has_permission(user, permission, organization_id=organization_id)


def validate_evidence_references(references, *, user, organization_id):
    if not isinstance(references, list):
        raise ValidationError({"evidence": ["Evidence must be a list of references."]})
    if len(references) > MAX_EVIDENCE_REFERENCES:
        raise ValidationError(
            {"evidence": [f"No more than {MAX_EVIDENCE_REFERENCES} references are allowed."]}
        )

    parsed = []
    seen = set()
    ids_by_type = {"security_event": set(), "audit_record": set()}
    for reference in references:
        try:
            source_type, source_id = _parse_reference(reference)
        except ValueError as exc:
            raise ValidationError(
                {
                    "evidence": [
                        "Each reference must contain a supported type and UUID id."
                    ]
                }
            ) from exc
        key = (source_type, source_id)
        if key in seen:
            raise ValidationError({"evidence": ["Duplicate evidence references are not allowed."]})
        seen.add(key)
        parsed.append((source_type, source_id))
        ids_by_type[source_type].add(source_id)

    if any(
        ids and not _has_source_permission(user, organization_id, source_type)
        for source_type, ids in ids_by_type.items()
    ):
        raise ValidationError(
            {"evidence": ["One or more references are invalid or unavailable."]}
        )

    for source_type, source_ids in ids_by_type.items():
        if not source_ids:
            continue
        found_ids = set(
            _source_queryset(source_type, organization_id, source_ids).values_list(
                "id",
                flat=True,
            )
        )
        if found_ids != source_ids:
            raise ValidationError(
                {"evidence": ["One or more references are invalid or unavailable."]}
            )

    return [{"type": source_type, "id": str(source_id)} for source_type, source_id in parsed]


def visible_evidence_details(references, *, user, organization_id):
    if not isinstance(references, list):
        return []

    details = []
    for reference in references[:MAX_EVIDENCE_REFERENCES]:
        try:
            source_type, source_id = _parse_reference(reference)
        except ValueError:
            continue
        if not _has_source_permission(user, organization_id, source_type):
            continue
        source = _source_queryset(
            source_type,
            organization_id,
            {source_id},
        ).first()
        if source is None:
            continue
        if source_type == "security_event":
            details.append(
                {
                    "type": source_type,
                    "id": str(source.id),
                    "event_type": source.event_type,
                    "severity": source.severity,
                    "occurred_at": source.occurred_at,
                }
            )
        else:
            details.append(
                {
                    "type": source_type,
                    "id": str(source.id),
                    "action": source.action,
                    "occurred_at": source.occurred_at,
                }
            )
    return details
