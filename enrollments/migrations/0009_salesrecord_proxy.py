"""
Replaces the managed=False SalesRecord (backed by a SQL view) with a proxy
model of Enrollment backed by an annotated ORM queryset.

Operations:
  1. Drop the physical database view (it is no longer needed).
  2. Delete the old managed=False SalesRecord model state.
  3. Re-create SalesRecord as a proxy of Enrollment.

No table is created or altered – only Django's internal migration state changes
and the stale SQL view is removed.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0008_enrollment_payment_fields'),
    ]

    operations = [
        # Remove the physical view from the database.
        migrations.RunSQL(
            "DROP VIEW IF EXISTS enrollments_salesrecord",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Remove the old managed=False model from Django's migration state.
        migrations.DeleteModel(
            name='SalesRecord',
        ),

        # Re-create it as a proxy model of Enrollment.
        migrations.CreateModel(
            name='SalesRecord',
            fields=[],
            options={
                'verbose_name': 'Sales Record',
                'verbose_name_plural': 'Sales Records',
                'ordering': ['-request_date'],
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('enrollments.enrollment',),
        ),
    ]
