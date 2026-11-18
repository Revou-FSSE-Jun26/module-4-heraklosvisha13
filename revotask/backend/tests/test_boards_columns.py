import uuid

from app.models import Board, Card, Column, Comment
from conftest import add_member, make_card, make_comment

MISSING = str(uuid.uuid4())


class TestBoards:
    def test_create_board_makes_creator_admin(self, client, alice_h):
        res = client.post("/api/boards", json={"name": "  Roadmap "}, headers=alice_h)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["name"] == "Roadmap"
        assert data["role"] == "admin"

    def test_create_board_validation(self, client, alice_h):
        for body in ({}, {"name": ""}, {"name": "   "}, {"name": "x" * 121}, {"name": "ok", "extra": 1}):
            res = client.post("/api/boards", json=body, headers=alice_h)
            assert res.status_code == 400, body
            assert isinstance(res.get_json()["error"], str)

    def test_requires_auth(self, client, board):
        assert client.post("/api/boards", json={"name": "x"}).status_code == 401
        assert client.get("/api/boards").status_code == 401
        assert client.get(f"/api/boards/{board.id}").status_code == 401

    def test_list_only_returns_own_boards_with_role(self, client, board, alice_h, bob_h, carol_h):
        alice_boards = client.get("/api/boards", headers=alice_h).get_json()["data"]
        bob_boards = client.get("/api/boards", headers=bob_h).get_json()["data"]
        assert [(b["id"], b["role"]) for b in alice_boards] == [(board.id, "admin")]
        assert [(b["id"], b["role"]) for b in bob_boards] == [(board.id, "member")]
        assert client.get("/api/boards", headers=carol_h).get_json()["data"] == []

    def test_get_board_detail_includes_ordered_columns_and_cards(
        self, client, board, columns, alice_h
    ):
        make_card(columns[0], "second", order=2000.0)
        make_card(columns[0], "first", order=1000.0)
        res = client.get(f"/api/boards/{board.id}", headers=alice_h)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert [c["name"] for c in data["columns"]] == ["To Do", "Doing", "Done"]
        assert [c["title"] for c in data["columns"][0]["cards"]] == ["first", "second"]
        assert data["columns"][1]["cards"] == []

    def test_non_member_gets_403_and_unknown_board_404(self, client, board, carol_h):
        assert client.get(f"/api/boards/{board.id}", headers=carol_h).status_code == 403
        assert client.get(f"/api/boards/{MISSING}", headers=carol_h).status_code == 404

    def test_admin_can_rename(self, client, board, alice_h):
        res = client.patch(f"/api/boards/{board.id}", json={"name": "Renamed"}, headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["name"] == "Renamed"

    def test_rename_empty_body_is_400(self, client, board, alice_h):
        assert client.patch(f"/api/boards/{board.id}", json={}, headers=alice_h).status_code == 400

    def test_member_cannot_rename_or_delete(self, client, board, bob_h):
        assert client.patch(f"/api/boards/{board.id}", json={"name": "x"}, headers=bob_h).status_code == 403
        assert client.delete(f"/api/boards/{board.id}", headers=bob_h).status_code == 403

    def test_delete_is_soft_and_cascades(self, client, db, board, columns, card, alice, alice_h):
        comment = make_comment(card, alice)
        res = client.delete(f"/api/boards/{board.id}", headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"] == {"id": board.id}

        # Rows are kept but flagged, never removed.
        assert db.session.get(Board, board.id).deleted_at is not None
        assert db.session.get(Card, card.id).deleted_at is not None
        assert db.session.get(Comment, comment.id).deleted_at is not None
        assert all(db.session.get(Column, c.id).deleted_at is not None for c in columns)

        assert client.get(f"/api/boards/{board.id}", headers=alice_h).status_code == 404
        assert client.get("/api/boards", headers=alice_h).get_json()["data"] == []


class TestColumns:
    def test_create_column_appends_with_order_step(self, client, board, columns, alice_h):
        res = client.post(f"/api/boards/{board.id}/columns", json={"name": "QA"}, headers=alice_h)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["name"] == "QA"
        assert data["order"] == columns[-1].order + 1000.0

    def test_first_column_order_is_1000(self, client, alice_h):
        board_id = client.post("/api/boards", json={"name": "Empty"}, headers=alice_h).get_json()["data"]["id"]
        res = client.post(f"/api/boards/{board_id}/columns", json={"name": "A"}, headers=alice_h)
        assert res.get_json()["data"]["order"] == 1000.0

    def test_member_can_create_column(self, client, board, bob_h):
        res = client.post(f"/api/boards/{board.id}/columns", json={"name": "Ideas"}, headers=bob_h)
        assert res.status_code == 201

    def test_create_column_validation_auth_and_access(self, client, board, alice_h, carol_h):
        url = f"/api/boards/{board.id}/columns"
        assert client.post(url, json={}, headers=alice_h).status_code == 400
        assert client.post(url, json={"name": ""}, headers=alice_h).status_code == 400
        assert client.post(url, json={"name": "x"}).status_code == 401
        assert client.post(url, json={"name": "x"}, headers=carol_h).status_code == 403
        assert client.post(f"/api/boards/{MISSING}/columns", json={"name": "x"}, headers=alice_h).status_code == 404

    def test_rename_column(self, client, columns, alice_h):
        res = client.patch(f"/api/columns/{columns[0].id}", json={"name": "Backlog"}, headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["name"] == "Backlog"

    def test_rename_column_errors(self, client, columns, alice_h, carol_h):
        url = f"/api/columns/{columns[0].id}"
        assert client.patch(url, json={}, headers=alice_h).status_code == 400
        assert client.patch(url, json={"name": "x"}, headers=carol_h).status_code == 403
        assert client.patch(url, json={"name": "x"}).status_code == 401
        assert client.patch(f"/api/columns/{MISSING}", json={"name": "x"}, headers=alice_h).status_code == 404

    def test_delete_column_soft_deletes_cards_and_comments(
        self, client, db, columns, card, alice, alice_h
    ):
        comment = make_comment(card, alice)
        res = client.delete(f"/api/columns/{columns[0].id}", headers=alice_h)
        assert res.status_code == 200
        assert db.session.get(Column, columns[0].id).deleted_at is not None
        assert db.session.get(Card, card.id).deleted_at is not None
        assert db.session.get(Comment, comment.id).deleted_at is not None

    def test_delete_column_forbidden_for_non_member(self, client, columns, carol_h):
        assert client.delete(f"/api/columns/{columns[0].id}", headers=carol_h).status_code == 403


class TestColumnReorder:
    def url(self, board):
        return f"/api/boards/{board.id}/columns/reorder"

    def test_move_between_neighbours_uses_given_order(self, client, board, columns, alice_h):
        res = client.patch(
            self.url(board), json={"column_id": columns[2].id, "order": 1500.0}, headers=alice_h
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["order"] == 1500.0
        assert data["rebalanced"] == []
        detail = client.get(f"/api/boards/{board.id}", headers=alice_h).get_json()["data"]
        assert [c["name"] for c in detail["columns"]] == ["To Do", "Done", "Doing"]

    def test_tiny_gap_triggers_rebalance(self, client, board, columns, alice_h):
        res = client.patch(
            self.url(board),
            json={"column_id": columns[2].id, "order": columns[0].order + 1e-9},
            headers=alice_h,
        )
        assert res.status_code == 200
        rebalanced = res.get_json()["data"]["rebalanced"]
        assert [r["order"] for r in rebalanced] == [1000.0, 2000.0, 3000.0]
        # the moved column sorts after the one it collided with
        assert [r["id"] for r in rebalanced] == [columns[0].id, columns[2].id, columns[1].id]

    def test_validation_errors(self, client, board, columns, alice_h):
        url = self.url(board)
        cid = columns[0].id
        for body in (
            {},
            {"column_id": cid},
            {"order": 5.0},
            {"column_id": "nope", "order": 5.0},
            {"column_id": cid, "order": 0},
            {"column_id": cid, "order": -3},
            {"column_id": cid, "order": "abc"},
            {"column_id": cid, "order": 5.0, "extra": True},
        ):
            assert client.patch(url, json=body, headers=alice_h).status_code == 400, body

    def test_column_from_other_board_is_400(self, client, board, alice, alice_h):
        from conftest import board_columns, make_board

        other = make_board(alice, "Other")
        foreign = board_columns(other)[0]
        res = client.patch(self.url(board), json={"column_id": foreign.id, "order": 5.0}, headers=alice_h)
        assert res.status_code == 400

    def test_auth_and_access(self, client, board, columns, carol_h):
        body = {"column_id": columns[0].id, "order": 5.0}
        assert client.patch(self.url(board), json=body).status_code == 401
        assert client.patch(self.url(board), json=body, headers=carol_h).status_code == 403
        assert client.patch(
            self.url(board), json={"column_id": MISSING, "order": 5.0}, headers=carol_h
        ).status_code == 403
