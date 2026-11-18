# Implementation Tasks: RevoTask

Source: `specs/design.md` (section numbers below refer to it) and `specs/requirements.md`.

How to read this file:
- Tasks run in order. Each task assumes the ones above it are done.
- Every task ends with a `Maps:` line naming the Flask route(s) (section 4) or Next.js page/component (section 5.1, 5.3) it implements or verifies. "Cross-cutting" tasks list the routes or pages they cover.
- Backend paths are relative to `backend/`, frontend paths to `frontend/`.
- Request order for every route is JWT (401), schema (400), service (404, 403, rules), then wrap in `{"data": ...}` (section 1.2). Use `get_active_or_404` for lookups (D-03).

Task ID prefixes: `BF` backend foundation, `AU` auth, `US` users, `BR` boards, `CO` columns, `CA` cards, `CM` comments, `NT` notifications, `AN` analytics, `BT` backend tests, `FF` frontend foundation, `FS` frontend shared components, `FH` hooks, `FP` pages, `FT` frontend tests, `DP` deployment.

Assumptions recorded here because `design.md` is silent (confirm or edit):
- A. `errors.ts` and `toast.ts` are not named in `design.md`. They are planned as `lib/errors.ts` (holds `ApiError` and a message mapper, re-exported from `apiClient.ts` so section 5.5 still holds) and `lib/toast.ts` (thin `react-hot-toast` wrapper). `useErrorHandler` stays the only caller of the error toast (steering rule).
- B. "4 auth scenarios" are: register success, login success, login with wrong password, and protected-route redirect plus logout.
- C. "8-step Kanban journey" is: login, create board, create column, create card, drag card to another column, comment, search, notification display (register is covered by the auth scenarios, per REQ-NFR AC at requirements line 786).

---

## 1. Backend Foundation, Models & Flask-Migrate Setup

- [ ] **BF-01 Project scaffold.** Create `backend/` per section 1.1: `app/`, `app/common/`, `app/models/`, `app/blueprints/{auth,users,boards,columns,cards,comments,notifications,analytics}/` (each with empty `__init__.py`, `routes.py`, `service.py`, `schema.py`), `migrations/`, `tests/`, `wsgi.py`. Create venv.
  Maps: cross-cutting, all 35 endpoints.
- [ ] **BF-02 Dependencies and tooling.** Write `requirements.txt` (Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS, marshmallow, psycopg2-binary, python-dotenv, gunicorn, pytest, ruff), `ruff.toml`, `.env.example` (`DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES`, `FRONTEND_URL`). Justify extras per section 1.4.
  Maps: cross-cutting (REQ-NFR-01, REQ-NFR-17, REQ-NFR-18).
- [ ] **BF-03 Config.** `app/config.py` loads env and raises at startup on any missing variable (section 3.1).
  Maps: `GET /api/health` and every route (app cannot start without config).
- [ ] **BF-04 Extensions.** `app/extensions.py` with `db`, `migrate`, `jwt`.
  Maps: cross-cutting.
- [ ] **BF-05 Model mixins.** `app/models/mixins.py`: `new_uuid`, `utcnow`, `AuditMixin` (`id`, `created_at`, `updated_at`, `deleted_at`, `active()`), section 2.1.
  Maps: cross-cutting, all soft-delete reads.
- [ ] **BF-06 `User` model.** `app/models/user.py`; lowercase unique email covering soft-deleted rows (D-12).
  Maps: `POST /api/auth/register`, `POST /api/auth/login`, `GET|PATCH /api/users/me`, `GET /api/users?email=`.
- [ ] **BF-07 `Board` and `BoardMember` models.** `board.py`, `board_member.py`; `UniqueConstraint(board_id, user_id)`, role enum `member|admin` (D-11).
  Maps: all 9 `/api/boards...` routes, `GET /api/boards/<id>/analytics`.
- [ ] **BF-08 `Column` model.** `column.py`; `order` float, FK to board.
  Maps: `/api/boards/<board_id>/columns` (GET, POST, PATCH `/reorder`), `PATCH|DELETE /api/columns/<id>`.
- [ ] **BF-09 `Card` model.** `card.py`; `column_id`, `assignee_id`, `due_date`, `order`, `completed_at`, `created_by_id` (nullable, `SET NULL`, D-08).
  Maps: `POST /api/columns/<column_id>/cards`, `GET /api/boards/<board_id>/cards`, `GET /api/cards`, `GET|PATCH|DELETE /api/cards/<id>`, `PATCH /api/cards/<id>/position`.
- [ ] **BF-10 `Comment` model.** `comment.py`; `card_id`, `author_id`, `body`.
  Maps: `GET|POST /api/cards/<card_id>/comments`, `PATCH|DELETE /api/comments/<id>`.
