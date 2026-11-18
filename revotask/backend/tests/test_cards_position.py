import uuid

import pytest

from app.models import Board, Card, Notification
from conftest import add_member, make_board, make_card, make_comment, board_columns, make_user

MISSING = str(uuid.uuid4())


def post_card(client, column, headers, **body):
    body.setdefault("title", "New card")
    return client.post(f"/api/columns/{column.id}/cards", json=body, headers=headers)


class TestCreateCard:
    def test_first_card_order_is_1000_then_steps(self, client, columns, alice_h):
        first = post_card(client, columns[0], alice_h).get_json()["data"]
        second = post_card(client, columns[0], alice_h).get_json()["data"]
        assert first["order"] == 1000.0
        assert second["order"] == 2000.0
        assert first["column_id"] == columns[0].id

    def test_order_is_scoped_per_column(self, client, columns, alice_h):
        post_card(client, columns[0], alice_h)
        assert post_card(client, columns[1], alice_h).get_json()["data"]["order"] == 1000.0

    def test_full_payload(self, client, columns, board, alice_h, bob):
        res = post_card(
            client, columns[0], alice_h,
            title="  Trim me ", description="details",
            assignee_id=bob.id, due_date="2030-01-01T10:00:00+00:00",
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["title"] == "Trim me"
        assert data["assignee"] == {"id": bob.id, "name": "Bob"}
        assert data["board_id"] == board.id
        assert data["due_date"].startswith("2030-01-01T10:00:00")

    def test_creating_in_last_column_marks_completed(self, client, columns, alice_h):
        done = post_card(client, columns[-1], alice_h).get_json()["data"]
        todo = post_card(client, columns[0], alice_h).get_json()["data"]
        assert done["completed_at"] is not None
        assert todo["completed_at"] is None

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"title": ""},
            {"title": "   "},
            {"title": "x" * 201},
            {"title": "ok", "assignee_id": "not-a-uuid"},
            {"title": "ok", "due_date": "yesterday-ish"},
            {"title": "ok", "unknown": 1},
        ],
    )
    def test_validation(self, client, columns, alice_h, body):
        res = client.post(f"/api/columns/{columns[0].id}/cards", json=body, headers=alice_h)
        assert res.status_code == 400

    def test_assignee_must_be_board_member(self, client, columns, alice_h, carol):
        assert post_card(client, columns[0], alice_h, assignee_id=carol.id).status_code == 400
        assert post_card(client, columns[0], alice_h, assignee_id=MISSING).status_code == 400

    def test_auth_access_and_missing(self, client, columns, carol_h):
        assert client.post(f"/api/columns/{columns[0].id}/cards", json={"title": "x"}).status_code == 401
        assert post_card(client, columns[0], carol_h).status_code == 403
        res = client.post(f"/api/columns/{MISSING}/cards", json={"title": "x"}, headers=carol_h)
        assert res.status_code == 404


