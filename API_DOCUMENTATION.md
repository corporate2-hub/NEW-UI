# API Endpoints Documentation

## Overview
The Skill.jobs Training platform provides comprehensive REST API endpoints for course management, enrollments, classes, and attendance. This document covers all available endpoints.

## Authentication
All protected endpoints require user authentication. Use session-based authentication or token-based authentication.

### Login
```
POST /auth/login/
Content-Type: application/x-www-form-urlencoded

username=user&password=pass
```

## Endpoints by Resource

### Courses

#### List All Courses
```
GET /courses/
Query Parameters:
  - search: Search term
  - category: Category slug
  - level: beginner|intermediate|advanced
  - sort: Field to sort by (default: -created_at)
  
Response: 200 OK
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Django REST Framework",
      "slug": "django-rest-framework",
      "description": "...",
      "category": "Web Development",
      "instructor": "john_instructor",
      "level": "advanced",
      "price": "49.99",
      "duration_hours": 24,
      "status": "published"
    }
  ]
}
```

#### Get Course Details
```
GET /courses/{slug}/

Response: 200 OK
{
  "id": 1,
  "title": "Django REST Framework",
  "description": "...",
  "sections": [
    {
      "id": 1,
      "title": "Introduction",
      "lessons": [...]
    }
  ],
  "benefits": [...],
  "requirements": [...],
  "faqs": [...],
  "batches": [...],
  "instructor": {...}
}
```

### Enrollments

#### Request Enrollment
```
POST /enroll/batch/{batch_id}/request/
Content-Type: application/json

Response: 302 Redirect to /enroll/my-enrollments/
```

#### List My Enrollments
```
GET /enroll/my-enrollments/
Authorization: Required (Student/Instructor/Admin)

Response: 200 OK
{
  "enrollments": [
    {
      "id": 1,
      "student": "student1",
      "batch": "Batch-1",
      "course": "Django REST Framework",
      "status": "approved|pending|rejected",
      "request_date": "2024-01-15T10:00:00Z",
      "approval_date": "2024-01-16T15:30:00Z"
    }
  ]
}
```

### Classes

#### List Classes for Batch
```
GET /classes/batch/{batch_id}/
Authorization: Required (Enrolled student or instructor)

Response: 200 OK
{
  "batch": {...},
  "classes": [
    {
      "id": 1,
      "title": "Introduction to REST APIs",
      "topic": "REST Principles",
      "scheduled_date": "2024-02-01",
      "scheduled_time": "10:00:00",
      "meet_link": "https://meet.google.com/...",
      "recording_link": "https://youtube.com/...",
      "resources": [...]
    }
  ]
}
```

#### Get Class Details
```
GET /classes/{class_id}/
Authorization: Required

Response: 200 OK
{
  "id": 1,
  "title": "Introduction to REST APIs",
  "topic": "REST Principles",
  "description": "...",
  "scheduled_date": "2024-02-01",
  "scheduled_time": "10:00:00",
  "meet_link": "https://meet.google.com/...",
  "recording_link": null,
  "resources": [
    {
      "id": 1,
      "title": "Presentation Slides",
      "file": "https://..."
    }
  ]
}
```

### Attendance

#### Mark Attendance
```
POST /attendance/class/{class_id}/
Authorization: Required (Instructor of the batch)
Content-Type: application/x-www-form-urlencoded

status_{student_id}=present|absent|late
remarks_{student_id}=Optional remarks

Response: 302 Redirect
```

#### Get Attendance Summary
```
GET /attendance/batch/{batch_id}/summary/
Authorization: Required

Response: 200 OK
{
  "batch": "Batch-1",
  "summary_data": [
    {
      "student": {
        "id": 1,
        "username": "student1",
        "first_name": "Student",
        "last_name": "One"
      },
      "summary": {
        "total": 5,
        "present": 4,
        "absent": 1,
        "late": 0,
        "percentage": 80.0
      }
    }
  ]
}
```

### Dashboard

#### Student Dashboard
```
GET /dashboard/student/
Authorization: Required (Student role)

Response: 200 OK + Rendered HTML
- Shows enrollments summary
- Upcoming classes
- Attendance statistics
```

#### Instructor Dashboard
```
GET /dashboard/instructor/
Authorization: Required (Instructor role)

Response: 200 OK + Rendered HTML
- Shows assigned batches
- Upcoming classes  
- Quick links to mark attendance
```

