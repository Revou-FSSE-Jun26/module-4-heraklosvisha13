# Specification Refinement Changelog

This document records the iterative review and refinement process applied to `requirements.md`, `design.md`, and `tasks.md`.

---

## Refinement #1: Align move/reorder endpoints with the API contract

**Target Document:** `specs/requirements.md` (REQ-COL-04, REQ-CRD-06, REQ-CRD-07; REQ-CRD-03 AC4 cross-reference)

**Issue Identified:**
- REQ-CRD-06 specified `PATCH /api/cards/<id>/move` with `column_id`, `prev_id`, `next_id`. The contract requires `PATCH /api/cards/<id>/position` with a validated `column_id` (UUID) and `order` (positive float) via `CardPositionSchema`. The server was also specified to compute the midpoint from neighbor IDs, which the contract does not do.
- REQ-COL-04 specified `PATCH /api/columns/<id>/move` with `prev_id`/`next_id`. The contract requires `PATCH /api/boards/<id>/columns/reorder`.
- REQ-CRD-07 referenced the old `/move` route in its Playwright criterion (AC5) and did not say who computes `order` (AC4).

**Targeted Prompt:**
> Critically review `specs/requirements.md` against the exact API contract in the RevoTask assignment brief. REQ-CRD-06 uses `PATCH /api/cards/<id>/move` with `prev_id`/`next_id`, but the brief requires `PATCH /api/cards/<id>/position` with `column_id` (UUID) and `order` (positive float) validated by `CardPositionSchema`. REQ-COL-04 uses `PATCH /api/columns/<id>/move`, but the brief requires `PATCH /api/boards/<id>/columns/reorder`. Update REQ-CRD-06, REQ-CRD-07, and REQ-COL-04 to match the exact routes and payload contracts.

**Before:**
- REQ-CRD-06 AC1: `PATCH /api/cards/<id>/move` with `column_id`, `prev_id`, and `next_id` (neighbors may be null) returns `200` with the updated card.
- REQ-CRD-06 AC2/AC3/AC4/AC6: server computes midpoint from neighbors, rebalances when gap < `1e-6`, returns `400` for neighbors outside the target column.
- REQ-COL-04 AC1: `PATCH /api/columns/<id>/move` with `prev_id` and `next_id` (either may be null) sets `order` to the midpoint of the neighbors' orders.
- REQ-COL-04 AC4/AC5: rebalance when gap < `1e-6`; neighbors on another board return `400`.
- REQ-CRD-07 AC5: A Playwright test waits on the `/api/cards/<id>/move` response.

**After:**
- REQ-CRD-06 AC1: `PATCH /api/cards/<id>/position` with `column_id` (UUID) and `order` (positive float), validated by `CardPositionSchema`, returns `200` with the updated card.
- REQ-CRD-06 AC2: the client computes `order` from neighbors; the server stores the received value.
- REQ-CRD-06 AC4: rebalance triggers when the received `order` equals another active card's `order` in the target column.
- REQ-CRD-06 AC6: invalid `column_id` or `order` returns `400` with `CardPositionSchema` field errors.
- REQ-COL-04 AC1: `PATCH /api/boards/<id>/columns/reorder` with `column_id` (UUID) and `order` (positive float) returns `200` with the updated column.
- REQ-COL-04 AC4/AC5: rebalance on equal `order`; a `column_id` outside the board, or an invalid `order`, returns `400`.
- REQ-CRD-07 AC4: the hook computes `order` and calls `PATCH /api/cards/<id>/position`. AC5: Playwright waits on that response.
- REQ-CRD-03 AC4: cross-reference now names `/position`.

**Open items:**
- `project-brief.md` in this repo does not contain the route or payload text. The routes and card payload come from the assignment brief as quoted in the review request.
- The column reorder payload was not specified. It mirrors the card payload (`column_id`, `order`). Confirm against the brief.
- The equal-`order` rebalance trigger is an assumption, since the server no longer sees neighbors.
- `.kiro/steering/frontend.md` and `guidelines/frontend.md` (lines 100 and 202) still use `/api/cards/${cardId}/move`. Also `design.md` and `tasks.md` were not changed in this refinement.

---
## Refinement #2: Align dashboard route, assigned-tasks endpoint, notification pagination, and analytics endpoint

