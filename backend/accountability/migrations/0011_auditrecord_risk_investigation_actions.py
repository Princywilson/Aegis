from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accountability', '0010_riskinvestigation'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='auditrecord',
            name='audit_action_valid',
        ),
        migrations.AddConstraint(
            model_name='auditrecord',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('action__in', [
                        'CONTENT_CREATED',
                        'CONTENT_UPDATED',
                        'CONTENT_ARCHIVED',
                        'CONTENT_VERSION_CREATED',
                        'CONTENT_VERSION_PUBLISHED',
                        'CONTENT_VERSION_ARCHIVED',
                        'PROGRAM_ACCESS_GRANTED',
                        'PROGRAM_ACCESS_REVOKED',
                        'PROGRAM_CREATED',
                        'PROGRAM_UPDATED',
                        'PROGRAM_ACTIVATED',
                        'PROGRAM_DEACTIVATED',
                        'CONTENT_ASSIGNED',
                        'CONTENT_UNASSIGNED',
                        'USER_ROLE_CHANGED',
                        'PERMISSION_CHANGED',
                        'USER_CREATED',
                        'USER_UPDATED',
                        'RISK_INVESTIGATION_CREATED',
                        'RISK_INVESTIGATION_UPDATED',
                        'RISK_INVESTIGATION_RESOLVED',
                        'RISK_INVESTIGATION_DISMISSED',
                    ])
                ),
                name='audit_action_valid',
            ),
        ),
    ]
