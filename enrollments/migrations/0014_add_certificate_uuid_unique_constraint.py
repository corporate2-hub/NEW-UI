# Generated manually to add unique constraint to certificate_uuid after fixing duplicates
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0013_fix_duplicate_certificate_uuids'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollment',
            name='certificate_uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='Public unique ID for certificate verification URL.', unique=True),
        ),
    ]