**Target Document:** `specs/requirements.md` (REQ-AUTH-05, REQ-BRD-10, REQ-TSK-01, REQ-TSK-02, REQ-NTF-01, REQ-ANL-01 to REQ-ANL-06)

**Issue Identified:**
- REQ-AUTH-05 and REQ-BRD-10 used `/boards` as the dashboard route. The brief requires `/`.
- REQ-TSK-01 and REQ-TSK-02 used `GET /api/my-tasks`. The brief requires `GET /api/cards?assignee=me`.
- REQ-NTF-01 did not define pagination for `GET /api/notifications`.
- REQ-ANL-01 to REQ-ANL-04 specified four analytics endpoints. The brief requires one endpoint, `GET /api/boards/<id>/analytics`, returning total cards per column, cards completed this week, and member activity.

**Targeted Prompt:**
> Review `specs/requirements.md` again for route mismatches against the RevoTask brief. The dashboard route must be `/` (not `/boards`) in REQ-AUTH-05 and REQ-BRD-10. The assigned tasks endpoint must be `GET /api/cards?assignee=me` (not `GET /api/my-tasks`) in REQ-TSK-01 and REQ-TSK-02. `GET /api/notifications` in REQ-NTF-01 must explicitly support `page` and `per_page`. Board analytics must be a single endpoint `GET /api/boards/<id>/analytics` returning total cards per column, cards completed this week, and member activity, instead of 4 separate endpoints in REQ-ANL-01 to REQ-ANL-04.

**Before:**
- REQ-AUTH-05 AC1/AC2: protected route list starts with `/boards`; logged-in users visiting `/login` or `/register` redirect to `/boards`.
- REQ-BRD-10 AC1: `/boards` lists the user's boards.
- REQ-TSK-01 AC1 and REQ-TSK-02 AC1: `GET /api/my-tasks`.
- REQ-NTF-01: AC1 to AC4 only. No pagination parameters.
- REQ-ANL-01: `GET /api/boards/<id>/analytics/cards-per-column`.
- REQ-ANL-02: `GET /api/boards/<id>/analytics/completed-this-week`.
- REQ-ANL-03: `GET /api/boards/<id>/analytics/member-activity`.
- REQ-ANL-04: `GET /api/boards/<id>/analytics/progress` (`total_cards`, `completed_cards`, `completion_percentage`).
- REQ-ANL-05 (access control) and REQ-ANL-06 (dashboard UI) referred to "each analytics endpoint" and to progress.

**After:**
- REQ-AUTH-05 AC1/AC2 and REQ-BRD-10 AC1: dashboard route is `/`.
- REQ-TSK-01 AC1 and REQ-TSK-02 AC1: `GET /api/cards?assignee=me`.
- REQ-NTF-01 AC5 to AC7: `page` (default `1`) and `per_page` (default `20`, max `100`) query parameters, pagination metadata (`page`, `per_page`, `total`, `pages`) in the response, `400` for invalid values, empty list beyond the last page.
- REQ-ANL-01: single `GET /api/boards/<id>/analytics` returning `cards_per_column`, `completed_this_week`, and `member_activity`. Per-metric routes return `404`.
- REQ-ANL-02 and REQ-ANL-03: now describe the `completed_this_week` and `member_activity` fields of that response.
- REQ-ANL-04 (progress) removed. Former REQ-ANL-05 and REQ-ANL-06 renumbered to REQ-ANL-04 and REQ-ANL-05, and reworded for the single endpoint. The dashboard no longer shows progress.

**Open items:**
- Pagination defaults (`page=1`, `per_page=20`, max `100`), the metadata field names, and `400` on invalid values are assumptions. Confirm against the brief.
- The `/my-tasks` UI page route (REQ-AUTH-05 AC1, REQ-TSK-03) was left unchanged because the brief items did not cover it.
- `GET /api/cards?assignee=me` has no board scope, so it is assumed to be the caller-scoped listing described in REQ-TSK-01. Also, REQ-TSK-02 counts in the same response are unchanged.
- Progress (REQ-ANL-04 before) was dropped because the brief lists only three analytics values.
- `.kiro/steering` and `guidelines` files, `design.md`, and `tasks.md` were not changed.

