# Database Guidelines (SQLAlchemy + PostgreSQL)

Scope: model definitions, columns, constraints, indexes, ordering data, and migrations. HTTP, query composition for endpoints, and UI behavior are defined in `backend.md` and `frontend.md`.

Models covered: `User`, `Board`, `BoardMember`, `Column`, `Card`, `Comment`, `Notification`.

---

## 1. UUID Primary Keys

**Rule**
Every model uses `db.String(36)` primary keys generated with `uuid.uuid4`. Never use auto-increment integers. Foreign keys to these keys are also `db.String(36)`.

**Rationale**
UUIDs cannot be guessed or enumerated in URLs such as `/api/boards/<id>`. They can be generated before insert, and they stay unique across environments (local, Railway).

**Example**
```python
import uuid
from app.extensions import db

def new_uuid() -> str:
    return str(uuid.uuid4())

class Board(db.Model):
    __tablename__ = "boards"
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    name = db.Column(db.String(120), nullable=False)

class Card(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    column_id = db.Column(db.String(36), db.ForeignKey("columns.id"), nullable=False, index=True)
```

---

## 2. Audit Timestamps & Soft Delete

**Rule**
Every model has `created_at`, `updated_at`, and `deleted_at`, all `DateTime` stored in UTC. `deleted_at` is nullable. Deleting a record sets `deleted_at` and never issues a SQL `DELETE`. Use one shared mixin so the columns are not redefined per model.

**Rationale**
Audit columns show when data changed. Soft delete avoids permanent data loss and orphaned rows, and lets deleted boards, cards, and comments be recovered.

**Example**
```python
from datetime import datetime, timezone

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class AuditMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()

class Comment(AuditMixin, db.Model):
    __tablename__ = "comments"
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
```

---

## 3. Soft-Deleted Rows Are Excluded From Reads

**Rule**
Any query on a model must filter `Model.deleted_at.is_(None)`. Models expose this as a reusable `active()` class method on `AuditMixin`.

**Rationale**
Without a filter, soft-deleted records reappear in boards, counts, and analytics. A single helper keeps the filter consistent.

**Example**
```python
class AuditMixin:
    # ...columns above...
    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

cards = Card.active().filter_by(column_id=column_id).order_by(Card.order).all()
```

---

## 4. FLOAT Ordering Strategy

**Rule**
`Column` and `Card` define `order = db.Column(db.Float, nullable=False)`. Never name it `position`. The first item gets `1000.0`, and each new item at the end gets the last `order` plus `1000.0`. Inserting between two neighbors uses the midpoint `(prev + next) / 2`. When the gap between neighbors falls below `1e-6`, rebalance all items in that scope inside one transaction, reassigning `1000.0, 2000.0, ...`. A card's scope is its column, and a column's scope is its board.

**Rationale**
Moving an item updates one row instead of every row in the list. Float gaps shrink with repeated midpoint inserts, so a transactional rebalance prevents ties and keeps ordering correct.

**Example**
```python
ORDER_STEP = 1000.0
MIN_GAP = 1e-6

class Card(AuditMixin, db.Model):
    __tablename__ = "cards"
    column_id = db.Column(db.String(36), db.ForeignKey("columns.id"), nullable=False)
    order = db.Column(db.Float, nullable=False)
    __table_args__ = (db.Index("ix_cards_column_id_order", "column_id", "order"),)

def midpoint(prev_order: float | None, next_order: float | None) -> float:
    if prev_order is None and next_order is None:
        return ORDER_STEP
    if prev_order is None:
        return next_order / 2
    if next_order is None:
        return prev_order + ORDER_STEP
    return (prev_order + next_order) / 2

def rebalance_column(column_id: str) -> None:
    with db.session.begin_nested():
        cards = Card.active().filter_by(column_id=column_id).order_by(Card.order).all()
        for i, card in enumerate(cards, start=1):
            card.order = i * ORDER_STEP
```

---

## 5. Board Membership & Ownership

**Rule**
Board access and roles live in a `board_members` join table (model `BoardMember`) with columns `board_id`, `user_id`, and `role`. `role` is `member` or `admin` and is stored per board, never on `User`. Add `UniqueConstraint("board_id", "user_id")`. The board creator is inserted as `admin`. `Card.completed_at` (nullable, UTC) records when a card was completed, and it is the source for weekly completion counts.

**Rationale**
A user can be admin on one board and member on another, so the role belongs to the membership. The unique constraint prevents duplicate memberships. `completed_at` makes "completed this week" a plain timestamp comparison.

**Example**
```python
class BoardMember(AuditMixin, db.Model):
    __tablename__ = "board_members"
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    board_id = db.Column(db.String(36), db.ForeignKey("boards.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False, default="member")  # "member" | "admin"
    __table_args__ = (
        db.UniqueConstraint("board_id", "user_id", name="uq_board_members_board_user"),
        db.CheckConstraint("role IN ('member', 'admin')", name="ck_board_members_role"),
    )

class Card(AuditMixin, db.Model):
    # ...
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
```

---

## 6. Card Assignee Reference

**Rule**
`Card.assignee_id` is a single nullable `db.String(36)` foreign key to `users.id` with `ondelete="SET NULL"`.

**Rationale**
One assignee keeps the `/my-tasks` query simple. `SET NULL` keeps cards when a user record is removed.

**Example**
```python
assignee_id = db.Column(
    db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
)
```

---

## 7. Migrations Only

**Rule**
Every schema change is a Flask-Migrate revision committed with the model change. Never call `db.create_all()` outside tests, and never edit the database by hand.

**Rationale**
Migrations make the schema reproducible in local, test, and Railway environments, and keep a reviewable history.

**Example**
```bash
flask db migrate -m "add completed_at to cards"
flask db upgrade
```
