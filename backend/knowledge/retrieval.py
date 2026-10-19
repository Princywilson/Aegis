from django.db.models import F, Q

from identity.models import Permission
from identity.rbac import has_permission

from .access import (
    program_queryset_for,
    require_content_search_permissions,
    user_is_content_consumer_only,
)
from .models import Content, ContentAssignment, ContentVersion


MAX_RETRIEVAL_QUESTION_LENGTH = 200


def _authorized_content_queryset(user):
    organization_id = user.organization_id
    queryset = Content.objects.filter(
        organization_id=organization_id,
        status=Content.Status.PUBLISHED,
        current_version__organization_id=organization_id,
        current_version__content_id=F("pk"),
        current_version__status=ContentVersion.Status.PUBLISHED,
    )

    require_content_search_permissions(user)
    if user_is_content_consumer_only(user):
        queryset = queryset.filter(
            program_assignments__organization_id=organization_id,
            program_assignments__program__in=program_queryset_for(user),
        ).distinct()

    return queryset


def _authorized_program_names(content, *, user):
    if not has_permission(
        user,
        Permission.Code.PROGRAM_VIEW,
        organization_id=user.organization_id,
    ):
        return []
    return list(
        ContentAssignment.objects.filter(
            organization_id=user.organization_id,
            content=content,
            program__organization_id=user.organization_id,
            program__in=program_queryset_for(user),
        )
        .values_list("program__name", flat=True)
        .distinct()
    )


def retrieve_authorized_sources(question, *, user):
    if not isinstance(question, str):
        raise ValueError("A string question is required.")
    search_terms = question.strip()
    if not search_terms:
        raise ValueError("A question is required.")
    if len(search_terms) > MAX_RETRIEVAL_QUESTION_LENGTH:
        raise ValueError(
            f"Question must be no more than {MAX_RETRIEVAL_QUESTION_LENGTH} characters."
        )
    queryset = _authorized_content_queryset(user)
    queryset = queryset.filter(
        Q(title__icontains=search_terms) | Q(description__icontains=search_terms)
    ).select_related("current_version", "current_version__content")

    matches = list(queryset.order_by("title")[:5])
    citations = []
    for content in matches:
        citations.append(
            {
                "content_id": str(content.id),
                "title": content.title,
                "version_number": getattr(content.current_version, "version_number", None),
                "program_names": _authorized_program_names(content, user=user),
                "source_summary": content.description or "No summary is available.",
            }
        )

    if not citations:
        return {
            "answer": "No authorized content metadata matched that query.",
            "citations": [],
            "insufficient_authorized_sources": True,
        }

    answer = (
        "I found {count} authorized content item(s) with matching metadata. "
        "The citations below are permission-checked references; no answer was generated."
    ).format(count=len(citations))
    return {
        "answer": answer,
        "citations": citations,
        "insufficient_authorized_sources": False,
    }