class TestReadUpdateDelete:
    def test_get_card_detail(self, client, card, alice, alice_h):
        make_comment(card, alice, "hello")
        res = client.get(f"/api/cards/{card.id}", headers=alice_h)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["title"] == "Write tests"
        assert [c["body"] for c in data["comments"]] == ["hello"]
        assert {a["type"] for a in data["activity"]} >= {"card_created", "comment_added"}

    def test_get_card_access(self, client, card, carol_h):
        assert client.get(f"/api/cards/{card.id}").status_code == 401
        assert client.get(f"/api/cards/{card.id}", headers=carol_h).status_code == 403
        assert client.get(f"/api/cards/{MISSING}", headers=carol_h).status_code == 404

    def test_update_fields(self, client, card, alice_h):
        res = client.patch(
            f"/api/cards/{card.id}", json={"title": "Renamed", "description": "d"}, headers=alice_h
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert (data["title"], data["description"]) == ("Renamed", "d")

    def test_update_can_clear_assignee(self, client, card, bob, alice_h):
        client.patch(f"/api/cards/{card.id}", json={"assignee_id": bob.id}, headers=alice_h)
        res = client.patch(f"/api/cards/{card.id}", json={"assignee_id": None}, headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["assignee_id"] is None

    def test_update_errors(self, client, card, alice_h, carol_h, carol):
        url = f"/api/cards/{card.id}"
        assert client.patch(url, json={}, headers=alice_h).status_code == 400
        assert client.patch(url, json={"title": ""}, headers=alice_h).status_code == 400
        assert client.patch(url, json={"assignee_id": carol.id}, headers=alice_h).status_code == 400
        assert client.patch(url, json={"title": "x"}).status_code == 401
        assert client.patch(url, json={"title": "x"}, headers=carol_h).status_code == 403

    def test_delete_is_soft(self, client, db, card, alice_h):
        res = client.delete(f"/api/cards/{card.id}", headers=alice_h)
        assert res.status_code == 200
        assert db.session.get(Card, card.id).deleted_at is not None
        assert client.get(f"/api/cards/{card.id}", headers=alice_h).status_code == 404

    def test_delete_access(self, client, card, carol_h):
        assert client.delete(f"/api/cards/{card.id}").status_code == 401
        assert client.delete(f"/api/cards/{card.id}", headers=carol_h).status_code == 403


class TestPosition:
    def url(self, card):
        return f"/api/cards/{card.id}/position"

    def test_reorder_within_column(self, client, columns, alice_h):
        a = make_card(columns[0], "a", 1000.0)
        b = make_card(columns[0], "b", 2000.0)
        c = make_card(columns[0], "c", 3000.0)
        res = client.patch(self.url(c), json={"column_id": columns[0].id, "order": 1500.0}, headers=alice_h)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["order"] == 1500.0
        assert data["rebalanced"] == []
        board = client.get(f"/api/boards/{columns[0].board_id}", headers=alice_h).get_json()["data"]
        assert [x["title"] for x in board["columns"][0]["cards"]] == ["a", "c", "b"]

    def test_move_to_other_column(self, client, columns, card, alice_h):
        res = client.patch(
            self.url(card), json={"column_id": columns[1].id, "order": 1000.0}, headers=alice_h
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["column_id"] == columns[1].id

    def test_member_can_move(self, client, columns, card, bob_h):
        res = client.patch(self.url(card), json={"column_id": columns[1].id, "order": 10.0}, headers=bob_h)
        assert res.status_code == 200

    def test_moving_into_last_column_sets_completed_at_and_out_clears_it(self, client, columns, card, alice_h):
        done = client.patch(
            self.url(card), json={"column_id": columns[-1].id, "order": 1000.0}, headers=alice_h
        ).get_json()["data"]
        assert done["completed_at"] is not None

        back = client.patch(
            self.url(card), json={"column_id": columns[0].id, "order": 1000.0}, headers=alice_h
        ).get_json()["data"]
        assert back["completed_at"] is None

    def test_moving_between_non_final_columns_keeps_completed_at_empty(self, client, columns, card, alice_h):
        res = client.patch(
            self.url(card), json={"column_id": columns[1].id, "order": 1000.0}, headers=alice_h
        )
        assert res.get_json()["data"]["completed_at"] is None

    def test_reentering_last_column_keeps_original_completion_time(self, client, columns, alice_h):
        done_card = post_card(client, columns[-1], alice_h).get_json()["data"]
        res = client.patch(
            f"/api/cards/{done_card['id']}/position",
            json={"column_id": columns[-1].id, "order": 5000.0},
            headers=alice_h,
        )
        assert res.get_json()["data"]["completed_at"] == done_card["completed_at"]

    def test_midpoint_between_neighbours_does_not_rebalance(self, client, columns, alice_h):
        make_card(columns[0], "a", 1000.0)
        make_card(columns[0], "b", 2000.0)
        c = make_card(columns[0], "c", 3000.0)
        res = client.patch(
            self.url(c), json={"column_id": columns[0].id, "order": (1000.0 + 2000.0) / 2}, headers=alice_h
        )
        assert res.get_json()["data"]["rebalanced"] == []

    def test_gap_below_threshold_rebalances_column(self, client, columns, alice_h):
        a = make_card(columns[0], "a", 1000.0)
        b = make_card(columns[0], "b", 2000.0)
        c = make_card(columns[0], "c", 3000.0)
        res = client.patch(
            self.url(c), json={"column_id": columns[0].id, "order": 1000.0 + 1e-9}, headers=alice_h
        )
        assert res.status_code == 200
        rebalanced = res.get_json()["data"]["rebalanced"]
        assert [r["order"] for r in rebalanced] == [1000.0, 2000.0, 3000.0]
        assert [r["id"] for r in rebalanced] == [a.id, c.id, b.id]

    def test_exact_tie_puts_moved_card_after_existing_one(self, client, columns, alice_h):
        a = make_card(columns[0], "a", 1000.0)
        b = make_card(columns[0], "b", 2000.0)
        res = client.patch(self.url(b), json={"column_id": columns[0].id, "order": 1000.0}, headers=alice_h)
        assert [r["id"] for r in res.get_json()["data"]["rebalanced"]] == [a.id, b.id]

    def test_repeated_midpoint_inserts_always_keep_distinct_order(self, client, db, columns, alice_h):
        """Halving the gap many times must eventually rebalance, never produce ties."""
        make_card(columns[0], "left", 1000.0)
        make_card(columns[0], "right", 2000.0)
        mover = make_card(columns[0], "mover", 3000.0)
        lo, hi = 1000.0, 2000.0
        rebalanced_seen = False
        for _ in range(45):
            target = (lo + hi) / 2
            res = client.patch(
                self.url(mover), json={"column_id": columns[0].id, "order": target}, headers=alice_h
            )
            assert res.status_code == 200
            if res.get_json()["data"]["rebalanced"]:
                rebalanced_seen = True
                break
            hi = target
        assert rebalanced_seen
        orders = [c.order for c in Card.active().filter_by(column_id=columns[0].id).all()]
        assert len(set(orders)) == len(orders) == 3

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"order": 1.0},
            {"column_id": "bad", "order": 1.0},
            {"order": 0, "column_id": "00000000-0000-4000-8000-000000000000"},
            {"order": -1, "column_id": "00000000-0000-4000-8000-000000000000"},
        ],
    )
    def test_invalid_payload_is_400(self, client, card, alice_h, body):
        assert client.patch(self.url(card), json=body, headers=alice_h).status_code == 400

    def test_invalid_order_values_are_400(self, client, columns, card, alice_h):
        for order in (0, -5, "x", None):
            res = client.patch(
                self.url(card), json={"column_id": columns[0].id, "order": order}, headers=alice_h
            )
            assert res.status_code == 400, order

    def test_cannot_move_to_another_board(self, client, card, alice, alice_h):
        other_column = board_columns(make_board(alice, "Other"))[0]
        res = client.patch(self.url(card), json={"column_id": other_column.id, "order": 1.0}, headers=alice_h)
        assert res.status_code == 400
        assert "another board" in res.get_json()["error"]

    def test_unknown_target_column_is_404(self, client, card, alice_h):
        res = client.patch(self.url(card), json={"column_id": MISSING, "order": 1.0}, headers=alice_h)
        assert res.status_code == 404

    def test_auth_and_access(self, client, columns, card, carol_h):
        body = {"column_id": columns[0].id, "order": 5.0}
        assert client.patch(self.url(card), json=body).status_code == 401
        assert client.patch(self.url(card), json=body, headers=carol_h).status_code == 403
        assert client.patch(f"/api/cards/{MISSING}/position", json=body, headers=carol_h).status_code == 404


