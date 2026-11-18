import uuid
from datetime import datetime, timedelta, timezone

from app.blueprints.analytics.service import week_start
from app.models import Notification
from app.models.mixins import utcnow
from conftest import add_member, make_card, make_comment, make_notification, make_user

MISSING = str(uuid.uuid4())


class TestNotificationTriggers:
    def test_assigning_card_on_create_notifies_assignee(self, client, db, columns, alice, bob, alice_h):
        res = client.post(
            f"/api/columns/{columns[0].id}/cards",
            json={"title": "Do it", "assignee_id": bob.id},
            headers=alice_h,
        )
        assert res.status_code == 201
        note = Notification.query.filter_by(recipient_id=bob.id).one()
        assert note.type == "card_assigned"
        assert note.actor_id == alice.id
        assert "Alice" in note.message and "Do it" in note.message

    def test_reassigning_via_patch_notifies_new_assignee_only_on_change(
        self, client, card, bob, alice_h
    ):
        url = f"/api/cards/{card.id}"
        client.patch(url, json={"assignee_id": bob.id}, headers=alice_h)
        client.patch(url, json={"assignee_id": bob.id}, headers=alice_h)
        client.patch(url, json={"title": "renamed"}, headers=alice_h)
        assert Notification.query.filter_by(recipient_id=bob.id).count() == 1

    def test_self_assignment_does_not_notify(self, client, card, alice, alice_h):
        client.patch(f"/api/cards/{card.id}", json={"assignee_id": alice.id}, headers=alice_h)
        assert Notification.query.count() == 0


class TestListNotifications:
    def test_requires_auth(self, client):
        assert client.get("/api/notifications").status_code == 401
        assert client.patch("/api/notifications/read-all").status_code == 401
        assert client.patch(f"/api/notifications/{MISSING}/read").status_code == 401

    def test_empty(self, client, alice_h):
        data = client.get("/api/notifications", headers=alice_h).get_json()["data"]
        assert data["items"] == []
        assert (data["total"], data["pages"], data["unread_count"]) == (0, 0, 0)
        assert (data["page"], data["per_page"]) == (1, 20)

    def test_only_own_notifications_newest_first(self, client, board, alice, bob, alice_h):
        old = make_notification(alice, board, message="old", created_at=utcnow() - timedelta(hours=2))
        new = make_notification(alice, board, message="new")
        make_notification(bob, board, message="bobs")
        data = client.get("/api/notifications", headers=alice_h).get_json()["data"]
        assert [n["id"] for n in data["items"]] == [new.id, old.id]
        assert data["total"] == 2

    def test_pagination(self, client, board, alice, alice_h):
        for i in range(5):
            make_notification(alice, board, message=f"n{i}", created_at=utcnow() - timedelta(minutes=i))
        page1 = client.get("/api/notifications?page=1&per_page=2", headers=alice_h).get_json()["data"]
        page3 = client.get("/api/notifications?page=3&per_page=2", headers=alice_h).get_json()["data"]
        beyond = client.get("/api/notifications?page=9&per_page=2", headers=alice_h).get_json()["data"]
        assert (len(page1["items"]), page1["total"], page1["pages"]) == (2, 5, 3)
        assert len(page3["items"]) == 1
        assert beyond["items"] == []

    def test_invalid_pagination_is_400(self, client, alice_h):
        for query in ("page=0", "per_page=0", "per_page=101", "page=abc", "bogus=1"):
            assert client.get(f"/api/notifications?{query}", headers=alice_h).status_code == 400, query

    def test_unread_count_ignores_read_items(self, client, board, alice, alice_h):
        make_notification(alice, board)
        make_notification(alice, board, read_at=utcnow())
        data = client.get("/api/notifications", headers=alice_h).get_json()["data"]
        assert (data["total"], data["unread_count"]) == (2, 1)


