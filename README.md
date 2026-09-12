# Team Task Tracker

A **multi-tenant task management backend** built with **Django REST Framework**.

The system allows users to work across multiple workspaces and teams while maintaining strict workspace-level data isolation. It supports projects, tasks, comments, labels, assignment rules, audit trails, role-based permissions, and an optimized dashboard.

> **The main challenge of this project is not creating CRUD APIs — it is ensuring that every API, custom action, queryset, serializer, and admin screen respects the workspace boundary.**

---

## Features

* JWT Authentication
* Multi-tenant Workspaces
* Multiple Workspace Memberships
* Team Membership & Roles
* Project Management
* Task Management
* Task Comments
* Labels
* Automatic Task Assignment Rules
* Role-Based Permissions
* Workspace-Level Data Isolation
* Audit Trail
* N+1-safe Dashboard
* Task Search & Filtering
* Pagination
* Ordering
* Swagger / ReDoc / OpenAPI Documentation
* Pytest Test Suite
* PostgreSQL Database
* Django REST Framework

---

# Architecture

The main relationship is:

```text
Workspace
   │
   ├── WorkspaceMembership
   │
   └── Team
        │
        ├── TeamMembership
        │
        └── Project
             │
             └── Task
                  │
                  └── Comment
```

Additional relationships:

```text
Workspace
 ├── Labels
 ├── Memberships
 ├── Teams
 └── Audit Events

Project
 ├── Tasks
 └── Assignment Rules

Task
 ├── Assignee
 ├── Labels
 └── Comments
```

---

# Multi-Tenant Security

Workspace isolation is the most important part of the architecture.

Every model below `Workspace` exposes a common `.workspace` relationship, either directly or through its parent objects.

For example:

```python
Task.workspace = task.project.team.workspace
```

This allows the same security architecture to be reused throughout the application.

### 1. Queryset Scoping

`WorkspaceScopedQuerysetMixin` automatically filters objects based on the authenticated user's workspace membership.

Example:

```python
class TaskViewSet(WorkspaceScopedQuerysetMixin, ModelViewSet):
    workspace_lookup = "project__team__workspace"
```

The resulting queryset only contains tasks from workspaces where the current user is a member.

Therefore:

```text
User A
   │
   ├── Workspace A
   │      └── Tasks ✅
   │
   └── Workspace B
          └── Tasks ❌
```

A user cannot simply guess another task's UUID and access it.

---

### 2. Object-Level Permissions

Workspace membership is checked again at the object level.

This prevents information leakage by returning a `404` when an object belongs to an inaccessible workspace rather than revealing that the object exists with a `403`.

---

### 3. Serializer Validation

Cross-workspace relationships are validated at the serializer level.

For example, a user from Workspace B cannot be assigned to a task belonging to Workspace A.

```text
Task → Workspace A

Assignee → Workspace B

❌ Validation Error
```

---

### 4. Django Admin Isolation

Django Admin also respects workspace boundaries.

For non-superusers, `ModelAdmin.get_queryset()` applies the same workspace membership filtering.

Therefore:

```text
API Security
     │
     ├── Querysets
     ├── Object permissions
     ├── Serializer validation
     └── Django Admin
```

All access paths follow the same tenant boundary.

---

# Roles & Permissions

## Workspace Roles

| Role   | Permissions                                      |
| ------ | ------------------------------------------------ |
| Owner  | Full workspace control                           |
| Admin  | Manage workspace members and workspace resources |
| Member | Work with teams, projects and tasks              |

The workspace owner is represented using:

```text
Workspace.owner
```

Membership roles are stored in:

```text
WorkspaceMembership.role
```

Available roles:

```text
admin
member
```

---

## Team Roles

| Role   | Permissions           |
| ------ | --------------------- |
| Lead   | Manage team resources |
| Member | Work with team tasks  |

Available roles:

```text
lead
member
```

---

## Permission Summary

### Workspace Admin

Can:

* Manage workspace members
* Change membership roles
* Manage workspace resources
* Manage teams/projects
* Manage assignment rules

### Team Lead

Can:

* Manage team projects
* Manage assignment rules
* Manage team tasks

### Regular Member

Can:

* Create tasks
* Update tasks they are allowed to act on
* Create comments
* Work with tasks inside their teams

---

# Assignment Rule Engine

Tasks can be automatically assigned when created without an explicit assignee.

The rule engine is implemented using:

