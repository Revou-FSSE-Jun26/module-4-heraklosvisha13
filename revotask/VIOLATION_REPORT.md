# Violation Report

Audit of `backend/app/blueprints/` and `backend/app/models/` against `guidelines/backend.md` and `guidelines/database.md` (identical to `.kiro/steering/backend.md` and `.kiro/steering/database.md`). All violations below are fixed in place.

## Violation #1: Board cascade-delete subqueries skip the soft-delete filter

- **File Location:** `backend/app/blueprints/boards/service.py` (`delete_board`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
      column_ids = db.session.query(Column.id).filter(Column.board_id == board.id)
      card_ids = db.session.query(Card.id).filter(Card.column_id.in_(column_ids))
  ```

- **Fix Applied (After Fix):**

  ```python
      column_ids = db.session.query(Column.id).filter(
          Column.board_id == board.id, Column.deleted_at.is_(None)
      )
      card_ids = db.session.query(Card.id).filter(
          Card.column_id.in_(column_ids), Card.deleted_at.is_(None)
      )
  ```

## Violation #2: Column cascade-delete subquery skips the soft-delete filter

- **File Location:** `backend/app/blueprints/columns/service.py` (`delete_column`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
      card_ids = db.session.query(Card.id).filter(Card.column_id == column.id)
  ```

- **Fix Applied (After Fix):**

  ```python
      card_ids = db.session.query(Card.id).filter(
          Card.column_id == column.id, Card.deleted_at.is_(None)
      )
  ```

## Violation #3: Registration email check uses an unfiltered User.query

- **File Location:** `backend/app/blueprints/auth/service.py` (`register`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
      # Plain query on purpose: the unique index also covers soft-deleted users.
      if User.query.filter_by(email=payload["email"]).first() is not None:
  ```

- **Fix Applied (After Fix):**

  ```python
      # The unique index also covers soft-deleted users; the IntegrityError
      # handler below turns that case into the same 400.
      if User.active().filter_by(email=payload["email"]).first() is not None:
  ```

## Violation #4: Profile email-uniqueness check uses an unfiltered User.query

- **File Location:** `backend/app/blueprints/users/service.py` (`update_current_user`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
          # Plain query: the unique index also covers soft-deleted users.
          if User.query.filter(User.email == email, User.id != user.id).first():
  ```

- **Fix Applied (After Fix):**

  ```python
          # The unique index also covers soft-deleted users; IntegrityError below handles that.
          if User.active().filter(User.email == email, User.id != user.id).first():
  ```

## Violation #5: Card detail loads the creator with the legacy unfiltered User.query.get

- **File Location:** `backend/app/blueprints/cards/service.py` (`get_card_detail`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
      creator = User.query.get(card.created_by_id) if card.created_by_id else None
  ```

- **Fix Applied (After Fix):**

  ```python
      creator = (
          User.active().filter_by(id=card.created_by_id).first()
          if card.created_by_id
          else None
      )
  ```

## Violation #6: Assignment notification loads the actor with an unfiltered db.session.get

- **File Location:** `backend/app/blueprints/cards/service.py` (`_notify_assigned`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
      notification_service.notify_card_assigned(db.session.get(User, actor_id), card, board_id)
  ```

- **Fix Applied (After Fix):**

  ```python
      actor = User.active().filter_by(id=actor_id).first()
      notification_service.notify_card_assigned(actor, card, board_id)
  ```

## Violation #7: Comment notification loads the actor with an unfiltered db.session.get

- **File Location:** `backend/app/blueprints/comments/service.py` (`create_comment`)

- **Guideline Broken:** `guidelines/database.md` — Rule 3: Soft-Deleted Rows Are Excluded From Reads

- **What AI Generated (Before Fix):**

  ```python
          actor = db.session.get(User, user_id)
  ```

- **Fix Applied (After Fix):**

  ```python
          actor = User.active().filter_by(id=user_id).first()
  ```

## Checked and Compliant

- `routes.py` (all 8 blueprints): no `Model.query` or `db.session`; they only parse, call schema and service, and return `success_response`. (`guidelines/backend.md` Rule 1)
- Deletes: no `session.delete()` or `DELETE` anywhere. Every delete sets `deleted_at` through `soft_delete()` or a bulk `UPDATE`. (`guidelines/database.md` Rule 2)
- Errors: no hand-built error dictionaries. All errors go through `ApiError` and `error_response`, producing flat `{"error": "<string>"}`. (`guidelines/backend.md` Rule 2)
- Analytics: `cards_per_column`, `completed_this_week` and `member_activity` use `func.count` with joins and `group_by`, with no Python counting loops. (`guidelines/backend.md` Rule 4)
- Models: UUID `String(36)` keys, `AuditMixin` columns, `active()`, `Float` `order`, `BoardMember` constraints and `completed_at` match `guidelines/database.md` Rules 1 to 6.

Verification: `compileall` passes and `create_app()` boots with all 30 routes registered. The repo has no test suite, so behavior was not exercised end to end.