---
## Refinement #3: Restrict `PATCH /api/users/me` to name and email and remove the password endpoint

**Target Document:** `specs/requirements.md` (REQ-USER-02, REQ-USER-03)

**Issue Identified:**
- REQ-USER-03 specified `PATCH /api/users/me/password` with `current_password` and `new_password`. The brief does not include this endpoint, so it is out of scope.
- REQ-USER-02 did not say what happens when `password` is sent to `PATCH /api/users/me`. The brief requires `400 Bad Request`.

**Targeted Prompt:**
> `PATCH /api/users/me` updates only `name` and `email`. It must not change the password, and it must return `400 Bad Request` if `password` is included. Remove the out-of-scope `/api/users/me/password` route from `specs/requirements.md` (REQ-USER-02 and REQ-USER-03).

**Before:**
- REQ-USER-02: "update their own `name` and `email`". AC4 said `id`, `password_hash`, and `created_at` are ignored or rejected. Nothing covered `password`.
- REQ-USER-03 "Change password": AC1 `PATCH /api/users/me/password` returns `200` with a correct `current_password` and valid `new_password`. AC2 login works with the new password only. AC3 wrong `current_password` returns `400` or `403`. AC4 `new_password` under 8 characters returns `400`.

**After:**
- REQ-USER-02: the endpoint updates only `name` and `email`. AC4 states that a `password` field is always rejected (see REQ-USER-03).
- REQ-USER-03 is now "Password is not changeable through the profile endpoint". AC1: a `password` field in `PATCH /api/users/me` returns `400` with an `error` string. AC2: nothing is updated and `password_hash` is unchanged. AC3: `PATCH /api/users/me/password` is not defined and returns `404`. AC4: login still works with the original password.
- The `/api/users/me/password` endpoint and its `current_password` and `new_password` criteria are removed. REQ-USER-04 and REQ-USER-05 keep their numbers.

**Open items:**
- A request containing `password` is rejected as a whole, even when `name` or `email` is valid. This is an assumption. Confirm against the brief.
- `design.md` and `tasks.md` had no references to the removed endpoint and were not changed. `.kiro/steering` and `guidelines` files were also unchanged.
---
## Refinement #4: Document `CardPositionSchema` and the Server/Client Component data-fetching split

**Target Document:** `specs/design.md` (sections 1.3 D-04, 3.3, 3.5 Cards, 5.2, 5.5 to 5.8)

**Issue Identified:**
- `CardPositionSchema` appeared only as a label in the section 4.8 endpoint table. Its fields and validation rules were not documented under the Cards blueprint design, and section 3.3 said every `PATCH` schema loads with `partial=True`, which would make both fields optional.
- Section 5.2 stated that no page fetches authenticated data and that `API_BASE_URL` was unused. The brief requires `/` (Dashboard) and `/boards/[id]` (Board Detail) to be Server Components that fetch initial data through `API_BASE_URL`, while `CardDetailModal.tsx` and drag and drop are Client Components that use `NEXT_PUBLIC_API_BASE_URL`.
- The JWT lives in `localStorage` (A-02), which a Server Component cannot read, so the server fetch had no token.

**Targeted Prompt:**
> Review `specs/design.md` to verify two rubric-critical details. (1) Explicitly document `CardPositionSchema` (validating `column_id` as UUID and `order` as positive float > 0) under the Cards blueprint design. (2) Explicitly specify that `/` (Dashboard) and `/boards/[id]` (Board Detail) are Next.js Server Components that fetch initial data via `API_BASE_URL`, while `CardDetailModal.tsx` and drag-and-drop interactions are Client Components using `NEXT_PUBLIC_API_BASE_URL`. Update `specs/design.md` if needed.

**Before:**
- Section 4.8: `{"column_id": uuid, "order": float > 0}` (`CardPositionSchema`) in the table row only. No schema definition in section 3.5.
- Section 3.3: "Every `PATCH` schema is loaded with `partial=True`."
- D-04 and section 5.2: every `page.tsx` is a static shell with "no authenticated fetch". "In this design no page uses [`API_BASE_URL`] for authenticated data." `DashboardView` and `useBoard` fetched in the browser.

