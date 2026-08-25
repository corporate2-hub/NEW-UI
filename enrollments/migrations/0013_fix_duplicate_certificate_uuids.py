# Generated manually to fix duplicate certificate_uuid values
import uuid
from django.db import migrations


def fix_duplicate_uuids(apps, schema_editor):
    """Assign unique UUIDs to all enrollments with duplicate values."""
    Enrollment = apps.get_model('enrollments', 'Enrollment')
    
    # Get all enrollments and assign unique UUIDs
    for enrollment in Enrollment.objects.all():
        enrollment.certificate_uuid = uuid.uuid4()
        enrollment.save(update_fields=['certificate_uuid'])


def reverse_fix(apps, schema_editor):
    """Reverse is a no-op since we're just fixing data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0012_enrollment_certificate_end_period_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_uuids, reverse_fix),
    ]