- [ ] **BF-11 `Notification` model.** `notification.py`; `recipient_id`, `actor_id`, `type`, `message`, `board_id`, `card_id`, `read_at`.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/read-all`, `PATCH /api/notifications/<id>/read`.
- [ ] **BF-12 Model registry and indexes.** `app/models/__init__.py` imports every model. Add the index inventory from section 2.4 (REQ-NFR-09 AC1).
  Maps: cross-cutting, `GET /api/boards/<id>`, `GET /api/boards/<board_id>/cards?q=`, `GET /api/cards?assignee=me`, `GET /api/boards/<id>/analytics`.
- [ ] **BF-13 Ordering module.** `app/ordering.py`: `ORDER_STEP`, `MIN_GAP`, `midpoint()`, `next_order()`, `needs_rebalance()`, `rebalance()` returning `[{"id","order"}]` (section 2.5, D-06).
  Maps: `POST /api/columns/<column_id>/cards`, `POST /api/boards/<board_id>/columns`, `PATCH /api/cards/<id>/position`, `PATCH /api/boards/<board_id>/columns/reorder`.
- [ ] **BF-14 Errors and envelope.** `app/errors.py`: `ApiError`, handlers for 400/401/403/404/500 returning `{"error": str}`, JWT callbacks (missing, expired, invalid token all give `401`), section 3.2.
  Maps: every protected route (401), all routes (error envelope).
- [ ] **BF-15 Shared helpers.** `app/common/schema.py` (`uuid_str()`, `order_field()`, `StrictSchema` with `unknown = RAISE`, error-message formatter, D-05) and `app/common/queries.py` (`get_active_or_404`).
  Maps: cross-cutting, all schemas and service lookups.
- [ ] **BF-16 App factory and health route.** `app/__init__.py` `create_app()`: config, extensions, CORS limited to `FRONTEND_URL`, register 8 blueprints under `/api`, error handlers, `GET /api/health`. `wsgi.py` exposes `app`.
  Maps: `GET /api/health`.
- [ ] **BF-17 Flask-Migrate init and first revision.** `flask db init`, `flask db migrate -m "initial schema"`, review the generated file (indexes, unique constraints, FKs), `flask db upgrade` on a local PostgreSQL.
  Maps: cross-cutting, all routes (schema exists).
- [ ] **BF-18 Authorization helper.** In `blueprints/boards/service.py`: `require_member(user_id, board_id, admin=False)` raising `403` (section 3.4).
  Maps: every board-scoped route (members: boards, columns, cards, comments, `GET /api/boards/<id>/analytics` admin).

## 2. Feature Blueprints (schema.py, service.py, routes.py)

Each blueprint is registered in `create_app()` (BF-16) with the URL prefix shown in section 4.

### 2.1 `auth` (section 4.4, domain rules section 3.5)

- [ ] **AU-01 `auth/schema.py`.** `RegisterSchema` (name 1-120, email, password 8-128), `LoginSchema` (email, password); extends `StrictSchema`.
  Maps: `POST /api/auth/register`, `POST /api/auth/login`.
- [ ] **AU-02 `auth/service.py`.** `register_user` (lowercase email, reject duplicates including soft-deleted with `400 "Email is already registered"`, `generate_password_hash`). `login_user` (load `User.active()`, dummy-hash check on unknown email for constant time, `401 "Invalid email or password"`, `create_access_token(identity=user.id)`).
  Maps: `POST /api/auth/register`, `POST /api/auth/login`.
- [ ] **AU-03 `auth/routes.py`.** `POST /register` returns `201 {"data": UserPublic}`. `POST /login` returns `200 {"data": {"access_token", "user"}}`. Both public.
  Maps: `POST /api/auth/register`, `POST /api/auth/login`.

### 2.2 `users` (section 4.5)

- [ ] **US-01 `users/schema.py`.** `UserUpdateSchema` (name 1-120, email; `password` key gives `"password: Password cannot be changed through this endpoint"`; other unknown keys rejected; empty body rejected). `UserLookupSchema` (`email` required query param).
  Maps: `PATCH /api/users/me`, `GET /api/users?email=`.
- [ ] **US-02 `users/service.py`.** `get_profile`, `update_profile` (lowercase email, duplicate check ignoring self), `find_by_email` (exact, case-insensitive, one user, `404` if none).
  Maps: `GET /api/users/me`, `PATCH /api/users/me`, `GET /api/users?email=`.
- [ ] **US-03 `users/routes.py`.** The three routes with `@jwt_required()`. `PATCH /api/users/me/password` is not defined and returns `404`.
  Maps: `GET /api/users/me`, `PATCH /api/users/me`, `GET /api/users?email=`.

### 2.3 `boards` (section 4.6)

- [ ] **BR-01 `boards/schema.py`.** `BoardCreateSchema`, `BoardUpdateSchema` (name 1-120), `MemberAddSchema` (email, optional role default `member`), `MemberRoleSchema` (role).
  Maps: `POST /api/boards`, `PATCH /api/boards/<id>`, `POST /api/boards/<id>/members`, `PATCH /api/boards/<id>/members/<user_id>`.
- [ ] **BR-02 `boards/service.py`, board CRUD.** `list_boards` (caller's active memberships), `create_board` (board plus admin `BoardMember` in one transaction), `get_board_detail` (4 constant queries, columns and cards sorted by `order`, assignee joined), `update_board` (admin), `delete_board` (admin, soft-delete cascade to columns, cards, comments by bulk `UPDATE`, A-08).
  Maps: `GET /api/boards`, `POST /api/boards`, `GET /api/boards/<id>`, `PATCH /api/boards/<id>`, `DELETE /api/boards/<id>`.
- [ ] **BR-03 `boards/service.py`, members.** `list_members`, `add_member` (admin; `404` unknown email; `400` already a member; restore soft-deleted row, D-11; create `board_member_added` notification), `change_role` and `remove_member` (admin; last-admin rule gives `400`; removal also clears the member's card assignments on that board).
  Maps: `GET /api/boards/<id>/members`, `POST /api/boards/<id>/members`, `PATCH /api/boards/<id>/members/<user_id>`, `DELETE /api/boards/<id>/members/<user_id>`.
- [ ] **BR-04 `boards/routes.py`.** All 9 routes with the roles in section 4.6. Delete returns `200 {"data": {"id"}}`.
  Maps: all 9 `/api/boards...` routes.

### 2.4 `columns` (section 4.7)

- [ ] **CO-01 `columns/schema.py`.** `ColumnCreateSchema`, `ColumnUpdateSchema` (name 1-120), `ColumnReorderSchema` (`column_id` uuid, `order` float > 0).
  Maps: `POST /api/boards/<board_id>/columns`, `PATCH /api/columns/<id>`, `PATCH /api/boards/<board_id>/columns/reorder`.
- [ ] **CO-02 `columns/service.py`.** `list_columns`, `create_column` (`next_order`), `rename_column`, `delete_column` (soft-delete column, its cards, their comments), `reorder_column` (`400` when column not on this board; rebalance; return `rebalanced`; no recompute of `completed_at`, D-10).
  Maps: `GET|POST /api/boards/<board_id>/columns`, `PATCH /api/boards/<board_id>/columns/reorder`, `PATCH|DELETE /api/columns/<id>`.
- [ ] **CO-03 `columns/routes.py`.** Five routes. Register `/reorder` so it is not shadowed by an `<id>` route. No endpoint changes `board_id`.
  Maps: all 5 column routes.

### 2.5 `cards` (section 4.8)

- [ ] **CA-01 `cards/schema.py`.** `CardCreateSchema` (title 1-200, optional description, assignee_id, due_date), `CardUpdateSchema` (any subset; empty body and `column_id`/`order` rejected), `CardPositionSchema` (`column_id` uuid, `order` float > 0, NaN rejected, required, not partial), `CardSearchSchema` (`q`), `MyTasksQuerySchema` (`assignee` must equal `me`).
  Maps: `POST /api/columns/<column_id>/cards`, `PATCH /api/cards/<id>`, `PATCH /api/cards/<id>/position`, `GET /api/boards/<board_id>/cards?q=`, `GET /api/cards?assignee=me`.
- [ ] **CA-02 `cards/service.py`, create/read/update/delete.** `create_card` (member check, assignee must be an active board member, `next_order`, set `created_by_id`, set `completed_at` in last column per D-09, notify assignee via `card_assigned`), `get_card_detail` (card, comments ascending, derived `activity` max 10 per section 3.6), `update_card` (notify only when assignee changes to another user), `delete_card` (soft delete plus comments).
  Maps: `POST /api/columns/<column_id>/cards`, `GET /api/cards/<id>`, `PATCH /api/cards/<id>`, `DELETE /api/cards/<id>`.
- [ ] **CA-03 `cards/service.py`, move.** `move_card` steps 1-6 of section 3.5: `404` card, `403` member, `404` column, `400` other-board target, write only the moved row, completion rule (set or clear `completed_at`), `needs_rebalance`/`rebalance`, single commit, return card plus `rebalanced` (D-06, D-13).
  Maps: `PATCH /api/cards/<id>/position`.
- [ ] **CA-04 `cards/service.py`, search and my tasks.** `search_cards` (escape `\`, `%`, `_`; match title or description case-insensitively; empty `q` returns all active cards), `list_my_tasks` (join Card, Column, Board, BoardMember with all `deleted_at IS NULL`; return `TaskList` with `total`, `completed`, `open`).
  Maps: `GET /api/boards/<board_id>/cards?q=`, `GET /api/cards?assignee=me`.
- [ ] **CA-05 `cards/routes.py`.** Seven routes from section 4.8. `GET /api/cards` with `assignee` missing or not `me` returns `400`.
  Maps: all 7 card routes.

### 2.6 `comments` (section 4.9)

- [ ] **CM-01 `comments/schema.py`.** `CommentCreateSchema`, `CommentUpdateSchema` (`body` 1-2000, strict).
  Maps: `POST /api/cards/<card_id>/comments`, `PATCH /api/comments/<id>`.
- [ ] **CM-02 `comments/service.py`.** `list_comments` (member, ascending `created_at`), `add_comment` (member; `author_id` from JWT; `comment_added` notification to assignee when assignee is not the author), `edit_comment` and `delete_comment` (`404` first, then `403` unless caller is the author, admins not exempt, delete is soft).
  Maps: `GET|POST /api/cards/<card_id>/comments`, `PATCH|DELETE /api/comments/<id>`.
- [ ] **CM-03 `comments/routes.py`.** Four routes with the status codes in section 4.9.
  Maps: all 4 comment routes.

### 2.7 `notifications` (section 4.10)

- [ ] **NT-01 `notifications/schema.py`.** `PaginationSchema` (`page` int >= 1 default 1, `per_page` int 1-100 default 20; non-integer, zero, negative, or > 100 gives `400`).
  Maps: `GET /api/notifications`.
- [ ] **NT-02 `notifications/service.py`.** `notify(...)` (add, no commit, skip when recipient equals actor), `list_notifications` (own only, newest first, `limit/offset`, returns `unread_count`, D-07), `mark_read` (`404`, `403` for another user's, idempotent), `mark_all_read` (single `UPDATE`, returns count). Message templates from section 3.5.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/read-all`, `PATCH /api/notifications/<id>/read`.
- [ ] **NT-03 `notifications/routes.py`.** Three routes. Register `/read-all` before `/<id>/read`.
  Maps: all 3 notification routes.