class TestMarkRead:
    def test_mark_one_read_is_idempotent(self, client, board, alice, alice_h):
        note = make_notification(alice, board)
        first = client.patch(f"/api/notifications/{note.id}/read", headers=alice_h)
        assert first.status_code == 200
        stamp = first.get_json()["data"]["read_at"]
        assert stamp is not None
        second = client.patch(f"/api/notifications/{note.id}/read", headers=alice_h)
        assert second.get_json()["data"]["read_at"] == stamp

    def test_other_users_notification_is_403(self, client, db, board, alice, bob_h):
        note = make_notification(alice, board)
        assert client.patch(f"/api/notifications/{note.id}/read", headers=bob_h).status_code == 403
        db.session.expire_all()
        assert db.session.get(Notification, note.id).read_at is None

    def test_unknown_notification_is_404(self, client, alice_h):
        assert client.patch(f"/api/notifications/{MISSING}/read", headers=alice_h).status_code == 404

    def test_read_all_only_touches_caller(self, client, board, alice, bob, alice_h):
        make_notification(alice, board)
        make_notification(alice, board)
        make_notification(alice, board, read_at=utcnow())
        theirs = make_notification(bob, board)
        res = client.patch("/api/notifications/read-all", headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"] == {"updated": 2}
        listing = client.get("/api/notifications", headers=alice_h).get_json()["data"]
        assert listing["unread_count"] == 0
        from app.extensions import db

        db.session.expire_all()
        assert db.session.get(Notification, theirs.id).read_at is None

    def test_read_all_with_nothing_unread(self, client, alice_h):
        res = client.patch("/api/notifications/read-all", headers=alice_h)
        assert res.get_json()["data"] == {"updated": 0}


class TestWeekStart:
    def test_monday_midnight_utc(self):
        wednesday = datetime(2024, 5, 15, 13, 45, 12, tzinfo=timezone.utc)
        assert week_start(wednesday) == datetime(2024, 5, 13, tzinfo=timezone.utc)

    def test_monday_itself_and_sunday_edges(self):
        monday = datetime(2024, 5, 13, 0, 0, 0, tzinfo=timezone.utc)
        sunday = datetime(2024, 5, 19, 23, 59, 59, tzinfo=timezone.utc)
        assert week_start(monday) == monday
        assert week_start(sunday) == monday

    def test_non_utc_input_is_converted(self):
        # Monday 02:00 at UTC+5 is still Sunday 21:00 UTC, i.e. the previous week.
        tz = timezone(timedelta(hours=5))
        assert week_start(datetime(2024, 5, 13, 2, 0, tzinfo=tz)) == datetime(2024, 5, 6, tzinfo=timezone.utc)


class TestAnalytics:
    def url(self, board):
        return f"/api/boards/{board.id}/analytics"

    def test_access_rules(self, client, board, alice_h, bob_h, carol_h):
        assert client.get(self.url(board)).status_code == 401
        assert client.get(self.url(board), headers=bob_h).status_code == 403  # member, not admin
        assert client.get(self.url(board), headers=carol_h).status_code == 403
        assert client.get(self.url(board), headers=alice_h).status_code == 200
        assert client.get(f"/api/boards/{MISSING}/analytics", headers=alice_h).status_code == 404

    def test_empty_board_shape(self, client, board, columns, alice, bob, alice_h):
        data = client.get(self.url(board), headers=alice_h).get_json()["data"]
        assert [(c["name"], c["count"]) for c in data["cards_per_column"]] == [
            ("To Do", 0), ("Doing", 0), ("Done", 0)
        ]
        assert data["completed_this_week"]["count"] == 0
        assert data["completed_this_week"]["week_start"].startswith(
            week_start(utcnow()).date().isoformat()
        )
        assert {m["name"] for m in data["member_activity"]} == {"Alice", "Bob"}
        assert all(
            (m["assigned_count"], m["completed_this_week"], m["comments_count"]) == (0, 0, 0)
            for m in data["member_activity"]
        )

    def test_cards_per_column_counts_in_column_order_and_skips_deleted(
        self, client, board, columns, alice_h
    ):
        make_card(columns[0], "a", 1000.0)
        make_card(columns[0], "b", 2000.0)
        make_card(columns[1], "c", 1000.0)
        gone = make_card(columns[1], "deleted", 2000.0)
        gone.soft_delete()
        from app.extensions import db

        db.session.commit()
        data = client.get(self.url(board), headers=alice_h).get_json()["data"]
        assert [c["count"] for c in data["cards_per_column"]] == [2, 1, 0]

    def test_completed_this_week_only_counts_current_week(self, client, board, columns, alice_h):
        now = utcnow()
        make_card(columns[2], "this week", 1000.0, completed_at=now)
        make_card(columns[2], "last week", 2000.0, completed_at=week_start(now) - timedelta(seconds=1))
        make_card(columns[0], "open", 1000.0)
        data = client.get(self.url(board), headers=alice_h).get_json()["data"]
        assert data["completed_this_week"]["count"] == 1

    def test_member_activity_aggregates(self, client, board, columns, alice, bob, alice_h):
        now = utcnow()
        make_card(columns[0], "a1", 1000.0, assignee_id=alice.id)
        make_card(columns[2], "a2", 1000.0, assignee_id=alice.id, completed_at=now)
        done_old = make_card(
            columns[2], "a3", 2000.0, assignee_id=alice.id, completed_at=now - timedelta(days=30)
        )
        b1 = make_card(columns[1], "b1", 1000.0, assignee_id=bob.id)
        make_comment(b1, alice, "c1")
        make_comment(b1, alice, "c2")
        make_comment(done_old, bob, "c3")
        data = client.get(self.url(board), headers=alice_h).get_json()["data"]
        by_name = {m["name"]: m for m in data["member_activity"]}
        assert by_name["Alice"] == {
            "user_id": alice.id, "name": "Alice",
            "assigned_count": 3, "completed_this_week": 1, "comments_count": 2,
        }
        assert by_name["Bob"]["assigned_count"] == 1
        assert by_name["Bob"]["completed_this_week"] == 0
        assert by_name["Bob"]["comments_count"] == 1
        assert [m["name"] for m in data["member_activity"]] == ["Alice", "Bob"]

    def test_other_boards_do_not_leak_into_analytics(self, client, board, columns, alice, alice_h):
        from conftest import board_columns, make_board

        other = make_board(alice, "Other")
        make_card(board_columns(other)[0], "elsewhere", 1000.0)
        data = client.get(self.url(board), headers=alice_h).get_json()["data"]
        assert sum(c["count"] for c in data["cards_per_column"]) == 0