class TestSearchAndMyTasks:
    def test_search_matches_title_and_description_case_insensitively(self, client, board, columns, alice_h):
        make_card(columns[0], "Fix LOGIN bug", 1000.0)
        make_card(columns[1], "Other", 1000.0, description="the login page")
        make_card(columns[1], "Unrelated", 2000.0)
        res = client.get(f"/api/boards/{board.id}/cards?q=login", headers=alice_h)
        assert res.status_code == 200
        assert {c["title"] for c in res.get_json()["data"]} == {"Fix LOGIN bug", "Other"}

    def test_search_without_query_returns_all_and_escapes_wildcards(self, client, board, columns, alice_h):
        make_card(columns[0], "100% done", 1000.0)
        make_card(columns[0], "plain", 2000.0)
        assert len(client.get(f"/api/boards/{board.id}/cards", headers=alice_h).get_json()["data"]) == 2
        res = client.get(f"/api/boards/{board.id}/cards?q=%25", headers=alice_h)
        assert [c["title"] for c in res.get_json()["data"]] == ["100% done"]

    def test_search_excludes_deleted_cards_and_other_boards(self, client, board, columns, alice, alice_h):
        gone = make_card(columns[0], "ghost", 1000.0)
        gone.soft_delete()
        other = board_columns(make_board(alice, "Other"))[0]
        make_card(other, "ghost elsewhere", 1000.0)
        from app.extensions import db

        db.session.commit()
        res = client.get(f"/api/boards/{board.id}/cards?q=ghost", headers=alice_h)
        assert res.get_json()["data"] == []

    def test_search_access(self, client, board, carol_h):
        assert client.get(f"/api/boards/{board.id}/cards").status_code == 401
        assert client.get(f"/api/boards/{board.id}/cards", headers=carol_h).status_code == 403

    def test_my_tasks_counts(self, client, board, columns, bob, bob_h):
        make_card(columns[0], "open", 1000.0, assignee_id=bob.id)
        from app.models.mixins import utcnow

        make_card(columns[2], "done", 1000.0, assignee_id=bob.id, completed_at=utcnow())
        make_card(columns[0], "not mine", 2000.0)
        res = client.get("/api/cards?assignee=me", headers=bob_h)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert (data["total"], data["completed"], data["open"]) == (2, 1, 1)
        assert {i["title"] for i in data["items"]} == {"open", "done"}
        assert data["items"][0]["board_name"] == board.name

    def test_my_tasks_requires_assignee_me_and_auth(self, client, bob_h):
        assert client.get("/api/cards", headers=bob_h).status_code == 400
        assert client.get("/api/cards?assignee=other", headers=bob_h).status_code == 400
        assert client.get("/api/cards?assignee=me").status_code == 401