### 2.8 `analytics` (section 4.11)

- [ ] **AN-01 `analytics/schema.py`.** Response serialization schemas for `Analytics` (no request body). Keep the module for consistency with the other blueprints.
  Maps: `GET /api/boards/<id>/analytics`.
- [ ] **AN-02 `analytics/service.py`.** `week_start(now)` (Monday 00:00 UTC), `cards_per_column` (outer join, group by), `completed_this_week` (inclusive `>= start`), `member_activity` (three grouped subqueries, outer-joined, zeros for idle members). `get_analytics(user_id, board_id, now=None)` loads board (`404`) then `require_member(admin=True)` (`403`). No card rows loaded into Python.
  Maps: `GET /api/boards/<id>/analytics`.
- [ ] **AN-03 `analytics/routes.py`.** One admin-only route returning `200 {"data": Analytics}`.
  Maps: `GET /api/boards/<id>/analytics`.

## 3. Backend Pytest Suite

Uses a test database (PostgreSQL, or SQLite only if the models stay portable), applied through migrations. Remember section 1.2: send a valid body in `403` tests, otherwise `400` wins.

- [ ] **BT-01 Test harness.** `tests/conftest.py`: app fixture with test config, DB create/drop, `client`, factory helpers (`make_user`, `make_board`, `make_column`, `make_card`, `make_comment`), `auth_headers(user)`, `freeze_time` helper for analytics.
  Maps: cross-cutting, all routes.
