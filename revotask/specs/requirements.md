# Requirements Specification: RevoTask

Sources: `specs/project-brief.md` (source of truth) and the steering files `.kiro/steering/backend.md`, `database.md`, `frontend.md`.

## 1. Introduction

RevoTask is a Trello-style Kanban web application. Users create boards, organize columns, manage task cards with drag-and-drop, collaborate through comments, receive notifications, and view board analytics.

### 1.1 Roles

| Role | Scope | Description |
|---|---|---|
| Board Member (`member`) | Per board | Manages columns, cards, and own comments on boards they belong to. |
| Board Administrator (`admin`) | Per board | All member permissions, plus board membership, analytics, and board-level administration. |

The role is stored per board in `board_members`, never on `User`. The board creator is `admin` of that board.

### 1.2 Conventions

- Requirement IDs use the format `REQ-<FEATURE>-<NN>`.
- "The system" means the backend API and frontend together. "The API" means the Flask backend only. "The UI" means the Next.js frontend only.
- Success responses are `{"data": <payload>}` with status `200` or `201`. Failures are flat `{"error": "<string>"}` with `400`, `401`, `403`, `404`, or `500` (see REQ-NFR-04).
- All API routes are under `/api/`.
- Each acceptance criterion (AC) is written so it can be verified by a Pytest API test, a frontend test, or a Playwright E2E test.

### 1.3 Assumptions

The brief does not define these points. They are recorded here per the brief's instruction to document assumptions.

| ID | Assumption |
|---|---|
| A-01 | Registration requires `name`, `email`, and `password`. Email is unique, case-insensitive. Passwords have a minimum of 8 characters. |
| A-02 | JWT access tokens expire after a configurable lifetime (default 60 minutes). No refresh-token flow is in scope. The frontend persists the token in `localStorage` to meet "persistent session". |
| A-03 | A card is "completed" when it is in the last column of its board (highest `order`). Moving a card into that column sets `completed_at`. Moving it out clears `completed_at`. |
| A-04 | A card has at most one assignee, who must be an active member of the card's board. |
| A-05 | Notification events: card assigned to a user, comment added to a card the user is assigned to, and the user added to a board. The actor never receives a notification for their own action. |
| A-06 | Board members are added by the board admin using the target user's email. The target user must already be registered. |
| A-07 | A board must always keep at least one admin. |
| A-08 | Deleting a board, column, or card is a soft delete and cascades to child records at the service layer. |
| A-09 | Analytics "team member activity" is the per-member count of cards assigned, cards completed this week, and comments written on the board. |
| A-10 | Search results are scoped to one board and exclude soft-deleted cards. |

### 1.4 Open questions

1. Should "completed" be an explicit per-column flag rather than the last column (A-03)?
2. Should a member be able to leave a board on their own?

---

## 2. Authentication (AUTH)

### REQ-AUTH-01: User registration
The system shall let an unauthenticated visitor create an account.

Acceptance criteria:
- AC1: `POST /api/auth/register` with valid `name`, `email`, `password` returns `201` and `{"data": {...}}` containing the user's `id`, `name`, and `email`.
- AC2: The response never contains `password` or `password_hash`.
- AC3: Registering an email that already exists (any letter case) returns `400` with an `error` string, and no second user is created.
- AC4: A missing field, an invalid email format, or a password shorter than 8 characters returns `400` with a readable `error` string.
- AC5: The new user's `id` is a UUID string.

### REQ-AUTH-02: Secure password storage
The API shall store only a salted hash of each password.

