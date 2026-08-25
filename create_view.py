import sqlite3
import os

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
    e.course_fee                                                AS course_fee,
    e.applied_discount                                          AS applied_discount,
    e.total_due                                                 AS total_due,
    e.payment_status                                            AS payment_status,
    e.request_date                                              AS request_date,
    e.approval_date                                             AS approval_date,
    e.certificate_given                                         AS certificate_given
FROM enrollments_enrollment  e
JOIN auth_customuser         u    ON e.student_id = u.id
JOIN enrollments_batch       b    ON e.batch_id   = b.id
JOIN courses_course          c    ON b.course_id  = c.id
JOIN accounts_company        comp ON b.company_id = comp.id
"""

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(SQL_CREATE_VIEW)
        conn.commit()
        print("Created view successfully")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("DB file not found")