- [ ] **BT-02 Health and error envelope.** `GET /api/health` returns `200`. Unknown route returns `404` JSON. Forced exception returns `500 {"error": "Internal server error"}`. Missing, malformed, and expired token each return `401` JSON.
  Maps: `GET /api/health`, every protected route (401).
- [ ] **BT-03 Ordering unit tests.** `tests/test_ordering.py`: `midpoint`, `next_order`, `needs_rebalance` threshold, `rebalance` result shape.
  Maps: `PATCH /api/cards/<id>/position`, `PATCH /api/boards/<board_id>/columns/reorder`.
- [ ] **BT-04 Auth tests.** Register `201`; `400` for missing field, bad email, short password, duplicate email in a different case; password stored hashed. Login `200` with token whose `sub` is the user id; `400` missing field; `401` for wrong password, unknown email, soft-deleted user (same message).
  Maps: `POST /api/auth/register`, `POST /api/auth/login`.
- [ ] **BT-05 Users tests.** `GET /me` `200` and `401`. `PATCH /me` `200`; `400` for empty name, invalid or duplicate email, `password` key, `id` key, empty body; `401`. `GET /users?email=` `200` case-insensitive, `400` missing email, `404` unknown, `401`. `PATCH /api/users/me/password` returns `404`.
  Maps: `GET|PATCH /api/users/me`, `GET /api/users?email=`.
- [ ] **BT-06 Boards tests.** List (empty and populated), create `201` role `admin`, `400` bad name. Detail `200` shape and order, `403` non-member, `404` unknown or soft-deleted. Rename and delete: `200` admin, `403` plain member, `401`. Delete cascades `deleted_at` to columns, cards, comments. Query count for detail stays constant.
  Maps: `GET|POST /api/boards`, `GET|PATCH|DELETE /api/boards/<id>`.
- [ ] **BT-07 Board members tests.** List `200`/`403`. Add: `201` default role, `400` invalid role or duplicate, `404` unknown email, `403` non-admin, restore after removal (D-11), notification created. Change role and remove: `200`, `400` last admin, `404` unknown member, `403` non-admin.
  Maps: `/api/boards/<id>/members`, `/api/boards/<id>/members/<user_id>`.
- [ ] **BT-08 Columns tests.** List sorted. Create `201` with increasing `order`, `400` empty name. Rename and delete `200` with cascade. Reorder `200` with `rebalanced`, `400` column from another board. `401`, `403`, `404` on each route.
  Maps: all 5 column routes.
- [ ] **BT-09 Cards CRUD tests.** Create `201`; `400` missing title or non-member assignee; `403`; `404`; card in last column gets `completed_at` (D-09); assignee notification. Get detail `200` with comments and activity (max 10, newest first). Update `200`; `400` for empty title, `column_id`, `order`, empty body, non-member assignee. Delete `200`.
  Maps: `POST /api/columns/<column_id>/cards`, `GET|PATCH|DELETE /api/cards/<id>`.
- [ ] **BT-10 Card move tests.** `200` same-column reorder and cross-column move; `completed_at` set on move to last column and cleared on move out; `400` for missing field, non-UUID, `order <= 0`, NaN, unknown key, other-board column; `403`; `404` card and column; rebalance response after tiny gap; exact collision places the moved card after (D-13); exactly one row written.
  Maps: `PATCH /api/cards/<id>/position`.
- [ ] **BT-11 Card search and My Tasks tests.** Search matches title and description case-insensitively, escapes `%` `_` `\`, empty `q` returns all, `403` non-member. My tasks returns only own, active cards on boards the user still belongs to, correct `total`, `completed`, `open`; `400` when `assignee` missing or not `me`; `401`.
  Maps: `GET /api/boards/<board_id>/cards?q=`, `GET /api/cards?assignee=me`.
- [ ] **BT-12 Comments tests (explicit status codes).** File `tests/test_comments.py`.
  - [ ] **201**: member `POST /api/cards/<card_id>/comments` returns `201` with `author_id` from the JWT; assignee gets a `comment_added` notification; author-is-assignee creates none.
  - [ ] **400**: missing `body`, empty `body`, `body` of 2001 chars, unknown key on `POST`; same on `PATCH /api/comments/<id>`.
  - [ ] **401**: no token, bad token on `GET`, `POST`, `PATCH`, `DELETE`.
  - [ ] **403**: non-member `GET` and `POST` (valid body); non-author member `PATCH` and `DELETE`; board admin who is not the author `PATCH` and `DELETE` (admins not exempt).
  - [ ] Also: `404` for unknown card or comment, `GET` sorted ascending, `PATCH` and `DELETE` return `200` for the author, deleted comment disappears from list.
  Maps: `GET|POST /api/cards/<card_id>/comments`, `PATCH|DELETE /api/comments/<id>`.
- [ ] **BT-13 Notifications tests.** List only own, newest first, `unread_count` independent of page, pagination metadata, `400` for `page=0`, `page=abc`, `per_page=101`; `401`. `read-all` returns `updated` count and affects only the caller. `<id>/read` `200`, idempotent (original `read_at` kept), `403` for another user's, `404`. No notification when actor equals recipient.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/read-all`, `PATCH /api/notifications/<id>/read`.
- [ ] **BT-14 Analytics tests.** Admin `200` with correct `cards_per_column` (including empty columns), `completed_this_week` boundary (card completed one second before `week_start` excluded), `member_activity` zeros for idle members; `403` for plain member and non-member; `404`; `401`.
  Maps: `GET /api/boards/<id>/analytics`.