```python
tasks.services.apply_assignment_rules(task)
```

Rules are processed according to:

```text
priority_order
```

The engine stops when the first matching rule is found.

---

## Assignment Strategies

### 1. Label Based

```text
Strategy: label_based
```

If a task contains the configured label:

```text
Task
 └── Label: Backend

Rule
 └── Label: Backend
      └── Target User: Bibash
```

The task is assigned to the target user.

---

### 2. Default Assignee

```text
Strategy: default_assignee
```

Always assigns the task to the configured target user.

---

### 3. Least Loaded

```text
Strategy: least_loaded
```

Finds the team member with the fewest open tasks.

Open tasks exclude:

```text
done
cancelled
```

Example:

```text
Bibash    → 5 open tasks
Ram       → 2 open tasks
Shyam     → 4 open tasks

Assigned to → Ram
```

---

### 4. Round Robin

```text
Strategy: round_robin
```

Assigns the task to the team member with the fewest tasks on the current project.

Example:

```text
Project: CRM Backend

Bibash → 4 tasks
Ram   → 2 tasks
Shyam  → 3 tasks

Assigned to → Ram
```

---

## Manual Assignment

Automatic assignment is optional.

Users with the required permissions can manually reassign a task:

```http
PATCH /api/tasks/{id}/assign/
```

---

# Dashboard

The dashboard provides aggregated workspace statistics.

Endpoint:

```http
GET /api/dashboard/
```

The dashboard is designed to avoid the **N+1 query problem**.

Instead of looping through tasks in Python, the implementation uses:

```python
aggregate()
annotate()
```

against already workspace-scoped querysets.

Conceptually:

```text
Database
   │
   ├── aggregate()
   ├── annotate()
   └── filtered querysets
          │
          ▼
       Dashboard
```

The test suite verifies that the query count remains within a fixed budget regardless of the number of tasks.

---

# Audit Trail

Important actions are recorded as audit events.

Endpoint:

```http
GET /api/audit-events/
```

Supported filters include:

```text
workspace
target_type
action
```

Example:

```http
GET /api/audit-events/?workspace=<workspace_uuid>&target_type=task
```

Audit events are **read-only** through the API.

---

# Task Filtering

Tasks support filtering, searching, ordering, and pagination.

### Status

```http
GET /api/tasks/?status=todo
```

### Priority

```http
GET /api/tasks/?priority=high
```

### Assignee

```http
GET /api/tasks/?assignee=5
```

### Project

```http
GET /api/tasks/?project=<uuid>
```

### Unassigned Tasks

```http
GET /api/tasks/?unassigned=true
```

### Due Date

```http
GET /api/tasks/?due_before=2026-12-31
```

### Search

```http
GET /api/tasks/?search=django
```

### Ordering

```http
GET /api/tasks/?ordering=-created_at
```

Supported ordering fields:

```text
created_at
updated_at
due_date
priority
```

### Pagination

```http
GET /api/tasks/?page=2
```

---

# 📄 Pagination

All list endpoints use the standard Django REST Framework pagination format.

```json
{
    "count": 100,
    "next": "http://localhost:8000/api/tasks/?page=2",
    "previous": null,
    "results": []
}
```

---

# API Endpoints

## Authentication

| Method    | Endpoint                     | Description     |
| --------- | ---------------------------- | --------------- |
| POST      | `/api/auth/register/`        | Register user   |
| POST      | `/api/auth/token/`           | Obtain JWT      |
| POST      | `/api/auth/token/refresh/`   | Refresh JWT     |
| GET/PATCH | `/api/auth/me/`              | Current user    |
| POST      | `/api/auth/change-password/` | Change password |

---

## Workspaces

| Method | Endpoint                | Description       |
| ------ | ----------------------- | ----------------- |
| GET    | `/api/workspaces/`      | List workspaces   |
| POST   | `/api/workspaces/`      | Create workspace  |
| GET    | `/api/workspaces/{id}/` | Workspace details |
| PATCH  | `/api/workspaces/{id}/` | Update workspace  |
| DELETE | `/api/workspaces/{id}/` | Delete workspace  |

---

## Workspace Members

```http
GET    /api/workspaces/{id}/members/
POST   /api/workspaces/{id}/members/
DELETE /api/workspaces/{id}/members/{user_id}/
```

Workspace membership writes require appropriate admin permissions.

---

## Memberships

```http
GET   /api/memberships/
PATCH /api/memberships/{id}/
DELETE /api/memberships/{id}/
```