#### Admin Dashboard
```
GET /dashboard/admin/
Authorization: Required (Admin/Staff)

Response: 200 OK + Rendered HTML
- Platform statistics
- Pending enrollments
- Quick admin actions
```

### Users/Accounts

#### Register
```
POST /auth/register/
Content-Type: application/x-www-form-urlencoded

username=&email=&first_name=&last_name=&phone=&password1=&password2=

Response: 302 Redirect to /auth/login/
```

#### Login
```
POST /auth/login/
Content-Type: application/x-www-form-urlencoded

username=&password=

Response: 302 Redirect to /dashboard/student/
```

#### Logout
```
POST /auth/logout/
Authorization: Required

Response: 302 Redirect to /
```

#### View Profile
```
GET /auth/profile/
Authorization: Required

Response: 200 OK + Rendered HTML
```

#### Edit Profile
```
POST /auth/profile/edit/
Authorization: Required
Content-Type: multipart/form-data

first_name=&last_name=&phone=&bio=&profile_image=

Response: 302 Redirect to /auth/profile/
```

#### Forgot Password
```
POST /auth/forgot-password/
Content-Type: application/x-www-form-urlencoded

email=user@example.com

Response: 302 Redirect to /auth/login/
```

#### Reset Password
```
POST /auth/reset-password/{token}/
Content-Type: application/x-www-form-urlencoded

password=&password_confirm=

Response: 302 Redirect to /auth/login/
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid input",
  "details": "Field 'email' is required"
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "You do not have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "An internal server error occurred"
}
```

## Rate Limiting
API calls are limited to prevent abuse:
- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour

## Pagination
List endpoints support pagination:
```
GET /courses/?page=1

Query Parameters:
  - page: Page number (default: 1)
  - per_page: Results per page (default: 12, max: 100)
```

## Filtering
Apply filters to list endpoints:
```
GET /courses/?category=web-development&level=advanced&search=django

Query Parameters:
  - search: Search in title and description
  - category: Filter by category slug
  - level: Filter by level (beginner|intermediate|advanced)
  - status: Filter by status (draft|published|archived)
```

## Sorting
Sort list results:
```
GET /courses/?sort=-created_at

Common sort fields:
  - created_at: Ascending by creation date
  - -created_at: Descending by creation date
  - title: Alphabetical by title
  - price: By price (low to high)
  - -price: By price (high to low)
```

## Data Types

### Course Object
```json
{
  "id": 1,
  "title": "string",
  "slug": "string",
  "description": "string",
  "category": 1,
  "instructor": 1,
  "banner_image": "string|null",
  "level": "beginner|intermediate|advanced",
  "price": "decimal",
  "duration_hours": "integer",
  "status": "draft|published|archived",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Batch Object
```json
{
  "id": 1,
  "course": 1,
  "name": "string",
  "instructor": 1,
  "start_date": "date",
  "end_date": "date",
  "max_students": "integer",
  "status": "upcoming|running|completed",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Enrollment Object
```json
{
  "id": 1,
  "student": 1,
  "batch": 1,
  "status": "pending|approved|rejected",
  "request_date": "datetime",
  "approval_date": "datetime|null",
  "approved_by": 1
}
```

### ClassSession Object
```json
{
  "id": 1,
  "batch": 1,
  "title": "string",
  "topic": "string",
  "description": "string",
  "scheduled_date": "date",
  "scheduled_time": "time",
  "meet_link": "url",
  "recording_link": "url|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Attendance Object
```json
{
  "id": 1,
  "class_session": 1,
  "student": 1,
  "status": "present|absent|late",
  "recorded_at": "datetime",
  "recorded_by": 1,
  "remarks": "string|null"
}
```

## Examples

### Example 1: Browse Courses
```bash
curl -X GET "http://localhost:8000/courses/?category=web-development&sort=-price"
```

### Example 2: Enroll in a Course
```bash
curl -X POST "http://localhost:8000/enroll/batch/1/request/" \
  -H "Cookie: sessionid=..." 
```

### Example 3: Mark Attendance
```bash
curl -X POST "http://localhost:8000/attendance/class/1/" \
  -H "Cookie: sessionid=..." \
  -d "status_1=present&status_2=absent&status_3=late"
```

## Webhooks (Future)
- enrollment.approved
- enrollment.rejected
- class.scheduled
- attendance.marked

## Versioning
- Current API Version: v1
- Future versions will be available at `/api/v2/`

---

**Last Updated**: April 6, 2026