- [ ] **BT-15 Lint and coverage gate.** `ruff check .` clean. `pytest` passes. Record the coverage figure for services and routes.
  Maps: cross-cutting (REQ-NFR-18 AC3).

## 4. Frontend Foundation & Shared Components

- [ ] **FF-01 Scaffold.** `create-next-app` (Next.js 15, App Router, TypeScript, Tailwind, ESLint) in `frontend/`. Add `react-hot-toast`, Vitest, `@testing-library/react`, `jsdom`, Playwright. Create `.env.example` (`API_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL`), `vitest.config.ts`, `playwright.config.ts`, directories from section 5.3.
  Maps: cross-cutting, all pages in section 5.1.
- [ ] **FF-02 `lib/types.ts`.** All types from section 4.2 with `snake_case` keys (D-02), plus `ColumnWithCards`.
  Maps: all pages (`/`, `/boards/[boardId]`, `/boards/[boardId]/analytics`, `/my-tasks`, `/profile`).
- [ ] **FF-03 `lib/errors.ts`.** `ApiError` class (`status`, `message`) and `getErrorMessage(err)` returning the API message for `ApiError` or `"Something went wrong"` otherwise. Re-exported from `apiClient.ts` (assumption A).
  Maps: cross-cutting, every page that calls the API.
- [ ] **FF-04 `lib/apiClient.ts`.** `apiClient<T>(path, token?, init?)` per section 5.5: `API_BASE_URL` on the server, `NEXT_PUBLIC_API_BASE_URL` in the browser, Bearer header, unwraps `data`, throws `ApiError`. Add ESLint `no-restricted-globals` for `fetch` with an override for this file.
  Maps: cross-cutting, all routes consumed by the UI.
- [ ] **FF-05 `lib/toast.ts`.** Wrapper exporting `showError`, `showSuccess` over `react-hot-toast`. Used by `useErrorHandler` and success paths.
  Maps: `/login`, `/register`, `/profile`, `/boards/[boardId]` (success and error toasts).
- [ ] **FF-06 `lib/ordering.ts`.** `ORDER_STEP`, `computeOrder(siblings, index)` (section 5.7).
  Maps: `PATCH /api/cards/<id>/position`, page `/boards/[boardId]`.
- [ ] **FF-07 `context/AuthContext.tsx`.** `AuthProvider` and `useAuth()` per section 5.6: `status`, `token`, `user`, `login`, `logout`, `setUser`. `localStorage["revotask.token"]` plus the `revotask_token` cookie (D-04). On mount load `GET /api/users/me`.
  Maps: `POST /api/auth/login`, `GET /api/users/me`, pages `/login`, `/register`, every `(app)` page.
- [ ] **FF-08 Layout components.** `components/layout/Providers.tsx` (AuthProvider and Toaster wiring), `AuthGate.tsx` (loading placeholder, redirect to `/login`), `GuestGate.tsx` (redirect to `/`).
  Maps: `app/(auth)/layout.tsx` for `/login` and `/register`; `app/(app)/layout.tsx` for `/`, `/boards/[boardId]`, `/boards/[boardId]/analytics`, `/my-tasks`, `/profile`.
- [ ] **FS-01 `BaseButton`.** Variants `primary|secondary|destructive`, `loading`, default `type="button"`. The only raw `<button>` in the app.
  Maps: every page; first used by `/login`.
- [ ] **FS-02 `BaseBadge`.** Tones `neutral|success|warning|danger`; no state, no handlers.
  Maps: `/` (role badge), `/boards/[boardId]` (Done/Open), `/my-tasks`, `NotificationBell`.
- [ ] **FS-03 `BaseModal`.** `role="dialog"`, `aria-modal`, `aria-labelledby`, closes on Escape and backdrop click, `max-h-[90vh] overflow-y-auto`.
  Maps: `/` (CreateBoardModal), `/boards/[boardId]` (card, column, members, confirm modals).
- [ ] **FS-04 Form controls.** `BaseInput`, `BaseTextarea`, `BaseSelect` with `label` bound via `useId`.
  Maps: `/login`, `/register`, `/profile`, `/boards/[boardId]` (CardFormModal).
- [ ] **FS-05 `ConfirmDialog`.** `BaseModal` with secondary cancel and destructive confirm.
  Maps: `DELETE /api/boards/<id>`, `DELETE /api/columns/<id>`, `DELETE /api/cards/<id>`, `DELETE /api/comments/<id>`.

## 5. Frontend Custom Hooks & All Pages

### 5.1 Hooks

- [ ] **FH-01 `hooks/useDebouncedValue.ts`.** `setTimeout` per change, cleared on change and unmount.
  Maps: page `/boards/[boardId]` (search), `GET /api/boards/<board_id>/cards?q=`.
