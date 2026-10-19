import uuid
from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accountability.models import AuditRecord, RiskInvestigation, SecurityEvent
from accountability.services import record_access_denied
from identity.models import Organization, Permission, RolePermission, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles
from knowledge.models import Content, ContentAccess, ContentAssignment, ContentVersion, Program, ProgramAccessGrant
from knowledge.storage import StorageService


class RiskAndAssistantTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Risk Org",
            slug="risk-org",
        )
        self.other_organization = Organization.objects.create(
            name="Other Org",
            slug="other-org",
        )
        self.admin = User.objects.create_user(
            email="admin@risk.example",
            password="StrongPass123!",
            organization=self.organization,
        )
        self.consumer = User.objects.create_user(
            email="consumer@risk.example",
            password="StrongPass123!",
            organization=self.organization,
        )
        self.other_consumer = User.objects.create_user(
            email="other@risk.example",
            password="StrongPass123!",
            organization=self.other_organization,
        )

        self.roles = seed_organization_roles(self.organization)
        self.other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(self.admin, self.roles["administrator"])
        assign_role_from_trusted_command(self.consumer, self.roles["content_consumer"])
        assign_role_from_trusted_command(self.other_consumer, self.other_roles["content_consumer"])

        self.program = Program.objects.create(
            organization=self.organization,
            name="Safety Program",
            created_by=self.admin,
        )
        self.content = Content.objects.create(
            organization=self.organization,
            title="Quarterly policy guidance",
            description="Policy guidance for the program.",
            status=Content.Status.PUBLISHED,
            created_by=self.admin,
        )
        version_id = uuid.uuid4()
        self.version = ContentVersion.objects.create(
            id=version_id,
            organization=self.organization,
            content=self.content,
            version_number=1,
            status=ContentVersion.Status.PUBLISHED,
            storage_key=StorageService.build_storage_key(
                organization_id=self.organization.id,
                content_id=self.content.id,
                version_id=version_id,
            ),
            original_filename="policy.pdf",
            mime_type="application/pdf",
            file_size=1024,
            checksum="a" * 64,
            created_by=self.admin,
        )
        self.content.current_version = self.version
        self.content.save(update_fields=["current_version"])
        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.program,
            content=self.content,
            created_by=self.admin,
        )
        ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
            granted_by=self.admin,
            status=ProgramAccessGrant.Status.ACTIVE,
        )
        self.client = APIClient()

    def test_risk_signals_are_advisory_and_organization_scoped(self):
        for _ in range(2):
            record_access_denied(
                organization=self.organization,
                user=self.consumer,
                content_id=self.content.id,
            )

        self.client.force_authenticate(self.admin)
        access_count_before = ContentAccess.objects.count()
        active_grant_before = ProgramAccessGrant.objects.get(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
        ).status
        response = self.client.get("/api/v1/risk-signals/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(
            item["type"] == "REPEATED_DENIALS"
            for item in response.data["data"]
        ))
        self.assertEqual(
            ContentAccess.objects.filter(
                organization=self.organization,
                access_result=ContentAccess.Result.DENIED,
            ).count(),
            0,
        )
        self.assertEqual(ContentAccess.objects.count(), access_count_before)
        self.assertEqual(
            ProgramAccessGrant.objects.get(
                organization=self.organization,
                user=self.consumer,
                program=self.program,
            ).status,
            active_grant_before,
        )

        record_access_denied(
            organization=self.organization,
            user=self.consumer,
            content_id=self.content.id,
        )
        for _ in range(3):
            SecurityEvent.objects.create(
                organization=self.other_organization,
                user=self.other_consumer,
                event_type="ACCESS_DENIED",
                severity=SecurityEvent.Severity.MEDIUM,
                resource_type="content",
                resource_id=uuid.uuid4(),
            )
        SecurityEvent.objects.filter(
            organization=self.organization,
            event_type="ACCESS_DENIED",
        ).update(occurred_at=timezone.now())
        response = self.client.get("/api/v1/risk-signals/")
        self.assertTrue(any(
            item["type"] == "REPEATED_DENIALS"
            for item in response.data["data"]
        ))
        self.assertEqual(
            {item["user_id"] for item in response.data["data"]},
            {str(self.consumer.id)},
        )

        self.client.force_authenticate(self.consumer)
        access_response = self.client.post(
            f"/api/v1/content/{self.content.id}/access/",
            {"program_id": str(self.program.id)},
            format="json",
        )
        self.assertEqual(access_response.status_code, 201)

    def test_access_burst_requires_four_accesses_and_three_distinct_content_items(self):
        for _ in range(4):
            ContentAccess.objects.create(
                organization=self.organization,
                user=self.consumer,
                content=self.content,
                content_version=self.version,
                access_result=ContentAccess.Result.GRANTED,
            )
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/risk-signals/")
        self.assertFalse(any(
            item["type"] == "ACCESS_BURST"
            for item in response.data["data"]
        ))
        ContentAccess.objects.filter(
            organization=self.organization,
            user=self.consumer,
        ).delete()

        contents = [self.content]
        for index in range(2):
            content = Content.objects.create(
                organization=self.organization,
                title=f"Additional guidance {index}",
                description="Synthetic test content.",
                status=Content.Status.PUBLISHED,
                created_by=self.admin,
            )
            version_id = uuid.uuid4()
            version = ContentVersion.objects.create(
                id=version_id,
                organization=self.organization,
                content=content,
                version_number=1,
                status=ContentVersion.Status.PUBLISHED,
                storage_key=StorageService.build_storage_key(
                    organization_id=self.organization.id,
                    content_id=content.id,
                    version_id=version_id,
                ),
                original_filename=f"policy-{index}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum="b" * 64,
                created_by=self.admin,
            )
            content.current_version = version
            content.save(update_fields=["current_version"])
            contents.append(content)

        for content in contents:
            ContentAccess.objects.create(
                organization=self.organization,
                user=self.consumer,
                content=content,
                content_version=content.current_version,
                access_result=ContentAccess.Result.GRANTED,
            )
        oldest_access = ContentAccess.objects.filter(
            organization=self.organization,
            user=self.consumer,
        ).order_by("accessed_at", "id").first()
        ContentAccess.objects.filter(pk=oldest_access.pk).update(
            accessed_at=timezone.now() - timedelta(hours=25)
        )

        response = self.client.get("/api/v1/risk-signals/")
        self.assertFalse(any(
            item["type"] == "ACCESS_BURST"
            for item in response.data["data"]
        ))

        ContentAccess.objects.create(
            organization=self.organization,
            user=self.consumer,
            content=self.content,
            content_version=self.version,
            access_result=ContentAccess.Result.GRANTED,
        )
        response = self.client.get("/api/v1/risk-signals/")
        self.assertFalse(any(
            item["type"] == "ACCESS_BURST"
            for item in response.data["data"]
        ))
        ContentAccess.objects.filter(pk=oldest_access.pk).update(
            accessed_at=timezone.now() - timedelta(minutes=5)
        )
        response = self.client.get("/api/v1/risk-signals/")
        signal = next(
            item for item in response.data["data"]
            if item["type"] == "ACCESS_BURST"
        )
        self.assertEqual(signal["event_count"], 4)
        self.assertEqual(signal["content_count"], 3)

        ContentAccess.objects.filter(
            organization=self.organization,
            user=self.consumer,
        ).delete()
        for content in contents:
            ContentAccess.objects.create(
                organization=self.organization,
                user=self.consumer,
                content=content,
                content_version=content.current_version,
                access_result=ContentAccess.Result.GRANTED,
                access_context=ContentAccess.Context.PREVIEW,
            )
        ContentAccess.objects.create(
            organization=self.organization,
            user=self.consumer,
            content=contents[0],
            content_version=contents[0].current_version,
            access_result=ContentAccess.Result.GRANTED,
            access_context=ContentAccess.Context.PREVIEW,
        )
        preview_only = self.client.get("/api/v1/risk-signals/")
        self.assertFalse(any(
            item["type"] == "ACCESS_BURST"
            for item in preview_only.data["data"]
        ))

    def test_access_bursts_and_denials_outside_the_24_hour_window_do_not_trigger(self):
        now = timezone.now()
        for _ in range(3):
            record_access_denied(
                organization=self.organization,
                user=self.consumer,
                content_id=self.content.id,
            )
        SecurityEvent.objects.filter(
            organization=self.organization,
            user=self.consumer,
            event_type="ACCESS_DENIED",
        ).update(occurred_at=now - timedelta(hours=25))

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/risk-signals/")
        self.assertEqual(response.data["meta"]["total"], 0)

    def test_risk_signal_date_filters_are_inclusive_and_paginated(self):
        now = timezone.now()
        timestamps = [now - timedelta(minutes=2), now - timedelta(minutes=1), now]
        for timestamp in timestamps:
            record_access_denied(
                organization=self.organization,
                user=self.consumer,
                content_id=self.content.id,
            )
        events = list(
            SecurityEvent.objects.filter(
                organization=self.organization,
                user=self.consumer,
                event_type="ACCESS_DENIED",
            ).order_by("occurred_at", "id")
        )
        for event, timestamp in zip(events, timestamps):
            SecurityEvent.objects.filter(pk=event.pk).update(occurred_at=timestamp)

        self.client.force_authenticate(self.admin)
        response = self.client.get(
            "/api/v1/risk-signals/",
            {
                "from": timestamps[0].isoformat(),
                "to": timestamps[-1].isoformat(),
                "page": "1",
                "page_size": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"], {"page": 1, "page_size": 1, "total": 1})
        self.assertEqual(response.data["data"][0]["type"], "REPEATED_DENIALS")
        summary = self.client.get(
            "/api/v1/risk-signals/summary/",
            {
                "from": timestamps[0].isoformat(),
                "to": timestamps[-1].isoformat(),
                "signal_type": "REPEATED_DENIALS",
            },
        )
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["data"]["total"], 1)

        outside = self.client.get(
            "/api/v1/risk-signals/",
            {
                "from": (timestamps[0] + timedelta(seconds=1)).isoformat(),
                "to": timestamps[-1].isoformat(),
            },
        )
        self.assertEqual(outside.status_code, 200)
        self.assertEqual(outside.data["meta"]["total"], 0)

    def test_risk_signal_filters_reject_invalid_values(self):
        self.client.force_authenticate(self.admin)
        invalid_queries = [
            "?page=0",
            "?page=1.5",
            "?page_size=101",
            "?page_size=-1",
            "?severity=HIGH",
            "?signal_type=UNKNOWN",
            "?user_id=not-a-uuid",
            "?from=2026-01-01T00%3A00%3A00",
            "?from=2026-01-02T00%3A00%3A00Z&to=2026-01-01T00%3A00%3A00Z",
        ]
        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/risk-signals/{query}")
                self.assertEqual(response.status_code, 400)

    def test_risk_signal_access_requires_organization_security_permission(self):
        self.client.force_authenticate(self.consumer)
        for path in ("/api/v1/risk-signals/", "/api/v1/risk-signals/summary/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 403)

    def test_risk_investigation_status_transitions_are_audited(self):
        record_access_denied(
            organization=self.organization,
            user=self.consumer,
            content_id=self.content.id,
        )
        source_event = SecurityEvent.objects.get(
            organization=self.organization,
            user=self.consumer,
            event_type="ACCESS_DENIED",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/risk-investigations/",
            {
                "title": "Suspicious access burst",
                "summary": "Repeated denied access attempts were observed.",
                "severity": "HIGH",
                "evidence": [
                    {"type": "security_event", "id": str(source_event.id)}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["data"]["evidence"][0]["id"],
            str(source_event.id),
        )
        investigation_id = response.data["data"]["id"]

        invalid = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"status": "RESOLVED"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

        update = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"status": "IN_REVIEW", "notes": "Under investigation"},
            format="json",
        )
        self.assertEqual(update.status_code, 200)
        investigation = RiskInvestigation.objects.get(pk=investigation_id)
        self.assertEqual(investigation.status, RiskInvestigation.Status.IN_REVIEW)
        self.assertIn("Under investigation", investigation.notes)

        audit = AuditRecord.objects.filter(resource_type="risk_investigation").latest("occurred_at")
        self.assertEqual(audit.action, AuditRecord.Action.RISK_INVESTIGATION_UPDATED)
        self.assertNotIn("Under investigation", str(audit.metadata))
        self.assertEqual(audit.metadata["changed_fields"], ["notes", "status"])

        resolved = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"status": "RESOLVED"},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(
            AuditRecord.objects.filter(
                resource_type="risk_investigation",
                action=AuditRecord.Action.RISK_INVESTIGATION_RESOLVED,
            ).count(),
            1,
        )
        terminal = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"status": "DISMISSED"},
            format="json",
        )
        self.assertEqual(terminal.status_code, 400)

    def test_every_investigation_status_transition_is_validated(self):
        allowed_transitions = {
            RiskInvestigation.Status.OPEN: {
                RiskInvestigation.Status.IN_REVIEW,
                RiskInvestigation.Status.DISMISSED,
            },
            RiskInvestigation.Status.IN_REVIEW: {
                RiskInvestigation.Status.RESOLVED,
                RiskInvestigation.Status.DISMISSED,
            },
            RiskInvestigation.Status.RESOLVED: set(),
            RiskInvestigation.Status.DISMISSED: set(),
        }
        self.client.force_authenticate(self.admin)

        for current_status in RiskInvestigation.Status.values:
            for target_status in RiskInvestigation.Status.values:
                with self.subTest(current=current_status, target=target_status):
                    investigation = RiskInvestigation.objects.create(
                        organization=self.organization,
                        created_by=self.admin,
                        title=f"{current_status} to {target_status}",
                        status=current_status,
                    )
                    response = self.client.patch(
                        f"/api/v1/risk-investigations/{investigation.id}/",
                        {"status": target_status},
                        format="json",
                    )
                    allowed = (
                        current_status not in {
                            RiskInvestigation.Status.RESOLVED,
                            RiskInvestigation.Status.DISMISSED,
                        }
                        and (
                            target_status == current_status
                            or target_status in allowed_transitions[current_status]
                        )
                    )
                    self.assertEqual(
                        response.status_code,
                        200 if allowed else 400,
                    )
                    investigation.refresh_from_db()
                    self.assertEqual(
                        investigation.status,
                        target_status if allowed else current_status,
                    )
                    transition_audits = AuditRecord.objects.filter(
                        resource_type="risk_investigation",
                        resource_id=investigation.id,
                        action__in=[
                            AuditRecord.Action.RISK_INVESTIGATION_UPDATED,
                            AuditRecord.Action.RISK_INVESTIGATION_RESOLVED,
                            AuditRecord.Action.RISK_INVESTIGATION_DISMISSED,
                        ],
                    )
                    self.assertEqual(
                        transition_audits.count(),
                        int(target_status != current_status and allowed),
                    )

    def test_closed_investigations_reject_all_updates_but_remain_readable(self):
        self.client.force_authenticate(self.admin)
        for status in (
            RiskInvestigation.Status.RESOLVED,
            RiskInvestigation.Status.DISMISSED,
        ):
            investigation = RiskInvestigation.objects.create(
                organization=self.organization,
                created_by=self.admin,
                title=f"{status} case",
                summary="Original summary",
                notes="Original notes",
                status=status,
                severity=RiskInvestigation.Severity.MEDIUM,
                evidence=[],
            )
            path = f"/api/v1/risk-investigations/{investigation.id}/"
            audit_count = AuditRecord.objects.filter(
                resource_type="risk_investigation",
                resource_id=investigation.id,
            ).count()

            for payload in (
                {"title": "Changed title"},
                {"summary": "Changed summary"},
                {"notes": "Changed notes"},
                {"severity": "HIGH"},
                {"evidence": [{"type": "security_event", "id": str(uuid.uuid4())}]},
                {"status": status},
            ):
                with self.subTest(status=status, payload=payload):
                    response = self.client.patch(path, payload, format="json")
                    self.assertEqual(response.status_code, 400)

            investigation.refresh_from_db()
            self.assertEqual(investigation.title, f"{status} case")
            self.assertEqual(investigation.summary, "Original summary")
            self.assertEqual(investigation.notes, "Original notes")
            self.assertEqual(investigation.severity, RiskInvestigation.Severity.MEDIUM)
            self.assertEqual(investigation.status, status)
            self.assertEqual(investigation.evidence, [])
            self.assertEqual(
                AuditRecord.objects.filter(
                    resource_type="risk_investigation",
                    resource_id=investigation.id,
                ).count(),
                audit_count,
            )

            read_response = self.client.get(path)
            self.assertEqual(read_response.status_code, 200)
            self.assertEqual(read_response.data["data"]["title"], f"{status} case")

    def test_investigation_endpoints_require_security_event_permission(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/risk-investigations/",
            {"title": "Permission check"},
            format="json",
        )
        investigation_id = created.data["data"]["id"]

        self.client.force_authenticate(self.consumer)
        requests = [
            self.client.get("/api/v1/risk-investigations/"),
            self.client.get(
                f"/api/v1/risk-investigations/{investigation_id}/"
            ),
            self.client.post(
                "/api/v1/risk-investigations/",
                {"title": "Unauthorized creation"},
                format="json",
            ),
            self.client.patch(
                f"/api/v1/risk-investigations/{investigation_id}/",
                {"status": "IN_REVIEW"},
                format="json",
            ),
        ]
        self.assertEqual([response.status_code for response in requests], [403] * 4)
        self.assertEqual(
            RiskInvestigation.objects.get(pk=investigation_id).status,
            RiskInvestigation.Status.OPEN,
        )

    def test_investigation_mutations_and_audit_records_roll_back_together(self):
        self.client.force_authenticate(self.admin)
        create_data = {"title": "Rollback case", "summary": "Before"}
        with patch(
            "accountability.views.AuditRecord.objects.create",
            side_effect=IntegrityError("audit write failed"),
        ):
            with self.assertRaises(IntegrityError):
                self.client.post(
                    "/api/v1/risk-investigations/",
                    create_data,
                    format="json",
                )
        self.assertFalse(RiskInvestigation.objects.exists())
        self.assertFalse(
            AuditRecord.objects.filter(
                resource_type="risk_investigation"
            ).exists()
        )

        created = self.client.post(
            "/api/v1/risk-investigations/",
            create_data,
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        investigation_id = created.data["data"]["id"]
        audit_count = AuditRecord.objects.filter(
            resource_type="risk_investigation"
        ).count()
        with patch(
            "accountability.views.AuditRecord.objects.create",
            side_effect=IntegrityError("audit write failed"),
        ):
            with self.assertRaises(IntegrityError):
                self.client.patch(
                    f"/api/v1/risk-investigations/{investigation_id}/",
                    {"summary": "After"},
                    format="json",
                )
        investigation = RiskInvestigation.objects.get(pk=investigation_id)
        self.assertEqual(investigation.summary, "Before")
        self.assertEqual(
            AuditRecord.objects.filter(
                resource_type="risk_investigation"
            ).count(),
            audit_count,
        )

    def test_investigation_edits_audit_fields_without_sensitive_text(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/risk-investigations/",
            {"title": "Initial title", "summary": "Initial summary"},
            format="json",
        )
        investigation_id = created.data["data"]["id"]
        response = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {
                "title": "Updated title",
                "summary": "private-summary-marker",
                "notes": "private-notes-marker",
                "severity": "HIGH",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        audit = AuditRecord.objects.filter(
            resource_type="risk_investigation",
            resource_id=investigation_id,
        ).latest("occurred_at")
        self.assertEqual(
            audit.metadata["changed_fields"],
            ["notes", "severity", "summary", "title"],
        )
        serialized_audit = str(
            {
                "old_values": audit.old_values,
                "new_values": audit.new_values,
                "metadata": audit.metadata,
            }
        )
        self.assertNotIn("private-summary-marker", serialized_audit)
        self.assertNotIn("private-notes-marker", serialized_audit)
        self.assertNotIn("Updated title", serialized_audit)

    def test_investigation_evidence_validation_rejects_invalid_and_cross_org_sources(self):
        source_event = SecurityEvent.objects.create(
            organization=self.organization,
            user=self.consumer,
            event_type="ACCESS_DENIED",
            severity=SecurityEvent.Severity.MEDIUM,
            resource_type="content",
            resource_id=self.content.id,
        )
        foreign_event = SecurityEvent.objects.create(
            organization=self.other_organization,
            user=self.other_consumer,
            event_type="ACCESS_DENIED",
            severity=SecurityEvent.Severity.MEDIUM,
            resource_type="content",
            resource_id=uuid.uuid4(),
        )
        self.client.force_authenticate(self.admin)
        invalid_references = [
            [{"type": "unknown", "id": str(source_event.id)}],
            [{"type": "security_event", "id": "not-a-uuid"}],
            [{"type": "security_event", "id": str(uuid.uuid4())}],
            [{"type": "security_event", "id": str(foreign_event.id)}],
            [
                {"type": "security_event", "id": str(source_event.id)},
                {"type": "security_event", "id": str(source_event.id)},
            ],
            [{"type": "security_event", "id": str(source_event.id), "extra": True}],
            [
                {"type": "security_event", "id": str(uuid.uuid4())}
                for _ in range(26)
            ],
        ]
        for evidence in invalid_references:
            with self.subTest(evidence=evidence):
                response = self.client.post(
                    "/api/v1/risk-investigations/",
                    {"title": "Evidence check", "evidence": evidence},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(RiskInvestigation.objects.exists())

        valid = self.client.post(
            "/api/v1/risk-investigations/",
            {
                "title": "Valid evidence",
                "evidence": [
                    {"type": "security_event", "id": str(source_event.id)}
                ],
            },
            format="json",
        )
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(
            valid.data["data"]["evidence"][0]["id"],
            str(source_event.id),
        )
        investigation_id = valid.data["data"]["id"]
        evidence_removed = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"evidence": []},
            format="json",
        )
        self.assertEqual(evidence_removed.status_code, 200)
        evidence_audit = AuditRecord.objects.filter(
            resource_type="risk_investigation",
            resource_id=investigation_id,
        ).latest("occurred_at")
        self.assertEqual(evidence_audit.metadata["changed_fields"], ["evidence"])
        self.assertEqual(evidence_audit.metadata["evidence_count_before"], 1)
        self.assertEqual(evidence_audit.metadata["evidence_count_after"], 0)
        source_event.refresh_from_db()
        self.assertEqual(source_event.event_type, "ACCESS_DENIED")

    def test_investigation_evidence_is_hidden_after_source_permission_revocation(self):
        source_audit = AuditRecord.objects.create(
            organization=self.organization,
            actor_user=self.admin,
            action=AuditRecord.Action.CONTENT_UPDATED,
            resource_type="content",
            resource_id=self.content.id,
        )
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/risk-investigations/",
            {
                "title": "Permission visibility case",
                "evidence": [
                    {"type": "audit_record", "id": str(source_audit.id)}
                ],
            },
            format="json",
        )
        investigation_id = created.data["data"]["id"]
        RolePermission.objects.filter(
            role=self.roles["administrator"],
            permission__code=Permission.Code.AUDIT_VIEW_ORGANIZATION,
        ).delete()
        detail = self.client.get(
            f"/api/v1/risk-investigations/{investigation_id}/"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["evidence"], [])

    def test_investigation_evidence_requires_source_specific_permission(self):
        source_audit = AuditRecord.objects.create(
            organization=self.organization,
            actor_user=self.admin,
            action=AuditRecord.Action.CONTENT_UPDATED,
            resource_type="content",
            resource_id=self.content.id,
        )
        RolePermission.objects.get_or_create(
            role=self.roles["content_consumer"],
            permission=Permission.objects.get(
                code=Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
            ),
        )
        self.client.force_authenticate(self.consumer)
        response = self.client.post(
            "/api/v1/risk-investigations/",
            {
                "title": "Unauthorized audit evidence",
                "evidence": [
                    {"type": "audit_record", "id": str(source_audit.id)}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(RiskInvestigation.objects.exists())
        self.assertNotIn(str(source_audit.id), str(response.data))

    def test_investigation_list_validates_filters_and_bounds_pagination(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/risk-investigations/",
            {"title": "Listed case"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        response = self.client.get(
            "/api/v1/risk-investigations/?status=OPEN&page=1&page_size=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"]["total"], 1)
        invalid_queries = [
            "?status=UNKNOWN",
            "?severity=UNKNOWN",
            "?page=0",
            "?page_size=101",
            "?unknown=value",
        ]
        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/risk-investigations/{query}")
                self.assertEqual(response.status_code, 400)

    def test_investigation_list_detail_and_mutations_are_organization_scoped(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/risk-investigations/",
            {"title": "Organization A case"},
            format="json",
        )
        investigation_id = created.data["data"]["id"]
        RolePermission.objects.get_or_create(
            role=self.other_roles["content_consumer"],
            permission=Permission.objects.get(
                code=Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
            ),
        )
        self.client.force_authenticate(self.other_consumer)
        listing = self.client.get("/api/v1/risk-investigations/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["meta"]["total"], 0)
        detail = self.client.get(
            f"/api/v1/risk-investigations/{investigation_id}/"
        )
        self.assertEqual(detail.status_code, 404)
        update = self.client.patch(
            f"/api/v1/risk-investigations/{investigation_id}/",
            {"title": "Cross-organization update"},
            format="json",
        )
        self.assertEqual(update.status_code, 404)
        self.assertEqual(
            RiskInvestigation.objects.get(pk=investigation_id).title,
            "Organization A case",
        )

    def test_assistant_retrieval_is_permission_filtered_and_safe_when_empty(self):
        self.client.force_authenticate(self.consumer)
        response = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly policy guidance"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["insufficient_authorized_sources"])
        self.assertEqual(response.data["data"]["citations"][0]["title"], self.content.title)
        self.assertNotIn("active grant scope", response.data["data"]["answer"])

        self.client.force_authenticate(self.other_consumer)
        denied = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly policy guidance"},
            format="json",
        )
        self.assertEqual(denied.status_code, 200)
        self.assertTrue(denied.data["data"]["insufficient_authorized_sources"])
        self.assertEqual(denied.data["data"]["citations"], [])

    def test_assistant_citations_include_only_programs_authorized_for_consumer(self):
        unrelated_program = Program.objects.create(
            organization=self.organization,
            name="Unrelated Program",
            created_by=self.admin,
        )
        ContentAssignment.objects.create(
            organization=self.organization,
            program=unrelated_program,
            content=self.content,
            created_by=self.admin,
        )
        self.client.force_authenticate(self.consumer)

        response = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly policy guidance"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        citation = response.data["data"]["citations"][0]
        self.assertEqual(citation["program_names"], [self.program.name])
        self.assertNotIn(unrelated_program.name, str(citation))

    def test_assistant_does_not_disclose_same_org_content_without_consumer_grant(self):
        private_program = Program.objects.create(
            organization=self.organization,
            name="Restricted program marker",
            created_by=self.admin,
        )
        private_content = Content.objects.create(
            organization=self.organization,
            title="Confidential metadata marker 8f6c",
            description="Private program-only description.",
            status=Content.Status.PUBLISHED,
            created_by=self.admin,
        )
        version_id = uuid.uuid4()
        version = ContentVersion.objects.create(
            id=version_id,
            organization=self.organization,
            content=private_content,
            version_number=1,
            status=ContentVersion.Status.PUBLISHED,
            storage_key=StorageService.build_storage_key(
                organization_id=self.organization.id,
                content_id=private_content.id,
                version_id=version_id,
            ),
            original_filename="private.pdf",
            mime_type="application/pdf",
            file_size=1024,
            checksum="c" * 64,
            created_by=self.admin,
        )
        private_content.current_version = version
        private_content.save(update_fields=["current_version"])
        ContentAssignment.objects.create(
            organization=self.organization,
            program=private_program,
            content=private_content,
            created_by=self.admin,
        )
        self.client.force_authenticate(self.consumer)

        response = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Confidential metadata marker 8f6c"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["insufficient_authorized_sources"])
        self.assertEqual(response.data["data"]["citations"], [])
        self.assertNotIn("Confidential metadata marker 8f6c", str(response.data))
        self.assertNotIn("Restricted program marker", str(response.data))

    def test_assistant_rechecks_grants_programs_assignments_and_current_version(self):
        self.client.force_authenticate(self.consumer)
        path = "/api/v1/assistant/query/"
        body = {"question": "Quarterly policy guidance"}
        grant = ProgramAccessGrant.objects.get(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
        )

        grant.expires_at = timezone.now() - timedelta(seconds=1)
        grant.save(update_fields=["expires_at"])
        expired = self.client.post(path, body, format="json")
        self.assertTrue(expired.data["data"]["insufficient_authorized_sources"])

        grant.expires_at = None
        grant.save(update_fields=["expires_at"])
        grant.status = ProgramAccessGrant.Status.REVOKED
        grant.save(update_fields=["status"])
        revoked = self.client.post(path, body, format="json")
        self.assertTrue(revoked.data["data"]["insufficient_authorized_sources"])

        grant.status = ProgramAccessGrant.Status.ACTIVE
        grant.save(update_fields=["status"])
        self.program.status = Program.Status.INACTIVE
        self.program.save(update_fields=["status"])
        inactive_program = self.client.post(path, body, format="json")
        self.assertTrue(
            inactive_program.data["data"]["insufficient_authorized_sources"]
        )

        self.program.status = Program.Status.ACTIVE
        self.program.save(update_fields=["status"])
        assignment = ContentAssignment.objects.get(
            organization=self.organization,
            program=self.program,
            content=self.content,
        )
        assignment.delete()
        missing_assignment = self.client.post(path, body, format="json")
        self.assertTrue(
            missing_assignment.data["data"]["insufficient_authorized_sources"]
        )

        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.program,
            content=self.content,
            created_by=self.admin,
        )
        self.content.status = Content.Status.ARCHIVED
        self.content.save(update_fields=["status"])
        unpublished = self.client.post(path, body, format="json")
        self.assertTrue(unpublished.data["data"]["insufficient_authorized_sources"])

        self.content.status = Content.Status.PUBLISHED
        self.content.save(update_fields=["status"])
        self.version.status = ContentVersion.Status.ARCHIVED
        self.version.save(update_fields=["status"])
        stale_version = self.client.post(path, body, format="json")
        self.assertTrue(
            stale_version.data["data"]["insufficient_authorized_sources"]
        )

        self.version.status = ContentVersion.Status.PUBLISHED
        self.version.save(update_fields=["status"])
        mismatched_content = Content.objects.create(
            organization=self.organization,
            title="Different content",
            status=Content.Status.PUBLISHED,
            created_by=self.admin,
        )
        mismatched_version_id = uuid.uuid4()
        mismatched_version = ContentVersion.objects.create(
            id=mismatched_version_id,
            organization=self.organization,
            content=mismatched_content,
            version_number=1,
            status=ContentVersion.Status.PUBLISHED,
            storage_key=StorageService.build_storage_key(
                organization_id=self.organization.id,
                content_id=mismatched_content.id,
                version_id=mismatched_version_id,
            ),
            original_filename="different.pdf",
            mime_type="application/pdf",
            file_size=1024,
            checksum="b" * 64,
            created_by=self.admin,
        )
        mismatched_content.current_version = mismatched_version
        mismatched_content.save(update_fields=["current_version"])
        self.content.current_version = mismatched_version
        self.content.save(update_fields=["current_version"])
        mismatched_version_result = self.client.post(path, body, format="json")
        self.assertTrue(
            mismatched_version_result.data["data"]["insufficient_authorized_sources"]
        )

    def test_assistant_applies_permission_checks_and_role_specific_content_scope(self):
        self.client.force_authenticate(self.consumer)
        RolePermission.objects.filter(
            role=self.roles["content_consumer"],
            permission__code=Permission.Code.CONTENT_SEARCH,
        ).delete()
        no_search = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly"},
            format="json",
        )
        self.assertEqual(no_search.status_code, 403)

        RolePermission.objects.get_or_create(
            role=self.roles["content_consumer"],
            permission=Permission.objects.get(
                code=Permission.Code.CONTENT_SEARCH
            ),
        )
        RolePermission.objects.filter(
            role=self.roles["content_consumer"],
            permission__code=Permission.Code.CONTENT_VIEW,
        ).delete()
        no_view = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly"},
            format="json",
        )
        self.assertEqual(no_view.status_code, 403)

        RolePermission.objects.get_or_create(
            role=self.roles["content_consumer"],
            permission=Permission.objects.get(code=Permission.Code.CONTENT_VIEW),
        )
        ProgramAccessGrant.objects.filter(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
        ).delete()
        self.client.force_authenticate(self.admin)
        elevated_result = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly"},
            format="json",
        )
        self.assertEqual(elevated_result.status_code, 200)
        self.assertFalse(
            elevated_result.data["data"]["insufficient_authorized_sources"]
        )
        self.assertIn(
            "no answer was generated",
            elevated_result.data["data"]["answer"],
        )

    def test_assistant_validates_question_shape_length_and_unknown_fields(self):
        self.client.force_authenticate(self.consumer)
        invalid_requests = [
            [],
            {"question": " "},
            {"question": 42},
            {"question": "q" * 201},
            {"question": "Quarterly", "extra": "not supported"},
        ]
        for body in invalid_requests:
            with self.subTest(body=body):
                response = self.client.post(
                    "/api/v1/assistant/query/",
                    body,
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

        missing = self.client.post(
            "/api/v1/assistant/query/",
            {},
            format="json",
        )
        self.assertEqual(missing.status_code, 400)

    def test_assistant_limits_results_and_does_not_mutate_access_state(self):
        for index in range(6):
            content = Content.objects.create(
                organization=self.organization,
                title=f"Quarterly update {index}",
                description="Additional authorized matching content.",
                status=Content.Status.PUBLISHED,
                created_by=self.admin,
            )
            version_id = uuid.uuid4()
            version = ContentVersion.objects.create(
                id=version_id,
                organization=self.organization,
                content=content,
                version_number=1,
                status=ContentVersion.Status.PUBLISHED,
                storage_key=StorageService.build_storage_key(
                    organization_id=self.organization.id,
                    content_id=content.id,
                    version_id=version_id,
                ),
                original_filename=f"update-{index}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum=f"{index + 1:064x}",
                created_by=self.admin,
            )
            content.current_version = version
            content.save(update_fields=["current_version"])
            ContentAssignment.objects.create(
                organization=self.organization,
                program=self.program,
                content=content,
                created_by=self.admin,
            )

        before = {
            "accesses": ContentAccess.objects.count(),
            "grants": list(
                ProgramAccessGrant.objects.filter(
                    organization=self.organization,
                    user=self.consumer,
                ).values_list("id", "status", "expires_at")
            ),
            "assignments": ContentAssignment.objects.count(),
            "content_statuses": list(
                Content.objects.filter(organization=self.organization)
                .order_by("id")
                .values_list("id", "status", "current_version_id")
            ),
        }
        self.client.force_authenticate(self.consumer)
        response = self.client.post(
            "/api/v1/assistant/query/",
            {"question": "Quarterly"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]["citations"]), 5)
        self.assertEqual(ContentAccess.objects.count(), before["accesses"])
        self.assertEqual(
            list(
                ProgramAccessGrant.objects.filter(
                    organization=self.organization,
                    user=self.consumer,
                ).values_list("id", "status", "expires_at")
            ),
            before["grants"],
        )
        self.assertEqual(ContentAssignment.objects.count(), before["assignments"])
        self.assertEqual(
            list(
                Content.objects.filter(organization=self.organization)
                .order_by("id")
                .values_list("id", "status", "current_version_id")
            ),
            before["content_statuses"],
        )
