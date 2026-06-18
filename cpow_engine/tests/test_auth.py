"""Session auth — tokens and account registry."""

import unittest

from cpow_engine.auth import (
    AccountRegistry,
    SessionTokenError,
    issue_session_token,
    verify_session_token,
)


class TestSessionTokens(unittest.TestCase):
    def test_issue_and_verify(self) -> None:
        token = issue_session_token("alice", secret="test-secret", ttl_sec=3600.0)
        user_id = verify_session_token(token, secret="test-secret")
        self.assertEqual(user_id, "alice")

    def test_expired_token_rejected(self) -> None:
        import base64
        import json

        token = issue_session_token("bob", secret="s", ttl_sec=60.0)
        body = token.rsplit(".", 1)[0]
        pad = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + pad))
        with self.assertRaises(SessionTokenError):
            verify_session_token(token, secret="s", now=float(payload["exp"]) + 1.0)

    def test_tampered_token_rejected(self) -> None:
        token = issue_session_token("carol", secret="s")
        bad = token[:-2] + "xx"
        with self.assertRaises(SessionTokenError):
            verify_session_token(bad, secret="s")


class TestAccountRegistry(unittest.TestCase):
    def test_register_and_authenticate(self) -> None:
        reg = AccountRegistry()
        created = reg.register("player1", "password123")
        self.assertTrue(created.ok, created.reason)
        auth = reg.authenticate("player1", "password123")
        self.assertTrue(auth.ok)
        self.assertEqual(auth.user_id, "player1")

    def test_duplicate_user_rejected(self) -> None:
        reg = AccountRegistry()
        reg.register("dup", "password123")
        again = reg.register("dup", "password456")
        self.assertFalse(again.ok)
        self.assertEqual(again.reason, "user_id_taken")

    def test_wrong_password_rejected(self) -> None:
        reg = AccountRegistry()
        reg.register("user", "password123")
        bad = reg.authenticate("user", "wrongpass")
        self.assertFalse(bad.ok)
        self.assertEqual(bad.reason, "invalid_credentials")


if __name__ == "__main__":
    unittest.main()