- [ ] **FH-02 `hooks/useBoard.ts`.** Board state seeded from `initialBoard`, browser fetch when `null`, `setColumns`, and `addColumn|renameColumn|removeColumn|addCard|updateCard|removeCard`. New objects only for changed columns and cards.
  Maps: page `/boards/[boardId]`; `GET /api/boards/<id>`, column and card CRUD routes.
- [ ] **FH-03 `hooks/useErrorHandler.ts`.** `ApiError` 401 calls `logout()` then toasts; other `ApiError` shows its message; anything else shows "Something went wrong". Uses `lib/errors.ts` and `lib/toast.ts`.
  Maps: cross-cutting, every protected route (401), all pages.
- [ ] **FH-04 `hooks/useDragAndDrop.ts`.** Native HTML5 DnD, `columnsRef`, `draggingId`, `overColumnId`, `getCardProps`, `getColumnProps`, optimistic update, rollback on error, `applyServerCard` (takes `completed_at` and `rebalanced`), no board re-fetch.
  Maps: `PATCH /api/cards/<id>/position`, page `/boards/[boardId]`.
- [ ] **FH-05 `hooks/useNotifications.ts`.** `NotificationsProvider` with one 30 s `setInterval`, cleanup on unmount, silent poll failures, `markRead`, `markAllRead`, `unread` from `unread_count`.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/<id>/read`, `PATCH /api/notifications/read-all`, `app/(app)/layout.tsx`.
- [ ] **FH-06 `hooks/useCardSearch.ts`.** 300 ms debounce, `AbortSignal`, `matchIds` null when empty, `isEmpty`.
  Maps: `GET /api/boards/<board_id>/cards?q=`, page `/boards/[boardId]`.

### 5.2 Pages and their components

- [ ] **FP-01 `/login`.** `app/(auth)/login/page.tsx`, `app/(auth)/layout.tsx`, `LoginForm`. Calls `POST /api/auth/login`, then `login()`.
  Maps: `POST /api/auth/login`; `/login`.
- [ ] **FP-02 `/register`.** `app/(auth)/register/page.tsx`, `RegisterForm`. `POST /api/auth/register` then follow-up login, success toast.
  Maps: `POST /api/auth/register`, `POST /api/auth/login`; `/register`.
- [ ] **FP-03 Root layout and app shell.** `app/layout.tsx` (fonts, `Providers`, `Toaster`), `app/(app)/layout.tsx` (`AuthGate`, `NotificationsProvider`, `AppHeader`), `AppHeader` (logo, links, `NotificationBell`, profile link, logout), `NotificationBell`, `NotificationList`.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/<id>/read`, `PATCH /api/notifications/read-all`; all `(app)` pages.
- [ ] **FP-04 `/` dashboard.** Server Component `app/(app)/page.tsx` reads the `revotask_token` cookie and fetches `GET /api/boards` with `cache: "no-store"`. `DashboardView`, `BoardList`, `BoardListItem` (role badge), `CreateBoardModal`. Browser fallback when the server fetch returns `null`.
  Maps: `GET /api/boards`, `POST /api/boards`; `/`.
- [ ] **FP-05 `/boards/[boardId]` board view.** Server Component `app/(app)/boards/[boardId]/page.tsx` (awaits `params`, reads cookie, `GET /api/boards/<id>`). `BoardView`, `BoardHeader` (admin-only rename, delete, members, analytics link), `RenameBoardModal`, `MembersModal`, `BoardColumn` (memo), `ColumnFormModal`, `CardItem` (memo), `CardSearchInput`.
  Maps: `GET|PATCH|DELETE /api/boards/<id>`, `GET|POST /api/boards/<id>/members`, `PATCH|DELETE /api/boards/<id>/members/<user_id>`, `GET /api/users?email=`, `GET|POST /api/boards/<board_id>/columns`, `PATCH|DELETE /api/columns/<id>`, `GET /api/boards/<board_id>/cards?q=`; `/boards/[boardId]`.
- [ ] **FP-06 Card create, edit, detail.** `CardFormModal`, `AssigneeSelect`, `CardDetailModal` (opens on `?card=<id>`, browser `GET /api/cards/<id>`, activity list, edit and delete with `ConfirmDialog`).
  Maps: `POST /api/columns/<column_id>/cards`, `GET|PATCH|DELETE /api/cards/<id>`; `/boards/[boardId]?card=<id>`.
- [ ] **FP-07 Comments UI.** `CommentList`, `CommentItem` (edit and delete only when `author_id === user.id`), `CommentForm`.
  Maps: `GET|POST /api/cards/<card_id>/comments`, `PATCH|DELETE /api/comments/<id>`; `/boards/[boardId]?card=<id>`.
- [ ] **FP-08 Drag and drop wiring.** `BoardView` applies `useDragAndDrop` props to `BoardColumn` and `CardItem`; Done badge updates from the server `completed_at`.
  Maps: `PATCH /api/cards/<id>/position`; `/boards/[boardId]`.
- [ ] **FP-09 `/boards/[boardId]/analytics`.** `app/(app)/boards/[boardId]/analytics/page.tsx`, `AnalyticsView`, `CardsPerColumnBars` (div bars), `MemberActivityTable`. `403` shows a toast via `useErrorHandler`.
  Maps: `GET /api/boards/<id>/analytics`; `/boards/[boardId]/analytics`.
- [ ] **FP-10 `/my-tasks`.** `app/(app)/my-tasks/page.tsx`, `MyTasksView`, `TaskProgress`, `TaskListItem` (grouped by `board_name`, empty state, links to `/boards/<board_id>?card=<id>`).
  Maps: `GET /api/cards?assignee=me`; `/my-tasks`.
