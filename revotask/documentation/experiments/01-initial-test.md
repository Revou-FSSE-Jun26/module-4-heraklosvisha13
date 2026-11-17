# 01. Initial Baseline Test (Without Steering Guidelines)

## 1. Purpose & Learning Objective
This baseline experiment was conducted before populating any rules in `.kiro/steering/` or `guidelines/`. Its purpose is to observe how Kiro behaves when relying solely on `specs/project-brief.md`, demonstrating why unguided AI generation leads to arbitrary architectural assumptions and rubric violations.

---

## 2. Input
- **Workspace State:** `specs/project-brief.md` was populated, while `.kiro/steering/*.md` and `guidelines/*.md` were completely empty (0 lines).
- **Prompt Executed:**
```text
Based on the existing revotask project brief and steering documents, create an example Flask API endpoint:
GET /api/boards/<board_id>/comments
The endpoint should retrieve all comments associated with a specific board.

Requirements:
1. Use Flask and SQLAlchemy.
2. Provide the SQLAlchemy Card model required to establish the relationship between boards, cards, and comments.
3. Include the necessary relationships and foreign keys.
4. Ensure that only authenticated users with access to the specified board can retrieve its comments.
5. Follow the project's existing architectural conventions and coding standards.
6. Include appropriate error handling and HTTP status codes.
7. Use the existing technology stack and avoid introducing unnecessary dependencies.

Output Instructions:
- Display all generated code directly in the chat.
- Do not create or modify any project files.
- Explain the purpose of each major code section.

If any required information is missing from the project brief or steering documents, explicitly state your assumptions instead of inventing project requirements.
```

---

## 3. Execution Process & Resulting Output

### Step 1: Workspace Scan & Assumption Formulation
When Kiro processed the prompt, it scanned `.kiro/steering/` and `guidelines/`, found them empty, and explicitly switched to making **12 independent assumptions** to fill in the missing technical specifications:

> **Kiro Output (Assumptions):**
> *"The steering files (.kiro/steering/backend.md, database.md, frontend.md) and the guidelines/*.md files are all empty. The only real source is specs/project-brief.md, so the conventions below come from the brief plus my stated assumptions."*
> 1. **Folder layout:** `app/models/`, `app/schemas/`, `app/services/`, `app/routes/` (horizontal layer layout).
> 2. **Hierarchy:** `Board -> Column -> Card -> Comment`.
> 3. **Membership:** `BoardMember` join table with `member` or `admin` roles.
> 4. **Error format:** Nested object `{"error": {"code": "...", "message": "..."}}`.
> 5. **Success format:** `{"data": [...]}`.
> 6. **Status codes:** `404` (missing board), `403` (non-member), `401` (handled by Flask-JWT-Extended).
> 7. **Identity:** JWT identity stored as string `user_id`.
> 8. **Pagination:** None implemented.
> 9. **Ordering:** Oldest comment first (`created_at`, then `id`).
> 10. **Soft delete & Notifications:** Treated as out of scope.
> 11. **App factory & Login:** Assumed to already exist.

### Step 2: Model Generation
Based on those assumptions, Kiro generated `app/models/board.py` and `app/models/card.py` directly in the chat before the response truncated prior to outputting the `Comment` model and route handler:

> **Kiro Output (`app/models/board.py`):**
> ```python
> from datetime import datetime, timezone
> from app.extensions import db
>
> def utcnow():
>     return datetime.now(timezone.utc)
>
> class Board(db.Model):
>     __tablename__ = "boards"
>
>     id = db.Column(db.Integer, primary_key=True)
>     name = db.Column(db.String(120), nullable=False)
>     created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
>
>     columns = db.relationship("Column", back_populates="board", cascade="all, delete-orphan")
>     members = db.relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")
>
> class BoardMember(db.Model):
>     __tablename__ = "board_members"
>     __table_args__ = (
>         db.UniqueConstraint("board_id", "user_id", name="uq_board_members_board_user"),
>     )
>
>     id = db.Column(db.Integer, primary_key=True)
>     board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
>     user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
>     role = db.Column(db.String(20), nullable=False, default="member")
>
>     board = db.relationship("Board", back_populates="members")
>     user = db.relationship("User", back_populates="board_memberships")
>
> class Column(db.Model):
>     __tablename__ = "columns"
>
>     id = db.Column(db.Integer, primary_key=True)
>     board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
>     name = db.Column(db.String(120), nullable=False)
>     position = db.Column(db.Float, nullable=False)
>
>     board = db.relationship("Board", back_populates="columns")
>     cards = db.relationship("Card", back_populates="column", cascade="all, delete-orphan")
> ```
>
> **Kiro Output (`app/models/card.py`):**
> ```python
> from app.extensions import db
> from app.models.board import utcnow
>
> class Card(db.Model):
>     __tablename__ = "cards"
>
>     id = db.Column(db.Integer, primary_key=True)
>     column_id = db.Column(db.Integer, db.ForeignKey("columns.id", ondelete="CASCADE"), nullable=False, index=True)
>     assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
>     title = db.Column(db.String(200), nullable=False)
>     description = db.Column(db.Text, nullable=True)
>     position = db.Column(db.Float, nullable=False)
> ```

---

## 4. Critical Evaluation & Takeaways
Reviewing Kiro's unguided output revealed **5 critical deviations** from the RevoTask rubric:

| Aspect | Unguided Kiro Output | Required RevoTask Standard | Why It Matters |
| :--- | :--- | :--- | :--- |
| **Primary Key** | `db.Integer` auto-increment | **UUID** (`String(36)` / `UUID`) | Prevents IDOR enumeration and meets the `Card` model rubric. |
| **Ordering Column** | Named `position` | Named **`order`** (`db.Float`) | Must match the `order` field expected by `PATCH /api/cards/<id>/position`. |
| **Audit & Soft Delete** | Missing `updated_at` & `deleted_at` | `created_at`, `updated_at`, `deleted_at` on all tables | Prevents permanent data loss and preserves audit history. |
| **Folder Structure** | Horizontal (`app/routes/`, `app/services/`) | Feature blueprints (`app/blueprints/<feature>/`) | Enforces modular separation (`routes.py`, `service.py`, `schema.py`). |
| **Error Envelope** | Nested `{"error": {"code": ...}}` | Flat `{"error": "<message>"}` | Ensures consistent error parsing in frontend `lib/apiClient.ts`. |