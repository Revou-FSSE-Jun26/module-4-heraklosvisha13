# Backend Guidelines (Flask)

Scope: blueprint structure, HTTP contract, authorization, and service-layer query composition. Column definitions, constraints, soft-delete helpers, and ordering math are defined in `database.md`. Client-side behavior is defined in `frontend.md`.

---

## 1. 3-Layer Feature Blueprints

**Rule**
Every feature lives in `app/blueprints/<feature>/` and is split into three files. Features: `auth`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `users`.
- `routes.py`: HTTP handling only (parse request, call a schema, call a service, return a response).
- `service.py`: business logic and all SQLAlchemy queries.
- `schema.py`: Marshmallow validation and serialization.

Never put SQLAlchemy queries (`Model.query`, `db.session`) in `routes.py`.

**Rationale**
Separating layers keeps logic testable without HTTP and prevents business rules from leaking into route handlers.

**Example**
```python
# app/blueprints/cards/routes.py
@cards_bp.post("/api/columns/<column_id>/cards")
@jwt_required()
def create_card(column_id):
    payload = CardCreateSchema().load(request.get_json() or {})
    card = card_service.create_card(get_jwt_identity(), column_id, payload)
    return jsonify({"data": CardSchema().dump(card)}), 201

# app/blueprints/cards/service.py
def create_card(user_id: str, column_id: str, payload: dict) -> Card:
    column = Column.active().filter_by(id=column_id).first_or_404()
    board_service.require_member(user_id, column.board_id)
    card = Card(column_id=column_id, title=payload["title"], order=next_card_order(column_id))
    db.session.add(card)
    db.session.commit()
    return card
```

---

## 2. Standard JSON Response Envelope

**Rule**
Every endpoint, including `GET /api/health`, returns one of two shapes.
- Success (`200`, `201`): `{"data": <payload>}`
- Failure (`400`, `401`, `403`, `404`, `500`): flat `{"error": "<message>"}`

`error` is always a string, never a nested object. Register central error handlers so routes do not build error responses by hand. Marshmallow `ValidationError` becomes a `400` whose message is a readable string. Routes are served under `/api/<resource>`.

**Rationale**
One envelope lets the API client parse every response the same way and keeps error handling consistent.

**Example**
```python
# app/errors.py
class ApiError(Exception):
    def __init__(self, message: str, status: int):
        self.message, self.status = message, status

@app.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify({"error": e.message}), e.status

@app.errorhandler(ValidationError)
def handle_validation(e):
    return jsonify({"error": "; ".join(f"{k}: {', '.join(v)}" for k, v in e.messages.items())}), 400

@app.errorhandler(Exception)
def handle_unexpected(e):
    app.logger.exception(e)
    return jsonify({"error": "Internal server error"}), 500

@app.get("/api/health")
def health():
    return jsonify({"data": {"status": "ok"}}), 200
```

---

## 3. Authorization & Ownership

**Rule**
- Protected endpoints use `@jwt_required()`. Missing, invalid, or expired tokens return `401`.
- Every board-scoped resource (board, column, card, comment, analytics) checks board membership in `service.py`. A non-member gets `403`.
- Board administration (membership changes, analytics) requires the `admin` role on that board, otherwise `403`.
- Comment edit and delete are allowed only for the author. Anyone else gets `403`.
- A missing resource returns `404`.
- Moving a card is allowed only within the same board.
- Do not rely on frontend restrictions. The backend enforces every rule.

**Rationale**
The brief requires the backend to enforce authorization independently of the UI. A single, predictable status policy (`401`, `403`, `404`) avoids inconsistent endpoints.

**Example**
```python
# app/blueprints/boards/service.py
def require_member(user_id: str, board_id: str, admin: bool = False) -> BoardMember:
    membership = BoardMember.active().filter_by(board_id=board_id, user_id=user_id).first()
    if membership is None or (admin and membership.role != "admin"):
        raise ApiError("You do not have access to this board", 403)
    return membership

# app/blueprints/comments/service.py
def update_comment(user_id: str, comment_id: str, payload: dict) -> Comment:
    comment = Comment.active().filter_by(id=comment_id).first()
    if comment is None:
        raise ApiError("Comment not found", 404)
    if comment.author_id != user_id:
        raise ApiError("Only the author can edit this comment", 403)
    comment.body = payload["body"]
    db.session.commit()
    return comment
```

---

## 4. Service-Layer Joins for Analytics

**Rule**
Analytics metrics are computed in `analytics/service.py` with SQLAlchemy joins and aggregations (`func.count`, `group_by`). This covers cards per column, cards completed this week, and member activity. Never load rows and count them in Python loops. "This week" is a UTC range on `Card.completed_at`, starting Monday 00:00 UTC.

**Rationale**
The database aggregates faster than Python, and it returns only the summary rows instead of every card.

**Example**
```python
# app/blueprints/analytics/service.py
def cards_per_column(board_id: str) -> list[dict]:
    rows = (
        db.session.query(Column.id, Column.name, func.count(Card.id))
        .outerjoin(Card, and_(Card.column_id == Column.id, Card.deleted_at.is_(None)))
        .filter(Column.board_id == board_id, Column.deleted_at.is_(None))
        .group_by(Column.id, Column.name)
        .order_by(Column.order)
        .all()
    )
    return [{"column_id": r[0], "name": r[1], "count": r[2]} for r in rows]

def completed_this_week(board_id: str, week_start: datetime) -> int:
    return (
        db.session.query(func.count(Card.id))
        .join(Column, Card.column_id == Column.id)
        .filter(Column.board_id == board_id, Card.deleted_at.is_(None),
                Card.completed_at >= week_start)
        .scalar()
    )
```

---

## 5. Card Search Contract

**Rule**
`GET /api/boards/<board_id>/cards?q=<text>` filters case-insensitively on card `title` and `description`, using `ilike` with a bound parameter. The query runs in `cards/service.py`.

**Rationale**
A defined contract lets the frontend's debounced search work against a predictable endpoint, and bound parameters prevent SQL injection.

**Example**
```python
def search_cards(board_id: str, q: str) -> list[Card]:
    pattern = f"%{q}%"
    return (
        Card.active().join(Column, Card.column_id == Column.id)
        .filter(Column.board_id == board_id,
                or_(Card.title.ilike(pattern), Card.description.ilike(pattern)))
        .order_by(Card.order).all()
    )
```

---

## 6. CORS and Configuration

**Rule**
Configure `Flask-CORS` with the single origin in the `FRONTEND_URL` environment variable. Read `DATABASE_URL`, `JWT_SECRET_KEY`, and `FRONTEND_URL` from the environment. Never hard-code secrets.

**Rationale**
The Vercel frontend and Railway backend are on different origins, so browsers block requests unless CORS is set. Restricting to one origin limits exposure.

**Example**
```python
# app/__init__.py
CORS(app, resources={r"/api/*": {"origins": os.environ["FRONTEND_URL"]}})
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
```