- [ ] **FP-11 `/profile`.** `app/(app)/profile/page.tsx`, `ProfileForm` (`PATCH /api/users/me` with `name`, `email` only; `setUser` and toast on success).
  Maps: `GET|PATCH /api/users/me`; `/profile`.
- [ ] **FP-12 Responsive pass.** Check `/login`, `/boards/[boardId]`, and card creation at 1280x800, 768x1024, 375x667. Only the column row scrolls horizontally.
  Maps: `/login`, `/boards/[boardId]`, `POST /api/columns/<column_id>/cards`.
- [ ] **FP-13 Frontend lint and build.** `next lint` and `next build` pass. No raw `<button>` outside `BaseButton`, no `fetch` outside `apiClient`.
  Maps: cross-cutting (REQ-NFR-12, REQ-NFR-18 AC3).
- [ ] **FP-14 Enforce `BaseButton` on `/my-tasks` and `/profile`.** Zero raw `<button>` tags in `app/(app)/my-tasks/page.tsx`, `MyTasksView`, `TaskProgress`, `TaskListItem`, `app/(app)/profile/page.tsx`, and `ProfileForm`.
  - [ ] Run `grep -rn "<button" app/(app)/my-tasks app/(app)/profile components/tasks components/profile`; the result is empty.
  - [ ] Replace every interactive control found (for example the `ProfileForm` save action and any retry or filter control) with `<BaseButton>`, using a `variant` and `loading` where it applies.
  - [ ] Add an ESLint `no-restricted-syntax` rule on `JSXOpeningElement[name.name='button']`, with an override that exempts only `components/shared/BaseButton.tsx`, so `next lint` fails on any raw `<button>`.
  - [ ] Add a Vitest check for `MyTasksView` and `ProfileForm` that `container.querySelectorAll("button")` all carry the `BaseButton` markup, with no unstyled raw buttons.
  Maps: pages `/my-tasks`, `/profile`; `GET /api/cards?assignee=me`, `GET|PATCH /api/users/me` (REQ-NFR-12).

## 6. React Testing Library (Vitest) & Playwright E2E Suite

### 6.1 Unit and component tests (Vitest, `@testing-library/react`, fake timers)

- [ ] **FT-01 `tests/ordering.test.ts`.** `computeOrder` for empty list, index 0, last index, middle.
  Maps: `PATCH /api/cards/<id>/position`; `/boards/[boardId]`.
- [ ] **FT-02 `tests/useDebouncedValue.test.ts`.** Value updates only after the delay; timer cleared on unmount.
  Maps: `GET /api/boards/<board_id>/cards?q=`; `/boards/[boardId]`.
- [ ] **FT-03 `tests/useCardSearch.test.tsx`.** Five keystrokes within 300 ms give one request; empty query sends none and returns `matchIds = null`; zero matches sets `isEmpty`.
  Maps: `GET /api/boards/<board_id>/cards?q=`; `/boards/[boardId]`.
- [ ] **FT-04 `tests/useNotifications.test.tsx`.** Polls every 30 s, a single timer, interval cleared on unmount and on logout, failed poll shows no toast, `markRead` lowers `unread` only for unread items.
  Maps: `GET /api/notifications`, `PATCH /api/notifications/<id>/read`; `app/(app)/layout.tsx`.
- [ ] **FT-05 `tests/BoardColumn.render.test.tsx`.** Moving one card does not re-render untouched `CardItem`s.
  Maps: `/boards/[boardId]`; `PATCH /api/cards/<id>/position`.
- [ ] **FT-06 `tests/useDragAndDrop.test.tsx`.** Optimistic update before response, rollback on error, `401` triggers logout, `rebalanced` orders applied, no board re-fetch.
  Maps: `PATCH /api/cards/<id>/position`; `/boards/[boardId]`.
- [ ] **FT-07 `tests/useErrorHandler.test.tsx` and `tests/apiClient.test.ts`.** 401 calls `logout()`; non-`ApiError` shows "Something went wrong"; `apiClient` picks the correct base URL, unwraps `data`, throws `ApiError` with the server message.
  Maps: cross-cutting, every protected route.
- [ ] **FT-08 `tests/CommentItem.test.tsx`.** Edit and delete controls render only for the author.
  Maps: `PATCH|DELETE /api/comments/<id>`; `/boards/[boardId]?card=<id>`.
- [ ] **FT-09 `tests/AuthGate.test.tsx`.** Loading placeholder, redirect to `/login` when unauthenticated, children when authenticated; `GuestGate` reverse.
  Maps: `GET /api/users/me`; `/login`, `/register`, `/`.

### 6.2 Playwright E2E (`e2e/`)

Rules: no `page.waitForTimeout()`. Wait on locators or `page.waitForResponse`. Use `page.clock` for the 30 s poll. Seed each test with unique emails.

