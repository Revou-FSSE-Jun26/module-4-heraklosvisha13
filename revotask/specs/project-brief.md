# Project Brief: RevoTask

## 1. Project Overview

RevoTask is a web-based task management application inspired by Trello. It is designed to help teams organize, manage, and track their workflows through a visual Kanban board.

The application allows users to create boards, manage task cards, organize workflow columns, collaborate through comments, and monitor team activities.

This project will follow an **AI-Driven Development approach**, using Kiro IDE and Kiro CLI to assist with project planning, architecture design, implementation, testing, and documentation.

The primary goal is to build a maintainable, scalable, secure, and responsive task management application following professional software development practices.

## 2. User Roles and Permissions

RevoTask has two primary user roles:

### 2.1 Board Member

Board Members can:

- Create and manage boards.
- Create, update, and delete board columns.
- Create, update, and delete task cards.
- Move task cards between columns using drag-and-drop functionality.
- Add comments to task cards.
- Edit and delete their own comments.
- View tasks assigned to them.
- Monitor their assigned tasks and progress.

### 2.2 Board Administrator

Board Administrators have all the permissions of Board Members, with additional administrative capabilities:

- Manage board membership and access permissions.
- View and monitor all task cards across board columns.
- Manage team collaboration and board access.
- Access board analytics and team progress summaries.
- Monitor member activities and board notifications.

**Authorization Rules:**
- Users must be authenticated before accessing protected application features.
- Board-level resources must only be accessible to authorized board members.
- Administrative operations must be restricted to Board Administrators.
- Users can only edit or delete comments they own.
- The backend must enforce all authorization rules independently of frontend restrictions.

## 3. Core Functional Requirements

### 3.1 Authentication and User Profile

- User registration and login.
- JWT-based authentication.
- Secure password hashing.
- Protected frontend routes and backend API endpoints.
- User profile viewing and updating.
- Persistent authentication session management.

### 3.2 Board and Column Management

- Create, read, update, and delete boards (CRUD).
- Create, read, update, and delete columns (CRUD).
- Organize columns within individual boards.
- Reorder columns using a numeric ordering strategy based on floating-point values (`FLOAT`).
- Ensure that each column belongs to a specific board.
- Restrict board and column management based on user permissions.

### 3.3 Task Card Management and Drag-and-Drop

- Create, read, update, and delete task cards (CRUD).
- Assign task cards to board members.
- Move cards between columns using drag-and-drop interactions.
- Implement Optimistic UI updates to provide immediate visual feedback during card movement.
- Persist card movements to the backend.
- Support real-time card searching with a 300ms debounce mechanism.
- Allow users to view task details, including descriptions, assignments, comments, and activity information.

**Ordering Strategy:**

Use floating-point ordering values (`FLOAT`) to manage card positions within columns.

When a card is moved, update its ordering value rather than updating the ordering values of every card in the column. This approach is intended to minimize unnecessary database updates.

The backend must also handle cases where ordering values become too close or require recalculation.

### 3.4 Collaboration and Notifications

**Comments:**
- Users can add comments to task cards.
- Users can edit and delete only their own comments.
- The backend must validate comment ownership before processing update or delete operations.
- Unauthorized operations must return HTTP `403 Forbidden`.

**Notifications:**
- Provide a notification bell icon in the application interface.
- Display relevant board activity notifications.
- Automatically refresh notification data every 30 seconds.
- Support notification status tracking, such as read and unread states.

### 3.5 Board Analytics and Activity Monitoring

Provide a board analytics dashboard containing:

- Total number of task cards grouped by column.
- Number of completed task cards during the current week.
- Team member activity summaries.
- Board progress overview.

Analytics data must be retrieved from the backend through dedicated API endpoints.

## 4. Technology Stack

The project must use the following technology stack:

### 4.1 Backend

- **Programming Language:** Python
- **Framework:** Flask
- **ORM:** SQLAlchemy
- **Database Migration:** Flask-Migrate
- **Authentication:** Flask-JWT-Extended
- **Data Validation and Serialization:** Marshmallow
- **Database:** PostgreSQL
- **Production WSGI Server:** Gunicorn
- **Testing Framework:** Pytest

### 4.2 Frontend