---

## Teams

```http
GET    /api/teams/
POST   /api/teams/
GET    /api/teams/{id}/
PATCH  /api/teams/{id}/
DELETE /api/teams/{id}/
```

Available filters:

```http
GET /api/teams/?mine=1
GET /api/teams/?workspace=<uuid>
```

---

## Team Members

```http
GET    /api/teams/{id}/members/
POST   /api/teams/{id}/members/
DELETE /api/teams/{id}/members/{user_id}/
```

---

## Projects

```http
GET    /api/projects/
POST   /api/projects/
GET    /api/projects/{id}/
PATCH  /api/projects/{id}/
DELETE /api/projects/{id}/
```

Filters:

```http
GET /api/projects/?team=<uuid>
GET /api/projects/?status=active
```

---

## Labels

```http
GET    /api/labels/
POST   /api/labels/
GET    /api/labels/{id}/
PATCH  /api/labels/{id}/
DELETE /api/labels/{id}/
```

Filter:

```http
GET /api/labels/?workspace=<uuid>
```

---

## Tasks

```http
GET    /api/tasks/
POST   /api/tasks/
GET    /api/tasks/{id}/
PATCH  /api/tasks/{id}/
DELETE /api/tasks/{id}/
```

Custom actions:

```http
PATCH /api/tasks/{id}/status/
PATCH /api/tasks/{id}/assign/
```

---

## Assignment Rules

```http
GET    /api/assignment-rules/
POST   /api/assignment-rules/
GET    /api/assignment-rules/{id}/
PATCH  /api/assignment-rules/{id}/
DELETE /api/assignment-rules/{id}/
```

Filters:

```http
GET /api/assignment-rules/?project=<uuid>
GET /api/assignment-rules/?strategy=least_loaded
GET /api/assignment-rules/?is_active=true
```

---

## Comments

```http
GET    /api/comments/
POST   /api/comments/
GET    /api/comments/{id}/
PATCH  /api/comments/{id}/
DELETE /api/comments/{id}/
```

Filter:

```http
GET /api/comments/?task=<uuid>
```

Only the author or an authorized administrator can edit/delete comments.

---

## Audit Events

Read-only endpoint:

```http
GET /api/audit-events/
```

Filters:

```http
GET /api/audit-events/?workspace=<uuid>
GET /api/audit-events/?target_type=task
GET /api/audit-events/?action=created
```

---

## Dashboard

```http
GET /api/dashboard/
```

Optional workspace:

```http
GET /api/dashboard/?workspace=<uuid>
```

---

# Project Structure

```text
team_task_tracker/
│
├── config/
│   ├── settings.py
│   ├── settings_test.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── common/
│   ├── models.py
│   ├── permissions.py
│   ├── mixins.py
│   └── pagination.py
│
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   └── admin.py
│
├── workspaces/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   └── admin.py
│
├── teams/
│
├── projects/
│
├── labels/
│
├── tasks/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── filters.py
│   ├── services.py
│   ├── urls.py
│   └── admin.py
│
├── comments/
│
├── audit/
│
├── dashboard/
│
├── tests/
│   ├── test_auth.py
│   ├── test_isolation.py
│   ├── test_tasks.py
│   ├── test_dashboard.py
│   └── test_audit.py
│
├── manage.py
├── requirements.txt
└── .env.example
```

---

# 🛠️ Technology Stack

| Technology            | Purpose               |
| --------------------- | --------------------- |
| Python                | Backend programming   |
| Django                | Web framework         |
| Django REST Framework | REST APIs             |
| PostgreSQL            | Production database   |
| SQLite                | Test database         |
| JWT                   | Authentication        |
| Pytest                | Testing               |
| drf-spectacular       | OpenAPI documentation |

---

# ⚙️ Installation & Setup

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd team_task_tracker
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure PostgreSQL credentials:

```env
DB_NAME=team_task_tracker
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

---

# Database Setup

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

---

# Run Development Server

```bash
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/
```

---

# API Documentation

After starting the server:

### OpenAPI Schema

```text
/api/schema/
```

### Swagger UI

```text
/api/docs/
```

### ReDoc

```text
/api/redoc/
```

For example:

```text
http://127.0.0.1:8000/api/docs/
```

---

# Testing

Tests use an in-memory SQLite database, so PostgreSQL is not required to run the test suite.

Run:

```bash
pytest
```

Or:

```bash
pytest -v
```

---

## Test Coverage

The test suite covers:

### Authentication

* User registration
* JWT login
* JWT refresh
* Current user
* Password change

### Workspace Isolation

Tests verify that a user cannot access another workspace's:

* Projects
* Tasks
* Comments
* Audit events
* Other workspace resources

Even when the user knows the object's ID.

Example:

```text
Bibash → Workspace A