- [ ] **FT-10 `e2e/auth.spec.ts`, four scenarios.**
  - [ ] Register a new user and land on `/`.
  - [ ] Log in with valid credentials and see the dashboard.
  - [ ] Log in with a wrong password and see the error toast, stay on `/login`.
  - [ ] Open `/` without a token and get redirected to `/login`; after login, log out and get redirected again.
  Maps: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/users/me`; `/register`, `/login`, `/`.
- [ ] **FT-11 `e2e/kanban-journey.spec.ts`, eight steps in one test.**
  1. Log in (seeded user).
  2. Create a board on `/` (`POST /api/boards`).
  3. Create a column (`POST /api/boards/<board_id>/columns`), then a second one.
  4. Create a card (`POST /api/columns/<column_id>/cards`).
  5. Drag the card to the second column; wait on `waitForResponse` for `PATCH /api/cards/<id>/position`; assert the card is in the new column.
  6. Open the card (`?card=<id>`) and add a comment (`POST /api/cards/<card_id>/comments`).
  7. Search by the card title (`GET /api/boards/<board_id>/cards?q=`); non-matching cards are hidden.
  8. Notification display: a second user assigns or comments, `page.clock` advances 30 s, the bell badge shows the unread count (`GET /api/notifications`).
  Maps: routes named per step; pages `/`, `/boards/[boardId]`, `/boards/[boardId]?card=<id>`.
- [ ] **FT-12 `e2e/drag-card.spec.ts`.** Optimistic move with the response delayed through `page.route`; rollback on a forced `500`; Done badge appears when dropped in the last column.
  Maps: `PATCH /api/cards/<id>/position`; `/boards/[boardId]`.
- [ ] **FT-13 `e2e/responsive.spec.ts`.** Login, board view, and card creation at 1280x800, 768x1024, 375x667.
  Maps: `POST /api/auth/login`, `GET /api/boards/<id>`, `POST /api/columns/<column_id>/cards`; `/login`, `/boards/[boardId]`.
- [ ] **FT-14 `e2e/contract.spec.ts`.** For each type in section 4.2 define a `*_KEYS satisfies Record<keyof T, true>` object; call the live API and assert response keys equal the key list.
  Maps: `GET /api/boards/<id>`, `GET /api/cards/<id>`, `GET /api/notifications`, `GET /api/cards?assignee=me`, `GET /api/boards/<id>/analytics`, `GET /api/boards/<id>/members`, `GET /api/users/me`.
- [ ] **FT-15 Extra specs from section 5.9 (optional beyond the 4 + 8 scope).** `board.spec.ts`, `comments.spec.ts`, `search.spec.ts`, `notifications.spec.ts` split out if `kanban-journey.spec.ts` becomes too long.
  Maps: pages `/boards/[boardId]`, `/`.
- [ ] **FT-16 CI-style full run.** Run backend `pytest`, Vitest, and Playwright against a local stack; all green.
  Maps: cross-cutting.
- [ ] **FT-17 Audit Playwright specs for `waitForTimeout` and card position persistence.** Covers `e2e/auth.spec.ts` and the kanban spec. The design names it `e2e/kanban-journey.spec.ts` (FT-11); there is no `e2e/kanban.spec.ts`. Include `drag-card.spec.ts` in the audit as well.
  - [ ] Run `grep -rn "waitForTimeout" e2e/`; the result is empty. Replace any hit with a locator assertion, `expect.poll`, or `page.waitForResponse`.
  - [ ] Add a CI step that runs the same grep and fails on any match.
  - [ ] In `kanban-journey.spec.ts` step 5, after the `PATCH /api/cards/<id>/position` response and the in-column assertion, call `page.reload()` and assert the card is still in the second column (`GET /api/boards/<id>`).
  - [ ] Also assert the card's order relative to its neighbours after `page.reload()`, for a drop between two cards, not only a drop into an empty column.
  - [ ] Confirm `auth.spec.ts` waits only on locators, URL assertions (`toHaveURL`), or `waitForResponse`.
  Maps: `PATCH /api/cards/<id>/position`, `GET /api/boards/<id>`; pages `/login`, `/register`, `/`, `/boards/[boardId]`.

## 7. Production Deployment (Railway & Vercel)

- [ ] **DP-01 Backend production config.** Confirm `wsgi.py`, `gunicorn wsgi:app --bind 0.0.0.0:$PORT`, and that `requirements.txt` includes `gunicorn` and `psycopg2-binary`.
  Maps: `GET /api/health` (liveness) and all backend routes.
- [ ] **DP-02 `railway.json`.** Set the start command and pre-deploy `flask db upgrade`. Check the exact keys against current Railway docs first (open item 3).
  Maps: cross-cutting (migrations for every route).
- [ ] **DP-03 Railway service.** Create the project, add PostgreSQL, set `DATABASE_URL`, `JWT_SECRET_KEY` (random, not committed), `JWT_ACCESS_TOKEN_EXPIRES`, `FRONTEND_URL` (Vercel origin, set after DP-05). Deploy `backend/`.
  Maps: `GET /api/health`, `POST /api/auth/register`.
- [ ] **DP-04 Backend smoke test.** `curl /api/health`, register, login, create board against the Railway URL; confirm CORS allows only the Vercel origin.
  Maps: `GET /api/health`, `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/boards`.
- [ ] **DP-05 Vercel project.** Import the repo with root directory `frontend/`. Set `API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` to the Railway URL. Deploy, then update Railway `FRONTEND_URL` to the Vercel origin and redeploy.
  Maps: all pages in section 5.1.
- [ ] **DP-06 Production smoke test.** On the Vercel URL: register, create board, column, card, drag, comment, check notification bell. Verify the server-rendered `/` and `/boards/[boardId]` receive data via the cookie.
  Maps: `/register`, `/`, `/boards/[boardId]`, `PATCH /api/cards/<id>/position`, `POST /api/cards/<card_id>/comments`, `GET /api/notifications`.
- [ ] **DP-07 Run Playwright against production (read-safe).** Point `playwright.config.ts` at the Vercel URL and run `auth.spec.ts` and `kanban-journey.spec.ts` with throwaway users.
  Maps: pages `/login`, `/register`, `/`, `/boards/[boardId]`.
- [ ] **DP-08 Docs.** Document env variables, deploy steps, and the touch-device DnD limitation (open item 2) in `README.md`.
  Maps: cross-cutting.
