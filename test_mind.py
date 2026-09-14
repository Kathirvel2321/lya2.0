"""Unit tests for LYA cloud reasoning gateway, persona brain, and memory scoping.

Checks:
1. Unified Groq key resolution across mind and forge (R06 fix).
2. Person-scoped memory injection into system prompt (guest vs verified owner).
3. Emotional tone detection and speech rate modulation.
4. Session history isolation and clearing.
5. Cloud gateway fallback behavior.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import mind
from storage import store


class MindGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "lya_test.db.enc"
        mind._histories.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        mind._histories.clear()

    def test_r06_unified_groq_key_resolution(self):
        # 1. When env var is set, get_groq_key returns it
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_key_123"}):
            self.assertEqual(mind.get_groq_key(), "gsk_test_key_123")

        # 2. When env var is absent, forge._groq uses mind.get_groq_key instead of crashing with KeyError
        from skills import forge
        with patch.dict(os.environ, {}, clear=True):
            with patch("brain.mind.get_groq_key", return_value=""):
                with self.assertRaises(RuntimeError) as ctx:
                    forge._groq("make a skill")
                self.assertIn("No Groq API key configured", str(ctx.exception))

    def test_guest_vs_verified_memory_scoping(self):
        # Setup: create Alice (admin) and Bob (friend) with memories in encrypted store
        p_alice = store.create_person("Alice", role="admin", db_path=self.db_path)
        p_bob = store.create_person("Bob", role="friend", db_path=self.db_path)

        store.remember(p_alice, "bank_pin", "secret 9999", kind="private", db_path=self.db_path)
        store.remember(p_bob, "favorite_color", "emerald blue", kind="preference", db_path=self.db_path)

        captured_messages = []
        def mock_client(messages):
            captured_messages.append(messages)
            return "Mock AI reply"

        # 1. Unverified guest interaction
        mind.reply("Hello LYA", admin_name="Alice", verified=False, session_id="s_guest",
                   person_id=p_alice, client_fn=mock_client)
        guest_prompt = captured_messages[-1][0]["content"]
        self.assertIn("(private memory unavailable)", guest_prompt)
        self.assertNotIn("secret 9999", guest_prompt)
        self.assertIn("NOT identity-verified", guest_prompt)

        # 2. Verified Alice interaction (owner)
        mind.reply("What is my pin?", admin_name="Alice", verified=True, session_id="s_alice",
                   person_id=p_alice, client_fn=mock_client, db_path=self.db_path)
        alice_prompt = captured_messages[-1][0]["content"]
        self.assertIn("bank_pin", alice_prompt)
        self.assertIn("secret 9999", alice_prompt)
        self.assertNotIn("emerald blue", alice_prompt)

    def test_tone_detection_and_speech_modulation(self):
        # Test emotional tone classification
        self.assertEqual(mind.detect_tone("haha that was a hilarious joke!"), "playful")
        self.assertEqual(mind.detect_tone("I am so sad and hurting right now"), "sad")
        self.assertEqual(mind.detect_tone("This is an important warning, listen carefully"), "serious")
        self.assertEqual(mind.detect_tone("I am so furious and angry"), "angry")
        self.assertEqual(mind.detect_tone("What is 2 + 2?"), "neutral")

        # Test set_tone safely updates voice rate without raising exception
        mind.set_tone("excited")
        mind.set_tone("sad")
        mind.set_tone("neutral")

    def test_session_history_isolation(self):
        def mock_client(messages):
            return f"Echo: {messages[-1]['content']}"

        # Session 1 interaction
        mind.reply("My secret code is alpha", session_id="sess_1", verified=True, client_fn=mock_client)
        # Session 2 interaction
        mind.reply("What is my secret code?", session_id="sess_2", verified=True, client_fn=mock_client)

        # Check session 2 history does NOT contain session 1 messages
        sess_2_history = mind._histories.get(("sess_2", True, None), [])
        self.assertTrue(sess_2_history)
        history_text = " ".join(m["content"] for m in sess_2_history)
        self.assertNotIn("alpha", history_text)

        # Clear session 1
        mind.clear_history("sess_1")
        self.assertNotIn(("sess_1", True, None), mind._histories)

    def test_person_switch_does_not_reuse_same_session_history(self):
        captured = []
        def client(messages):
            captured.append(messages)
            return "Fixture response"
        with patch.object(mind, "_memory_block", return_value=""):
            mind.reply("ALICE_ONLY_FIXTURE", verified=True, session_id="shared", person_id="alice", client_fn=client)
            mind.reply("Hello", verified=True, session_id="shared", person_id="bob", client_fn=client)
        self.assertNotIn("ALICE_ONLY_FIXTURE", str(captured[-1]))
        self.assertIn(("shared", True, "bob"), mind._histories)
        mind.clear_history("shared")
        self.assertFalse(mind._histories)

    def test_offline_gateway_fallback_message(self):
        # When all external and local providers fail, returns friendly recoverable message
        with patch.dict(os.environ, {"GROQ_API_KEY": "", "OPENAI_API_KEY": "", "OMNIROUTE_KEY": ""}):
            with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("Connection refused")):
                res = mind._chat([{"role": "user", "content": "hi"}])
                self.assertIn("My brain is offline", res)
                self.assertIn("GROQ_API_KEY", res)


if __name__ == "__main__":
    unittest.main()
