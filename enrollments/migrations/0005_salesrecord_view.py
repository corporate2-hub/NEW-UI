"""
Migration that creates the ``enrollments_salesrecord`` database VIEW.

The VIEW is the physical backend for the SalesRecord model (managed=False).
It joins Enrollment → Batch → Course → Company to give each row its full
commercial context without storing any extra data.
"""

from django.db import migrations

SQL_CREATE_VIEW = """
CREATE VIEW enrollments_salesrecord AS
SELECT
    e.id                                                        AS id,
    e.student_id                                                AS student_id,
    CASE
        WHEN TRIM(u.first_name || u.last_name) = ''
        THEN u.username
        ELSE TRIM(u.first_name || ' ' || u.last_name)
    END                                                         AS student_name,
    u.email                                                     AS student_email,
    b.course_id                                                 AS course_id,
    c.title                                                     AS course_title,
    c.price                                                     AS course_price,
    e.batch_id                                                  AS batch_id,
    b.name                                                      AS batch_name,
    b.company_id                                                AS company_id,
    comp.name                                                   AS company_name,
    e.status                                                    AS status,
    e.request_date                                              AS request_date,
    e.approval_date                                             AS approval_date,
    e.certificate_given                                         AS certificate_given
FROM enrollments_enrollment  e
JOIN auth_customuser         u    ON e.student_id = u.id
JOIN enrollments_batch       b    ON e.batch_id   = b.id
JOIN courses_course          c    ON b.course_id  = c.id
JOIN accounts_company        comp ON b.company_id = comp.id
"""

SQL_DROP_VIEW = "DROP VIEW IF EXISTS enrollments_salesrecord"


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0004_enrollment_certificate_given'),
        ('accounts', '0008_company_ssl_commerce_key_company_ssl_commerce_secret_and_more'),
    ]

    operations = [
        migrations.RunSQL(SQL_CREATE_VIEW, SQL_DROP_VIEW),
    ]