**After:**
- Section 3.5 Cards: new `CardPositionSchema(StrictSchema)` with `column_id = uuid_str(required=True)` and `order = order_field()` (float, `Range(min=0, min_inclusive=False)`, NaN rejected). It is loaded without `partial=True`. Missing fields, a non-UUID `column_id`, `order <= 0`, a non-number, or unknown keys return `400` before `move_card` runs. Section 3.3 points to it.
- Section 5.2: `/` and `/boards/[boardId]` are Server Components that read the `revotask_token` cookie, fetch `GET /api/boards` or `GET /api/boards/<id>` through `API_BASE_URL` (`cache: "no-store"`), and pass `initialBoards` or `initialBoard` to `DashboardView` or `BoardView`. `CardDetailModal.tsx` and the drag-and-drop code (`useDragAndDrop`, `CardItem`, `BoardColumn`) are Client Components that use `NEXT_PUBLIC_API_BASE_URL` and the `localStorage` token. Other pages and layouts stay static shells.
- D-04 and section 5.6: `AuthContext` mirrors the token to a `revotask_token` cookie on `login()` and removes it on `logout()`. If the cookie is missing or the server fetch fails, the page passes `null` and the client fetches as before.
- Section 5.8: `DashboardView`, `useBoard`, and `CardDetailModal` descriptions updated to match.

**Open items:**
- The cookie mirror is a design addition, not in the brief. It is not `HttpOnly` (JavaScript sets it), so its XSS exposure equals `localStorage`. An alternative is an `HttpOnly` cookie set by a Next.js route handler, which would change A-02. Confirm which the brief allows.
- `requirements.md` (A-02) and `tasks.md` were not changed. `tasks.md` needs tasks for the cookie, the server fetch in both pages, and `CardPositionSchema`.
- `.kiro/steering` and `guidelines` files were not changed.

---

## Refinement #5: Add explicit `BaseButton` enforcement and Playwright audit tasks

**Target Document:** `specs/tasks.md` (sections 5.2 and 6.2)

**Issue Identified:**
- The `BaseButton` rule appeared only inside FS-01 and FP-13 ("No raw `<button>` outside `BaseButton`"). No task checked `/my-tasks` or `/profile` specifically, and nothing enforced the rule automatically.
- The "no `page.waitForTimeout()`" rule was a note under section 6.2 with no task that checks it. No task required a `page.reload()` check that a dragged card keeps its position.

**Targeted Prompt:**
> Review `specs/tasks.md` and ensure there are explicit checklist tasks for (1) enforcing `<BaseButton>` usage across `/my-tasks` and `/profile` with zero raw `<button>` tags, and (2) auditing the Playwright E2E tests (`e2e/auth.spec.ts` and `e2e/kanban.spec.ts`) to confirm zero `page.waitForTimeout()` calls and verifying card position persistence after `page.reload()`.

**Before:**
- FP-10 (`/my-tasks`) and FP-11 (`/profile`) listed components only. FP-13 had one line: "No raw `<button>` outside `BaseButton`".
- Section 6.2 had the rule text "no `page.waitForTimeout()`" and no audit task. FT-11 step 5 asserted the card in the new column right after the drag, with no reload.

**After:**
- New task FP-14 with four sub-tasks: grep `/my-tasks` and `/profile` files for `<button`, replace hits with `<BaseButton>`, add an ESLint `no-restricted-syntax` rule that exempts only `BaseButton.tsx`, and add Vitest checks for `MyTasksView` and `ProfileForm`.
- New task FT-17 with five sub-tasks: grep `e2e/` for `waitForTimeout` (and fail CI on a match), add a `page.reload()` assertion to FT-11 step 5 that the card stays in the new column, assert order relative to neighbours after reload, and confirm `auth.spec.ts` uses only locator, URL, or response waits.

**Open items:**
- The request names `e2e/kanban.spec.ts`. The spec defines `e2e/kanban-journey.spec.ts` (FT-11), and FT-17 targets that file. Confirm whether to rename it.
- The ESLint rule and the CI grep step are additions beyond the request. Remove them if only a one-time audit is wanted.
- FT-11 itself was not edited. The reload check is carried by FT-17.
- `requirements.md`, `design.md`, `.kiro/steering`, and `guidelines` files were not changed.
