import uuid

import pytest

from app.models import Comment, Notification
from conftest import make_comment

MISSING = str(uuid.uuid4())


@pytest.fixture()
def comments_url(card):
    return f"/api/cards/{card.id}/comments"


@pytest.fixture()
def alice_comment(card, alice):
    return make_comment(card, alice, "Alice wrote this")


# --------------------------------------------------------------------------
# 1. 201 Created: authenticated board member posts a valid comment
# --------------------------------------------------------------------------
class TestCreateComment201:
    def test_board_admin_gets_201(self, client, comments_url, alice, alice_h):
        res = client.post(comments_url, json={"body": "Looks good"}, headers=alice_h)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["body"] == "Looks good"
        assert data["author_id"] == alice.id
        assert data["author_name"] == "Alice"
        assert data["id"]

    def test_regular_board_member_gets_201(self, client, card, comments_url, bob, bob_h):
        res = client.post(comments_url, json={"body": "On it"}, headers=bob_h)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["author_id"] == bob.id
        assert data["card_id"] == card.id

    def test_comment_is_persisted_and_listed(self, client, db, comments_url, alice_h):
        created = client.post(comments_url, json={"body": "Persist me"}, headers=alice_h).get_json()["data"]
        assert db.session.get(Comment, created["id"]).body == "Persist me"
        listed = client.get(comments_url, headers=alice_h).get_json()["data"]
        assert [c["id"] for c in listed] == [created["id"]]

    def test_body_is_trimmed(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={"body": "  padded  "}, headers=alice_h)
        assert res.status_code == 201
        assert res.get_json()["data"]["body"] == "padded"

    def test_body_at_max_length_is_accepted(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={"body": "x" * 2000}, headers=alice_h)
        assert res.status_code == 201


# --------------------------------------------------------------------------
# 2. 400 Bad Request: content/body missing or empty
# --------------------------------------------------------------------------
class TestCreateComment400:
    def test_missing_body_field(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={}, headers=alice_h)
        assert res.status_code == 400
        assert "body" in res.get_json()["error"]

    def test_no_json_payload_at_all(self, client, comments_url, alice_h):
        res = client.post(comments_url, headers=alice_h)
        assert res.status_code == 400

    @pytest.mark.parametrize("body", ["", "   ", "\n\t "])
    def test_empty_or_whitespace_body(self, client, comments_url, alice_h, body):
        res = client.post(comments_url, json={"body": body}, headers=alice_h)
        assert res.status_code == 400
        assert isinstance(res.get_json()["error"], str)

    def test_null_body(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={"body": None}, headers=alice_h)
        assert res.status_code == 400

    def test_wrong_field_name_content_is_rejected(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={"content": "hello"}, headers=alice_h)
        assert res.status_code == 400

    def test_non_string_body(self, client, comments_url, alice_h):
        assert client.post(comments_url, json={"body": 123}, headers=alice_h).status_code == 400

    def test_body_over_max_length(self, client, comments_url, alice_h):
        res = client.post(comments_url, json={"body": "x" * 2001}, headers=alice_h)
        assert res.status_code == 400

    def test_nothing_is_stored_on_400(self, client, db, comments_url, alice_h):
        client.post(comments_url, json={"body": ""}, headers=alice_h)
        assert Comment.query.count() == 0

    def test_empty_body_on_patch(self, client, alice_comment, alice_h):
        url = f"/api/comments/{alice_comment.id}"
        assert client.patch(url, json={"body": ""}, headers=alice_h).status_code == 400
        assert client.patch(url, json={}, headers=alice_h).status_code == 400


# --------------------------------------------------------------------------
# 3. 401 Unauthorized: no JWT
# --------------------------------------------------------------------------
class TestNoToken401:
    def test_post_without_token(self, client, comments_url):
        res = client.post(comments_url, json={"body": "hi"})
        assert res.status_code == 401
        assert isinstance(res.get_json()["error"], str)

    def test_post_without_token_stores_nothing(self, client, comments_url):
        client.post(comments_url, json={"body": "hi"})
        assert Comment.query.count() == 0

    def test_get_without_token(self, client, comments_url):
        assert client.get(comments_url).status_code == 401

    def test_patch_without_token(self, client, alice_comment):
        res = client.patch(f"/api/comments/{alice_comment.id}", json={"body": "edit"})
        assert res.status_code == 401

    def test_delete_without_token(self, client, alice_comment):
        assert client.delete(f"/api/comments/{alice_comment.id}").status_code == 401

    def test_malformed_token(self, client, comments_url):
        res = client.post(comments_url, json={"body": "hi"}, headers={"Authorization": "Bearer junk"})
        assert res.status_code == 401

    def test_wrong_auth_scheme(self, client, comments_url):
        res = client.post(comments_url, json={"body": "hi"}, headers={"Authorization": "Basic abc"})
        assert res.status_code == 401

    def test_401_precedes_validation(self, client, comments_url):
        """An invalid payload without a token is still a 401, not a 400."""
        assert client.post(comments_url, json={"body": ""}).status_code == 401