- **Framework:** Next.js
- **Routing:** Next.js App Router
- **UI Library:** React
- **Programming Language:** TypeScript
- **Styling:** Tailwind CSS
- **Toast Notifications:** react-hot-toast
- **End-to-End Testing:** Playwright

### 4.3 Development Tools and Deployment

- **AI-Assisted Development:** Kiro IDE and Kiro CLI
- **Backend Hosting:** Railway
- **Database Hosting:** Railway PostgreSQL
- **Frontend Hosting:** Vercel
- **Version Control:** Git

## 5. Non-Functional Requirements

### 5.1 Security and Authorization

- Passwords must never be stored in plain text.
- Use a secure password hashing algorithm.
- All protected API endpoints must require valid JWT authentication.
- JWT tokens must be validated on the backend.
- Implement role-based access control (RBAC).
- Validate board membership before allowing access to board resources.
- Validate comment ownership before allowing comment updates or deletions.
- Return appropriate HTTP status codes for authentication and authorization failures:
  - `401 Unauthorized`: Missing, invalid, or expired authentication token.
  - `403 Forbidden`: Authenticated user does not have permission to perform the requested operation.
  - `404 Not Found`: Requested resource does not exist.

### 5.2 Performance and Responsiveness

- Use floating-point ordering strategies to minimize unnecessary database updates when moving cards or reordering columns.
- Implement a 300ms debounce mechanism for card search to reduce unnecessary API requests.
- Use Optimistic UI updates for a responsive drag-and-drop experience.
- Implement appropriate database indexing for frequently queried fields.
- Avoid unnecessary API requests and redundant frontend rendering.
- Ensure the application is responsive across desktop, tablet, and mobile devices.

### 5.3 Maintainability and Scalability

- Follow a modular and maintainable project architecture.
- Separate frontend and backend responsibilities.
- Apply clear separation of concerns across application layers.
- Use reusable frontend components.
- Implement consistent API response structures and error handling.
- Maintain clear naming conventions and coding standards.
- Write automated tests for critical business logic and API endpoints.
- Keep application configuration and environment variables separate from source code.

## 6. Development Guidelines

The project must be developed using an AI-Driven Development workflow with Kiro.

Kiro should follow a structured development process:

1. Analyze the project brief and identify the functional and non-functional requirements.
2. Generate project steering documents to establish coding standards, architectural principles, technology constraints, and project conventions.
3. Create feature specifications using the Spec workflow, including:
   - Requirements documentation.
   - Technical design documentation.
   - Implementation task breakdown.
4. Implement features incrementally based on approved specifications.
5. Generate and execute automated tests.
6. Review implementation against the requirements and design documents.
7. Update project documentation whenever architectural or implementation decisions change.

**Important Development Principles:**

- Do not implement the entire application in a single development task.
- Build the application incrementally, starting with the project foundation.
- Prioritize backend architecture, database design, and API contracts before frontend integration.
- Ensure frontend and backend implementations follow consistent API contracts.
- Avoid unnecessary dependencies and overengineering.
- Follow established software engineering best practices.
- Do not introduce additional technologies without a clear technical justification.

## 7. Project Success Criteria

The project will be considered successful when:

- Users can register, log in, and manage their profiles securely.
- Board Administrators can manage boards, columns, and board membership.
- Board Members can manage their assigned tasks and collaborate with other members.
- Task cards can be moved between columns using drag-and-drop.
- Card movements are persisted correctly using the ordering strategy.
- Users can collaborate through comments with proper ownership restrictions.
- Notifications are refreshed automatically.
- Board analytics accurately reflect task and team activity.
- The application works consistently across desktop and mobile devices.
- Critical application workflows are covered by automated tests.
- The application can be deployed successfully using Railway and Vercel.

## 8. General Instructions for Kiro

Treat this document as the primary project brief and source of truth for RevoTask.

Before implementing any feature:

- Analyze the existing project structure and development context.
- Identify dependencies and potential technical constraints.
- Follow the established steering documents and project specifications.
- Ask for clarification when requirements are ambiguous or conflicting.
- Do not assume unspecified business rules without documenting the assumptions.

The objective is to build RevoTask as a production-oriented application while maintaining a development workflow that is understandable, testable, and suitable for future enhancements.