Workspace B Task UUID
        ↓
GET /api/tasks/<workspace-b-task-id>/
        ↓
404 Not Found
```

---

### Task Tests

* Task creation
* Task update
* Task deletion
* Task filtering
* Search
* Ordering
* Pagination
* Assignment
* Status changes

---

### Assignment Tests

* Label-based assignment
* Default assignment
* Least-loaded assignment
* Round-robin assignment
* Cross-workspace assignment rejection

---

### Dashboard Tests

The dashboard test verifies:

```text
Correct statistics
        +
Workspace isolation
        +
Bounded database queries
```

The query count remains within a fixed limit even as the number of tasks increases.

---

# Typical Workflow

A typical workflow looks like:

```text
Register
   ↓
Login
   ↓
Create Workspace
   ↓
Add Workspace Members
   ↓
Create Team
   ↓
Add Team Members
   ↓
Create Project
   ↓
Create Labels
   ↓
Create Assignment Rules
   ↓
Create Task
   ↓
Assignment Rule Engine
   ↓
Task Assigned
   ↓
Members Work on Task
   ↓
Comments Added
   ↓
Task Status Updated
   ↓
Audit Event Created
   ↓
Dashboard Updated
```

---

# Security Model

The application follows a defense-in-depth approach.

```text
                 Request
                    │
                    ▼
             Authentication
                    │
                    ▼
          Workspace Queryset
             Scoping
                    │
                    ▼
          Object Permission
                    │
                    ▼
       Serializer Validation
                    │
                    ▼
              View Action
                    │
                    ▼
            Audit Logging
```

This prevents relying on a single security layer.

---

# Example: Cross-Workspace Protection

Suppose:

```text
Workspace A
 └── Project A
      └── Task A

Workspace B
 └── Project B
      └── Task B
```

User belongs only to Workspace A.

The following request:

```http
GET /api/tasks/<task-b-id>/
```

must not expose Task B.

Expected:

```http
404 Not Found
```

The same protection applies to:

```text
Tasks
Projects
Teams
Comments
Labels
Assignment Rules
Audit Events
Dashboard
```

---

# Future Improvements

The architecture is designed so additional features can be added without changing the core tenant-isolation design.

## Notifications

Add:

```text
Celery
Redis
Email notifications
In-app notifications
```

Notifications can be triggered from existing:

```text
perform_create()
perform_update()
```

methods.

---

## Real-Time Updates

Django Channels can be introduced for:

```text
Task updates
Comment updates
Assignment changes
Status changes
```

Existing task/comment mutation points provide natural places to trigger WebSocket events.

---

## File Attachments

An `Attachment` model can be added:

```text
Attachment
 ├── task
 ├── uploaded_by
 ├── file
 └── workspace
```

By exposing the same `.workspace` contract, it can automatically reuse the existing:

```text
Queryset scoping
Object permissions
Serializer validation
Admin isolation
```

---

# Project Goals

This project focuses on learning and demonstrating:

* Multi-tenant architecture
* Django REST Framework
* Relationship modeling
* Object-level permissions
* Role-based authorization
* Queryset security
* Serializer validation
* Service-layer business logic
* Automated assignment systems
* Database optimization
* N+1 query prevention
* Audit logging
* API testing
* API documentation

---

# Key Engineering Principle

> **Never trust the client to provide a valid workspace boundary.**

Workspace ownership should be determined from the authenticated user's membership and server-side relationships.

Instead of:

```python
Task.objects.all()
```

the application should always work from a workspace-scoped queryset.

This principle is what makes the application genuinely multi-tenant rather than simply having a `workspace_id` field in the database.

---

# Author

**Bibash Bayalkoti**

Backend Developer | Python & Django

---

# Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/your-feature
```

3. Make your changes
4. Run the tests

```bash
pytest
```

5. Commit your changes

```bash
git add .
git commit -m "Add your feature"
```

6. Push the branch

```bash
git push origin feature/your-feature
```

7. Open a Pull Request

---

# 📄 License

This project is intended for educational and development purposes.