# --------------------------------------------------------------------------
# 4. 403 Forbidden: PATCH / DELETE another user's comment
# --------------------------------------------------------------------------
class TestOtherUsersComment403:
    def test_member_cannot_patch_admins_comment(self, client, db, alice_comment, bob_h):
        res = client.patch(f"/api/comments/{alice_comment.id}", json={"body": "hijacked"}, headers=bob_h)
        assert res.status_code == 403
        assert isinstance(res.get_json()["error"], str)
        db.session.expire_all()
        assert db.session.get(Comment, alice_comment.id).body == "Alice wrote this"

    def test_member_cannot_delete_admins_comment(self, client, db, alice_comment, bob_h):
        res = client.delete(f"/api/comments/{alice_comment.id}", headers=bob_h)
        assert res.status_code == 403
        db.session.expire_all()
        assert db.session.get(Comment, alice_comment.id).deleted_at is None

    def test_admin_cannot_patch_members_comment(self, client, card, bob, alice_h):
        comment = make_comment(card, bob, "Bob wrote this")
        res = client.patch(f"/api/comments/{comment.id}", json={"body": "edited by admin"}, headers=alice_h)
        assert res.status_code == 403

    def test_admin_cannot_delete_members_comment(self, client, db, card, bob, alice_h):
        """Board admin role does not override authorship."""
        comment = make_comment(card, bob, "Bob wrote this")
        res = client.delete(f"/api/comments/{comment.id}", headers=alice_h)
        assert res.status_code == 403
        db.session.expire_all()
        assert db.session.get(Comment, comment.id).deleted_at is None

    def test_valid_body_from_non_author_is_still_403(self, client, alice_comment, bob_h):
        res = client.patch(f"/api/comments/{alice_comment.id}", json={"body": "valid"}, headers=bob_h)
        assert res.status_code == 403

    def test_non_member_is_403_on_all_comment_routes(self, client, card, alice_comment, carol_h):
        assert client.post(f"/api/cards/{card.id}/comments", json={"body": "hi"}, headers=carol_h).status_code == 403
        assert client.get(f"/api/cards/{card.id}/comments", headers=carol_h).status_code == 403
        assert client.patch(f"/api/comments/{alice_comment.id}", json={"body": "x"}, headers=carol_h).status_code == 403
        assert client.delete(f"/api/comments/{alice_comment.id}", headers=carol_h).status_code == 403


# --------------------------------------------------------------------------
# Author happy paths and remaining behaviour
# --------------------------------------------------------------------------
class TestAuthorActions:
    def test_author_can_patch(self, client, alice_comment, alice_h):
        res = client.patch(f"/api/comments/{alice_comment.id}", json={"body": " edited "}, headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["body"] == "edited"

    def test_author_can_delete_softly(self, client, db, card, alice_comment, alice_h):
        res = client.delete(f"/api/comments/{alice_comment.id}", headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"] == {"id": alice_comment.id}
        assert db.session.get(Comment, alice_comment.id).deleted_at is not None
        assert client.get(f"/api/cards/{card.id}/comments", headers=alice_h).get_json()["data"] == []

    def test_deleted_comment_is_404(self, client, alice_comment, alice_h):
        client.delete(f"/api/comments/{alice_comment.id}", headers=alice_h)
        assert client.patch(f"/api/comments/{alice_comment.id}", json={"body": "x"}, headers=alice_h).status_code == 404
        assert client.delete(f"/api/comments/{alice_comment.id}", headers=alice_h).status_code == 404

    def test_unknown_ids_are_404(self, client, alice_h):
        assert client.post(f"/api/cards/{MISSING}/comments", json={"body": "x"}, headers=alice_h).status_code == 404
        assert client.get(f"/api/cards/{MISSING}/comments", headers=alice_h).status_code == 404
        assert client.patch(f"/api/comments/{MISSING}", json={"body": "x"}, headers=alice_h).status_code == 404
        assert client.delete(f"/api/comments/{MISSING}", headers=alice_h).status_code == 404

    def test_comments_listed_oldest_first(self, client, card, alice, bob, alice_h):
        make_comment(card, alice, "one")
        make_comment(card, bob, "two")
        listed = client.get(f"/api/cards/{card.id}/comments", headers=alice_h).get_json()["data"]
        assert [c["body"] for c in listed] == ["one", "two"]


class TestCommentNotifications:
    def test_comment_notifies_assignee(self, client, db, card, alice, bob, alice_h, bob_h):
        card.assignee_id = bob.id
        db.session.commit()
        client.post(f"/api/cards/{card.id}/comments", json={"body": "ping"}, headers=alice_h)
        notes = Notification.query.filter_by(recipient_id=bob.id, type="comment_added").all()
        assert len(notes) == 1
        assert notes[0].actor_id == alice.id
        assert notes[0].card_id == card.id

    def test_commenting_on_own_assigned_card_does_not_notify(self, client, db, card, bob, bob_h):
        card.assignee_id = bob.id
        db.session.commit()
        client.post(f"/api/cards/{card.id}/comments", json={"body": "note to self"}, headers=bob_h)
        assert Notification.query.count() == 0

    def test_unassigned_card_creates_no_notification(self, client, card, alice_h):
        client.post(f"/api/cards/{card.id}/comments", json={"body": "hi"}, headers=alice_h)
        assert Notification.query.count() == 0