Acceptance criteria:
- AC1: After registration, the stored `password_hash` value differs from the submitted password.
- AC2: The hash is produced by a slow, salted algorithm (bcrypt, argon2, or werkzeug's scrypt/pbkdf2). Two users with the same password have different hashes.
- AC3: No endpoint response and no log line contains a plain-text password.

### REQ-AUTH-03: User login
The system shall let a registered user authenticate with email and password.

Acceptance criteria:
- AC1: `POST /api/auth/login` with correct credentials returns `200` and `{"data": {"access_token": <JWT>, "user": {...}}}`.
- AC2: Login with a wrong password or an unknown email returns `401` with the same generic `error` message for both cases.
- AC3: Email matching at login is case-insensitive.
- AC4: The returned token decodes with the configured `JWT_SECRET_KEY` and its `sub` equals the user's `id`.
- AC5: A soft-deleted user cannot log in (`401`).

### REQ-AUTH-04: JWT validation on protected endpoints
The API shall require a valid JWT on every endpoint except register, login, and health.

Acceptance criteria:
- AC1: A request to any protected endpoint with no `Authorization` header returns `401`.
- AC2: A request with a malformed, tampered, or wrongly signed token returns `401`.
- AC3: A request with an expired token returns `401`.
- AC4: A request with a valid `Bearer` token reaches the handler.
- AC5: All `401` bodies follow `{"error": "<string>"}`.

### REQ-AUTH-05: Protected frontend routes
The UI shall block unauthenticated access to application pages.

Acceptance criteria:
- AC1: Visiting `/` (dashboard), `/boards/<id>`, `/my-tasks`, or `/profile` without a session redirects to `/login`.
- AC2: Visiting `/login` or `/register` with an active session redirects to `/`.
- AC3: Public pages (`/login`, `/register`) render without a token.

### REQ-AUTH-06: Persistent session
The UI shall keep the user signed in across page reloads until logout or token expiry.

Acceptance criteria:
- AC1: After login, reloading the browser keeps the user on the protected page and `AuthContext` holds the token.
- AC2: After closing and reopening the tab within the token lifetime, the user is still authenticated.
- AC3: When the stored token is expired, the first API call returns `401` and the UI clears the session and redirects to `/login`.

### REQ-AUTH-07: Logout
The UI shall let the user end their session.

Acceptance criteria:
- AC1: Clicking Logout removes the token from storage and from `AuthContext`.
- AC2: After logout, navigating to a protected route redirects to `/login`.
- AC3: After logout, the notification polling timer is cleared (no further `/api/notifications` calls).

### REQ-AUTH-08: Auth forms and feedback
The UI shall provide login and registration forms with validation feedback.

Acceptance criteria:
- AC1: Submitting an invalid form shows a `react-hot-toast` error with the server's `error` message.
- AC2: Submit buttons use `<BaseButton>` and are disabled while a request is in flight.
- AC3: A successful registration signs the user in or redirects to `/login`, and shows a success toast.

---

## 3. Users and Profile (USER)

### REQ-USER-01: View own profile
The system shall let an authenticated user view their profile.

Acceptance criteria:
- AC1: `GET /api/users/me` returns `200` with `id`, `name`, `email`, and `created_at`.
- AC2: The response does not include `password_hash`.
- AC3: Without a token the endpoint returns `401`.
- AC4: The `/profile` page displays the returned name and email.

### REQ-USER-02: Update own profile
The system shall let a user update only their own `name` and `email` through `PATCH /api/users/me`.

Acceptance criteria:
- AC1: `PATCH /api/users/me` with a valid `name` returns `200` and the updated user. A subsequent `GET /api/users/me` returns the new value.
- AC2: Changing `email` to one used by another account returns `400` with an `error` string.
- AC3: An empty `name` or an invalid email returns `400`.
- AC4: Fields such as `id`, `password_hash`, and `created_at` in the payload are ignored or rejected, and are not changed. A `password` field is always rejected (see REQ-USER-03).
- AC5: A user cannot update another user's profile through this endpoint.

### REQ-USER-03: Password is not changeable through the profile endpoint
The API shall not allow a password change through `PATCH /api/users/me`. No password-change endpoint is in scope.
Acceptance criteria:
- AC1: `PATCH /api/users/me` with a `password` field in the payload (alone or with `name` or `email`) returns `400` with an `error` string.
- AC2: When the request returns `400` for `password`, no field is updated and the stored `password_hash` is unchanged.
- AC3: `PATCH /api/users/me/password` is not defined and returns `404`.
- AC4: After a rejected request, login still succeeds with the original password.
### REQ-USER-04: Look up users for board membership
The API shall let an admin find a registered user by email when adding members.

Acceptance criteria:
- AC1: `GET /api/users?email=<email>` returns `200` with a user's `id`, `name`, and `email` only when the caller is authenticated.
- AC2: An email with no matching user returns `404`.
- AC3: The response never exposes `password_hash` or other users' private fields.
- AC4: The endpoint does not return a list of all users.

### REQ-USER-05: Profile UI
The UI shall provide a profile page for viewing and editing user details.

Acceptance criteria:
- AC1: The form is prefilled with the current name and email.
- AC2: Saving shows a success toast and updates the name shown in the header.
- AC3: A server validation error is shown as a toast through `useErrorHandler`.

---

## 4. Boards (BRD)

### REQ-BRD-01: Create board
The system shall let an authenticated user create a board.

Acceptance criteria:
- AC1: `POST /api/boards` with a valid `name` (1 to 120 characters) returns `201` with the board `id` and `name`.
- AC2: The creator is inserted into `board_members` with role `admin`.
- AC3: A missing or empty `name`, or a name over 120 characters, returns `400`.
- AC4: The board `id` is a UUID string.

### REQ-BRD-02: List boards
The system shall list the boards the user belongs to.

Acceptance criteria:
- AC1: `GET /api/boards` returns only boards where the caller has an active membership.
- AC2: Each item includes the caller's `role` on that board.
- AC3: Soft-deleted boards are excluded.
- AC4: A user with no boards receives `200` and an empty list.

### REQ-BRD-03: View board
The system shall return one board with its columns and cards to members.

Acceptance criteria:
- AC1: `GET /api/boards/<id>` by a member returns `200` with board details.
- AC2: A non-member authenticated user receives `403`.
- AC3: An unknown or soft-deleted board `id` returns `404`.
- AC4: Columns are returned ordered by `order` ascending, and cards by `order` ascending within each column.
- AC5: Soft-deleted columns and cards are not returned.

### REQ-BRD-04: Update board
The system shall let a board admin rename a board.

Acceptance criteria:
- AC1: `PATCH /api/boards/<id>` by an admin with a valid `name` returns `200` and the new name.
- AC2: A `member` who is not an admin receives `403`.
- AC3: A non-member receives `403`.
- AC4: An invalid `name` returns `400`.

### REQ-BRD-05: Delete board
The system shall let a board admin delete a board.

Acceptance criteria:
- AC1: `DELETE /api/boards/<id>` by an admin returns `200` and sets `deleted_at` on the board. No SQL `DELETE` is issued.
- AC2: The board's columns, cards, and comments are also soft-deleted (A-08).
- AC3: A later `GET /api/boards/<id>` returns `404`, and the board is absent from `GET /api/boards`.
- AC4: A non-admin member receives `403`.

### REQ-BRD-06: Add board member
The system shall let a board admin add a registered user to the board.

Acceptance criteria:
- AC1: `POST /api/boards/<id>/members` by an admin with a registered user's `email` and `role` (`member` or `admin`) returns `201`.
- AC2: The added user can now `GET /api/boards/<id>` (`200`).
- AC3: Adding a user who is already a member returns `400`. The unique constraint on `(board_id, user_id)` is never violated.
- AC4: An unregistered email returns `404`.
- AC5: A `role` other than `member` or `admin` returns `400`.
- AC6: A non-admin caller receives `403`.
- AC7: The added user receives a notification (see REQ-NTF-02).

### REQ-BRD-07: List board members
The system shall let any board member see the board's members.

Acceptance criteria:
- AC1: `GET /api/boards/<id>/members` by a member returns each member's `user_id`, `name`, `email`, and `role`.
- AC2: A non-member receives `403`.
- AC3: Soft-removed memberships are excluded.

### REQ-BRD-08: Change member role
The system shall let a board admin change another member's role.

Acceptance criteria:
- AC1: `PATCH /api/boards/<id>/members/<user_id>` by an admin with `role` returns `200` and the new role.
- AC2: A non-admin receives `403`.
- AC3: Demoting the last remaining admin returns `400` (A-07).
- AC4: An invalid `role` returns `400`.
- AC5: An unknown member returns `404`.

### REQ-BRD-09: Remove board member
The system shall let a board admin remove a member.

Acceptance criteria:
- AC1: `DELETE /api/boards/<id>/members/<user_id>` by an admin returns `200` and soft-deletes the membership.
- AC2: The removed user then receives `403` on `GET /api/boards/<id>`.
- AC3: Cards assigned to the removed user in that board have `assignee_id` set to `null`.
- AC4: Removing the last admin returns `400` (A-07).
- AC5: A non-admin receives `403`.

### REQ-BRD-10: Boards UI
The UI shall provide a dashboard page (`/`) that lists boards, and a board page.

Acceptance criteria:
- AC1: The dashboard route `/` lists the user's boards and offers "Create board" in a `<BaseModal>`.
- AC2: Admin-only actions (rename, delete, manage members, analytics link) are shown only when the user's role on that board is `admin`.
- AC3: Hiding an action in the UI does not replace backend enforcement. Calling the endpoint directly as a non-admin still returns `403`.
- AC4: Deleting a board asks for confirmation using a `destructive` `<BaseButton>`.

---

## 5. Columns (COL)

### REQ-COL-01: Create column
The system shall let a board member create a column.

Acceptance criteria:
- AC1: `POST /api/boards/<board_id>/columns` with a valid `name` returns `201`.
- AC2: The new column's `order` is `1000.0` when it is the first column, otherwise last `order` + `1000.0`.
- AC3: The column belongs to the board in the URL (`board_id` is set).
- AC4: A non-member receives `403`. An unknown board returns `404`.
- AC5: A missing or empty `name` returns `400`.

### REQ-COL-02: List columns
The system shall return a board's columns in order.

Acceptance criteria:
- AC1: `GET /api/boards/<board_id>/columns` by a member returns columns sorted by `order` ascending.
- AC2: Soft-deleted columns are excluded.
- AC3: A non-member receives `403`.

### REQ-COL-03: Rename column
The system shall let a board member rename a column.

Acceptance criteria:
- AC1: `PATCH /api/columns/<id>` with a valid `name` returns `200` and the new name.
- AC2: A non-member of the column's board receives `403`.
- AC3: An unknown column returns `404`.
- AC4: An invalid `name` returns `400`.

### REQ-COL-04: Reorder column with FLOAT ordering
The API shall move a column by changing only that column's `order` value.
Acceptance criteria:
- AC1: `PATCH /api/boards/<id>/columns/reorder` with `column_id` (UUID) and `order` (positive float) sets that column's `order` and returns `200` with the updated column. The request body is validated by a marshmallow schema.
- AC2: The client computes `order` from the neighbors' orders: the midpoint between neighbors, `next_order / 2` at the start, `prev_order + 1000.0` at the end. The server stores the value it receives.
- AC3: Exactly one column row is updated. The other columns' `order` values are unchanged.
- AC4: When the received `order` equals another column's `order` on that board, all columns of that board are rebalanced to `1000.0, 2000.0, ...` in one transaction, preserving the requested relative order.
- AC5: A `column_id` that does not belong to the board in the URL returns `400`. An `order` that is missing, not a number, or not greater than zero returns `400`.
- AC6: A non-member receives `403`. An unknown board returns `404`.
### REQ-COL-05: Delete column
The system shall let a board member delete a column.

Acceptance criteria:
- AC1: `DELETE /api/columns/<id>` returns `200` and sets `deleted_at` on the column.
- AC2: Cards in the column are soft-deleted (A-08).
- AC3: A subsequent board fetch excludes the column and its cards.
- AC4: A non-member receives `403`. An unknown column returns `404`.

### REQ-COL-06: Column integrity
Every column shall belong to exactly one board.

Acceptance criteria:
- AC1: `columns.board_id` is `NOT NULL` with a foreign key to `boards.id`.
- AC2: A column cannot be created without a board.
- AC3: There is no API operation that moves a column to another board.

### REQ-COL-07: Columns UI
The UI shall let members manage columns on the board page.

Acceptance criteria:
- AC1: A member can add a column from the board page via `<BaseModal>`, and it appears at the end.
- AC2: Rename and delete actions update the page without a full reload.
- AC3: A failed request shows a toast with the server `error` message.

---

## 6. Cards and Drag-and-Drop (CRD)

### REQ-CRD-01: Create card
The system shall let a board member create a card in a column.

Acceptance criteria:
- AC1: `POST /api/columns/<column_id>/cards` with a valid `title` (1 to 200 characters) returns `201`.
- AC2: Optional fields `description`, `assignee_id`, and `due_date` are accepted and stored.
- AC3: The card's `order` is `1000.0` for an empty column, otherwise last `order` + `1000.0`.
- AC4: A non-member of the column's board receives `403`. An unknown column returns `404`.
- AC5: A missing `title` returns `400`.
- AC6: The card `id` is a UUID string.

### REQ-CRD-02: View card details
The system shall return full card details to board members.

Acceptance criteria:
- AC1: `GET /api/cards/<id>` returns `title`, `description`, `assignee`, `column_id`, `order`, `completed_at`, and `created_at`.
- AC2: The response includes the card's comments and recent activity entries.
- AC3: A non-member receives `403`. An unknown or soft-deleted card returns `404`.
- AC4: Clicking a card in the UI opens a detail modal that shows these fields.

### REQ-CRD-03: Update card
The system shall let a board member edit a card.

Acceptance criteria:
- AC1: `PATCH /api/cards/<id>` with any of `title`, `description`, `due_date` returns `200` and the updated card.
- AC2: An empty `title` returns `400`.
- AC3: A non-member receives `403`.
- AC4: `column_id` and `order` cannot be changed through this endpoint. Moves use REQ-CRD-06 (`/position`).
- AC5: `updated_at` changes after a successful update.

### REQ-CRD-04: Assign card
The system shall let a board member assign a card to a board member or clear the assignment.

Acceptance criteria:
- AC1: `PATCH /api/cards/<id>` with `assignee_id` of an active board member returns `200` and the card shows that assignee.
- AC2: An `assignee_id` of a user who is not a member of the card's board returns `400`.
- AC3: `assignee_id: null` clears the assignment.
- AC4: The new assignee receives a notification (REQ-NTF-02), unless the assignee is the caller.
- AC5: The assignee picker in the UI lists only the board's members.

### REQ-CRD-05: Delete card
The system shall let a board member delete a card.

Acceptance criteria:
- AC1: `DELETE /api/cards/<id>` returns `200` and sets `deleted_at`. No SQL `DELETE` is issued.
- AC2: The card is excluded from board fetch, search, My Tasks, and analytics counts.
- AC3: A non-member receives `403`. An unknown card returns `404`.
- AC4: The UI asks for confirmation using a `destructive` `<BaseButton>`.

### REQ-CRD-06: Move card (persistence and ordering)
The API shall persist a card move by updating only that card's `column_id` and `order`.
Acceptance criteria:
- AC1: `PATCH /api/cards/<id>/position` with `column_id` (UUID) and `order` (positive float), validated by `CardPositionSchema`, returns `200` with the updated card.
- AC2: The client computes `order` from the neighbors' orders: the midpoint between neighbors, `next_order / 2` at the start, `prev_order + 1000.0` at the end, and `1000.0` in an empty target column. The server stores the value it receives.
- AC3: Exactly one card row is updated.
- AC4: When the received `order` equals another active card's `order` in the target column, all active cards in that column are rebalanced to `1000.0, 2000.0, ...` in one transaction, and the moved card lands in the requested position.
- AC5: A target column on a different board than the card's board returns `400` or `403`, and the card is unchanged.
- AC6: A missing or non-UUID `column_id`, or an `order` that is missing, not a number, or not greater than zero, returns `400` with the `CardPositionSchema` field errors.
- AC7: A non-member receives `403`. An unknown card or column returns `404`.
- AC8: A move within the same column changes `order` only.
- AC9: Moving a card into the board's last column sets `completed_at` to the current UTC time. Moving it out sets `completed_at` to `null` (A-03).
### REQ-CRD-07: Drag-and-drop interaction
The UI shall let a member drag a card to another position or column using the native HTML5 Drag and Drop API.

Acceptance criteria:
- AC1: Cards have `draggable="true"` and columns accept drops. No third-party drag-and-drop library is installed.
- AC2: Dropping a card in another column shows it there and persists after a page reload.
- AC3: Dropping a card between two cards places it between them, and the order persists after reload.
- AC4: The drag logic lives in `hooks/useDragAndDrop.ts`, computes `order` from the neighboring cards, and calls `PATCH /api/cards/<id>/position` only through `lib/apiClient.ts`.
- AC5: A Playwright test waits on the `PATCH /api/cards/<id>/position` response, not on a fixed timeout.

### REQ-CRD-08: Optimistic UI with rollback
The UI shall update the card position immediately on drop and restore it if the request fails.

Acceptance criteria:
- AC1: On drop, the card appears in its new position before the move API response arrives (verified by delaying the response in a test).
- AC2: When the move request fails with an `ApiError`, the card returns to its original column and position.
- AC3: A failed move shows an error toast through `useErrorHandler`.
- AC4: A `401` on a move clears the session and redirects to `/login`.
- AC5: A successful move triggers no board re-fetch beyond the single move request.

### REQ-CRD-09: Card UI
The UI shall display cards and their key details inside columns.

Acceptance criteria:
- AC1: Each card shows its title, assignee name or avatar, and a `<BaseBadge>` showing "Done" or "Open" based on `completed_at`.
- AC2: A member can create, edit, and delete a card through `<BaseModal>` forms.
- AC3: All card action buttons are `<BaseButton>`. No raw `<button>` exists outside `components/shared/BaseButton.tsx`.

---

## 7. Comments (CMT)

### REQ-CMT-01: Add comment
The system shall let a board member comment on a card.

Acceptance criteria:
- AC1: `POST /api/cards/<card_id>/comments` with a non-empty `body` returns `201` with the comment, its `author_id`, and `created_at`.
- AC2: `author_id` is the caller's id and cannot be set by the client.
- AC3: An empty `body` or a body over 2000 characters returns `400`.
- AC4: A non-member of the card's board receives `403`. An unknown card returns `404`.

### REQ-CMT-02: List comments
The system shall return a card's comments to board members.

Acceptance criteria:
- AC1: `GET /api/cards/<card_id>/comments` returns comments ordered by `created_at` ascending, each with the author's `name`.
- AC2: Soft-deleted comments are excluded.
- AC3: A non-member receives `403`.

### REQ-CMT-03: Edit own comment
The system shall let only the author edit a comment.

Acceptance criteria:
- AC1: `PATCH /api/comments/<id>` by the author with a valid `body` returns `200` and the updated body.
- AC2: A different board member (including an admin) receives `403` with an `error` string, and the body is unchanged.
- AC3: The ownership check runs in `comments/service.py`, before any change.
- AC4: An unknown or soft-deleted comment returns `404`.
- AC5: An empty `body` returns `400`.

### REQ-CMT-04: Delete own comment
The system shall let only the author delete a comment.

Acceptance criteria:
- AC1: `DELETE /api/comments/<id>` by the author returns `200` and sets `deleted_at`.
- AC2: A different user returns `403`, and the comment still appears in the list.
- AC3: An unknown comment returns `404`.
- AC4: A deleted comment no longer appears in card details or the comment list.

### REQ-CMT-05: Comments UI
The UI shall show comments in the card detail modal.

Acceptance criteria:
- AC1: The comment form posts a comment, and it appears in the list without a page reload.
- AC2: Edit and delete controls are visible only on the current user's own comments.
- AC3: A `403` returned from the API is shown as an error toast.

---

## 8. Notifications (NTF)

### REQ-NTF-01: Notification data model and listing
The API shall store notifications per recipient and return them to that recipient only.

Acceptance criteria:
- AC1: `GET /api/notifications` returns only the caller's notifications, newest first, each with `id`, `type`, `message`, `board_id`, `read_at`, and `created_at`.
- AC5: The endpoint accepts the query parameters `page` (integer, 1-based, default `1`) and `per_page` (integer, default `20`, maximum `100`). The response includes the pagination metadata `page`, `per_page`, `total`, and `pages`.
- AC6: A non-integer, zero, or negative `page` or `per_page` returns `400`. A `per_page` above the maximum returns `400`.
- AC7: A `page` beyond the last page returns `200` with an empty list.
- AC2: User A cannot see User B's notifications.
- AC3: Soft-deleted notifications are excluded.
- AC4: Without a token the endpoint returns `401`.

### REQ-NTF-02: Notification creation
The API shall create notifications for relevant board activity (A-05).

Acceptance criteria:
- AC1: Assigning a card to user B (by user A) creates one notification for B.
- AC2: A comment added to a card assigned to B (by A) creates one notification for B.
- AC3: Adding user B to a board creates one notification for B.
- AC4: An action performed by a user on themselves (for example self-assignment) creates no notification.
- AC5: Notification creation happens in the same transaction as the triggering action. If the action fails, no notification is stored.

### REQ-NTF-03: Read and unread status
The system shall track read and unread state per notification.

Acceptance criteria:
- AC1: New notifications have `read_at = null`.
- AC2: `PATCH /api/notifications/<id>/read` by the recipient sets `read_at` and returns `200`.
- AC3: `PATCH /api/notifications/read-all` marks all of the caller's unread notifications read.
- AC4: Marking another user's notification returns `403`. An unknown id returns `404`.
- AC5: Marking an already-read notification is idempotent and keeps the original `read_at`.

### REQ-NTF-04: Notification bell
The UI shall show a bell icon with an unread count.

Acceptance criteria:
- AC1: The bell is visible on every authenticated page.
- AC2: The badge shows the number of notifications with `read_at = null` and is hidden when the count is zero.
- AC3: Clicking the bell opens a list of notifications, with unread items visually distinct.
- AC4: Clicking a notification marks it read and the badge count decreases by one.

### REQ-NTF-05: 30-second polling
The UI shall refresh notifications automatically every 30 seconds.

Acceptance criteria:
- AC1: `hooks/useNotifications.ts` calls `GET /api/notifications` once on mount and then every 30,000 ms (verified with fake timers).
- AC2: The interval is cleared on unmount and on logout. No requests continue after that.
- AC3: Only one polling timer exists at a time, even with several components using the bell.
- AC4: A failed poll does not show an error toast and does not stop later polls.
- AC5: A notification created on the server appears in the UI within 30 seconds, without a page reload.

---

## 9. Analytics (ANL)

### REQ-ANL-01: Board analytics endpoint
The API shall serve all board analytics from a single endpoint.
Acceptance criteria:
- AC1: `GET /api/boards/<id>/analytics` returns `200` with `{"data": {"cards_per_column": [...], "completed_this_week": {...}, "member_activity": [...]}}`.
- AC2: No other analytics endpoints exist. Per-metric routes such as `/analytics/cards-per-column` return `404`.
- AC3: `cards_per_column` has one entry per active column, with `column_id`, `name`, and `count`, ordered by column `order`.
- AC4: A column with no cards returns `count: 0`.
- AC5: Soft-deleted cards and columns are excluded.
- AC6: Counts are computed with a SQL join and `GROUP BY`, not by iterating card rows in Python.

### REQ-ANL-02: Completed this week
The analytics response shall report the number of cards completed in the current week.
Acceptance criteria:
- AC1: `completed_this_week` is `{"count": <int>, "week_start": <ISO UTC>}`.
- AC2: `week_start` is the most recent Monday 00:00 UTC.
- AC3: A card with `completed_at` at or after `week_start` is counted. A card completed one second before `week_start` is not.
- AC4: Soft-deleted cards and cards with `completed_at = null` are not counted.

### REQ-ANL-03: Team member activity
The analytics response shall include an activity summary for each board member.
Acceptance criteria:
- AC1: `member_activity` has one entry per active member with `user_id`, `name`, `assigned_count`, `completed_this_week`, and `comments_count` (A-09).
- AC2: A member with no activity returns zeros, not an omitted row.
- AC3: Counts only include cards and comments in that board.
- AC4: Counts are computed by SQL aggregation.

### REQ-ANL-04: Analytics access control
Only board admins shall access analytics.

Acceptance criteria:
- AC1: `GET /api/boards/<id>/analytics` returns `403` for a board `member` who is not an admin.
- AC2: The endpoint returns `403` for a non-member.
- AC3: The endpoint returns `404` for an unknown board and `401` without a token.
- AC4: An admin on board X cannot read analytics of board Y where they are not a member (`403`).

### REQ-ANL-05: Analytics dashboard UI
The UI shall display analytics on a dashboard page for admins.

Acceptance criteria:
- AC1: The dashboard shows cards per column, completed this week, and member activity, all loaded from the single `GET /api/boards/<id>/analytics` call.
- AC2: The dashboard link is visible only to admins.
- AC3: A `403` or error response shows a toast and does not crash the page.
- AC4: The page shows a loading state, then the data.

---

## 10. My Tasks (TSK)

### REQ-TSK-01: List assigned tasks
The API shall return the cards assigned to the caller.

Acceptance criteria:
- AC1: `GET /api/cards?assignee=me` returns only active cards where `assignee_id` equals the caller's id.
- AC2: Each item includes `id`, `title`, `board_id`, `board_name`, `column_name`, `due_date`, and `completed_at`.
- AC3: Cards on boards where the caller is no longer a member are excluded.
- AC4: Soft-deleted cards and cards in soft-deleted boards are excluded.
- AC5: Without a token the endpoint returns `401`.
- AC6: A user with no assigned cards receives `200` and an empty list.

### REQ-TSK-02: Task progress summary
The API shall return progress figures for the caller's assigned tasks.

Acceptance criteria:
- AC1: The `GET /api/cards?assignee=me` response includes `total`, `completed`, and `open` counts for the caller.
- AC2: `completed + open = total`.
- AC3: Counts update after a card is reassigned or completed.

### REQ-TSK-03: My Tasks UI
The UI shall provide a `/my-tasks` page.

Acceptance criteria:
- AC1: The page lists assigned cards grouped or labeled by board, with a `<BaseBadge>` for Done or Open status.
- AC2: Clicking a task navigates to its board or opens its card detail.
- AC3: The page shows the progress summary from REQ-TSK-02.
- AC4: An empty state message appears when there are no assigned tasks.

---

## 11. Card Search (SRC)

### REQ-SRC-01: Search API
The API shall search cards on one board by text.

Acceptance criteria:
- AC1: `GET /api/boards/<board_id>/cards?q=<text>` returns active cards whose `title` or `description` contains `<text>`, case-insensitively.
- AC2: Results are ordered by `order` ascending.
- AC3: The query uses a bound parameter (`ilike` with a bound pattern). A `q` of `' OR 1=1 --` returns no extra rows and causes no error.
- AC4: Results include only cards of the board in the URL, and exclude soft-deleted cards (A-10).
- AC5: A non-member receives `403`. An unknown board returns `404`.
- AC6: When `q` is missing or empty, the endpoint returns all active cards of the board.
- AC7: The `%` and `_` characters in `q` are treated as literal text, not wildcards.

### REQ-SRC-02: 300 ms debounce
The UI shall send a search request 300 ms after the user's last keystroke.

Acceptance criteria:
- AC1: Typing five characters with less than 300 ms between keystrokes sends exactly one request, 300 ms after the last keystroke (verified with fake timers).
- AC2: No request is sent before 300 ms elapse after the last keystroke.
- AC3: The debounce uses `useDebouncedValue(value, 300)`.
- AC4: The query string is URL-encoded with `encodeURIComponent`.
- AC5: Requests go through `lib/apiClient.ts`.

### REQ-SRC-03: Search results behavior
The UI shall show matching cards and handle empty and failed searches.

Acceptance criteria:
- AC1: Matching cards are shown on the board and non-matching cards are hidden or dimmed.
- AC2: Clearing the input restores all cards.
- AC3: A search with no matches shows an empty-state message.
- AC4: A failed request shows a toast through `useErrorHandler`.
- AC5: A late response from an older query does not overwrite the results of a newer query.
- AC6: The search input has an accessible label.

---

## 12. Non-Functional Requirements (NFR)

### REQ-NFR-01: Password and secret handling
The system shall never expose or hard-code secrets.

Acceptance criteria:
- AC1: `DATABASE_URL`, `JWT_SECRET_KEY`, and `FRONTEND_URL` are read from environment variables. A repository search finds no hard-coded values.
- AC2: A `.env.example` lists every required variable with no real values. `.env` files are in `.gitignore`.
- AC3: The app fails at startup with a clear message when a required variable is missing.
- AC4: Frontend variables: `API_BASE_URL` (server) and `NEXT_PUBLIC_API_BASE_URL` (browser). The server-only URL does not appear in the browser bundle.

### REQ-NFR-02: Role-based access control
The API shall enforce RBAC and board membership on every board-scoped resource.

Acceptance criteria:
- AC1: For each board-scoped endpoint (boards, columns, cards, comments, analytics, search), a test with a non-member token expects `403`.
- AC2: For each admin-only endpoint (board update, board delete, membership changes, analytics), a test with a `member` token expects `403`.
- AC3: Authorization checks exist in `service.py` and do not depend on frontend state.
- AC4: A user who is `admin` on board X and `member` on board Y is treated as `member` on Y.
- AC5: Moving a card to a column of another board is rejected.

### REQ-NFR-03: HTTP status policy
The API shall use one consistent status-code policy.

Acceptance criteria:
- AC1: Missing, invalid, or expired token returns `401`.
- AC2: Authenticated but not permitted returns `403`.
- AC3: A missing resource returns `404`.
- AC4: A validation failure returns `400`.
- AC5: An unhandled exception returns `500` with `{"error": "Internal server error"}` and no stack trace in the body.

### REQ-NFR-04: Response envelope
Every endpoint shall use the standard envelope.

Acceptance criteria:
- AC1: Success responses are `{"data": ...}` for every endpoint, including `GET /api/health` (`{"data": {"status": "ok"}}`).
- AC2: Failure responses are `{"error": "<string>"}`. `error` is always a string.
- AC3: A Marshmallow `ValidationError` becomes a `400` with a readable string message.
- AC4: Central error handlers produce errors. Route functions do not build error responses by hand.
- AC5: `lib/apiClient.ts` returns `data` on success and throws a typed `ApiError` on non-2xx.

### REQ-NFR-05: Layered architecture
The backend shall follow the 3-layer blueprint structure.

Acceptance criteria:
- AC1: Each of `auth`, `users`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics` has `routes.py`, `service.py`, and `schema.py` under `app/blueprints/<feature>/`.
- AC2: A search for `db.session` and `Model.query` in `routes.py` files finds no matches.
- AC3: Business rules are unit-testable by calling `service.py` functions without an HTTP request.
- AC4: Input validation and serialization use Marshmallow schemas.

### REQ-NFR-06: Data model standards
The database shall follow the project data conventions.

Acceptance criteria:
- AC1: All primary keys and foreign keys are `String(36)` UUIDs generated by `uuid.uuid4`.
- AC2: Every model has `created_at`, `updated_at`, and `deleted_at` in UTC through a shared `AuditMixin`.
- AC3: No endpoint issues a SQL `DELETE` on application records. Deletion sets `deleted_at`.
- AC4: Every read query filters `deleted_at IS NULL` using `active()`.
- AC5: `board_members` has `UniqueConstraint(board_id, user_id)` and `CHECK role IN ('member','admin')`.
- AC6: `Card.assignee_id` is a nullable foreign key with `ondelete="SET NULL"`.
- AC7: `Card.completed_at` is nullable and indexed.

### REQ-NFR-07: FLOAT ordering
Ordering shall use `FLOAT` values in a column named `order`.

Acceptance criteria:
- AC1: `Column.order` and `Card.order` are `db.Float`, `nullable=False`. No `position` column exists.
- AC2: A first item gets `1000.0`. A new last item gets last + `1000.0`. A middle insert gets the midpoint.
- AC3: A gap below `1e-6` triggers a transactional rebalance of that scope (column for cards, board for columns), and the relative order is preserved.
- AC4: A unit test performs 50 consecutive midpoint insertions at the same spot, and the final order is strictly increasing with no duplicate values.

### REQ-NFR-08: Migrations
Schema changes shall be managed only through Flask-Migrate.

Acceptance criteria:
- AC1: `flask db upgrade` on an empty PostgreSQL database creates the full schema.
- AC2: `flask db migrate` on the upgraded database produces no further changes.
- AC3: `db.create_all()` is called only in test setup.
- AC4: Each model change is committed together with its migration revision.

### REQ-NFR-09: Database indexing and query efficiency
The database shall index frequently queried fields.

Acceptance criteria:
- AC1: Indexes exist on `cards(column_id, order)`, `cards.assignee_id`, `cards.completed_at`, `board_members.board_id`, `board_members.user_id`, `columns(board_id, order)`, `comments.card_id`, `notifications.recipient_id`, and every `deleted_at` column.
- AC2: Board fetch uses a constant number of queries regardless of card count (verified by a query-count test with 5 and 50 cards giving the same count).
- AC3: Analytics queries return aggregated rows only.

### REQ-NFR-10: Frontend performance
The UI shall avoid unnecessary requests and renders.

Acceptance criteria:
- AC1: Card search sends no more than one request per 300 ms idle period (REQ-SRC-02).
- AC2: Notification polling uses one timer (REQ-NTF-05).
- AC3: Drag-and-drop does not re-fetch the board after a successful move (REQ-CRD-08 AC5).
- AC4: Card and column components that receive unchanged props do not re-render when an unrelated card moves (verified with a render-count test or React Profiler).

### REQ-NFR-11: Responsive design
The UI shall work on desktop, tablet, and mobile.

Acceptance criteria:
- AC1: Playwright tests at 1280x800, 768x1024, and 375x667 viewports complete login, board view, and card creation.
- AC2: No horizontal page scroll occurs at 375 px width. The board's column area scrolls horizontally on its own.
- AC3: Interactive targets are at least 44x44 px on the mobile viewport.
- AC4: Modals fit within the mobile viewport and can be scrolled and closed.
- AC5: Layout uses Tailwind responsive utilities.

### REQ-NFR-12: Shared UI components
The UI shall use shared base components.

Acceptance criteria:
- AC1: A search for `<button` in `app/` and `components/` (excluding `components/shared/BaseButton.tsx`) finds no matches.
- AC2: `BaseButton` supports `primary`, `secondary`, and `destructive` variants.
- AC3: All status tags use `<BaseBadge>` and all form modals use `<BaseModal>`.
- AC4: Shared components live in `components/shared/`.

### REQ-NFR-13: Error handling in UI
The UI shall handle API errors in one place.

Acceptance criteria:
- AC1: `hooks/useErrorHandler.ts` maps an `ApiError` to a `react-hot-toast` message. Other code does not call `toast.error` with raw error objects.
- AC2: A `401` response clears the session and redirects to `/login`.
- AC3: A non-`ApiError` exception shows "Something went wrong".

### REQ-NFR-14: CORS
The API shall accept browser requests only from the configured frontend origin.

Acceptance criteria:
- AC1: A request with `Origin` equal to `FRONTEND_URL` receives a matching `Access-Control-Allow-Origin` header.
- AC2: A request from any other origin receives no `Access-Control-Allow-Origin` header.
- AC3: CORS applies to `/api/*`.

### REQ-NFR-15: Automated testing
Critical business logic and workflows shall have automated tests.

Acceptance criteria:
- AC1: Pytest covers every endpoint for its success path and its `400`, `401`, `403`, and `404` paths where applicable.
- AC2: Pytest covers the ordering functions, rebalancing, comment ownership, completion tracking, and analytics date boundaries.
- AC3: Playwright covers register, login, create board, create column, create card, drag-and-drop, comment, search, and notification display.
- AC4: Playwright tests do not use `page.waitForTimeout()`. They wait on locators or `page.waitForResponse`.
- AC5: The test suites run and pass in a clean checkout with documented commands.

### REQ-NFR-16: Deployment
The application shall deploy to the specified hosts.

Acceptance criteria:
- AC1: The backend runs under Gunicorn on Railway and connects to Railway PostgreSQL.
- AC2: The frontend builds and runs on Vercel.
- AC3: `GET /api/health` on the deployed backend returns `200` with `{"data": {"status": "ok"}}`.
- AC4: Migrations are applied as part of the backend release step.
- AC5: A deployed end-to-end smoke test (register, login, create board, and move a card) passes.

### REQ-NFR-17: Technology constraints
The project shall use only the technology stack in the brief.

Acceptance criteria:
- AC1: Backend dependencies include Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Marshmallow, Gunicorn, and Pytest, with PostgreSQL as the database. `Flask-CORS` is used for CORS.
- AC2: Frontend uses Next.js (App Router), React, TypeScript, Tailwind CSS, react-hot-toast, and Playwright.
- AC3: Any dependency outside this list has a written justification in `design.md`.

### REQ-NFR-18: Maintainability and conventions
The code shall be modular and consistently named.

Acceptance criteria:
- AC1: Frontend and backend live in separate top-level directories with no shared source imports.
- AC2: The frontend API contract types match backend response shapes (checked by an E2E or contract test).
- AC3: Frontend code passes `tsc --noEmit` and the configured linter. Backend code passes the configured linter.
- AC4: Repeated UI elements are reusable components and not copied.
