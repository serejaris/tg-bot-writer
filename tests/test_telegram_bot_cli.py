import subprocess
import sys
import unittest

from tg_bot_writer.telegram_bot import build_bot_reply_payload


class TelegramBotCliTests(unittest.TestCase):
    def test_dry_run_checks_imports_without_starting_polling(self):
        result = subprocess.run(
            [sys.executable, "-m", "tg_bot_writer.telegram_bot", "--dry-run"],
            cwd=".",
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY_RUN_OK", result.stdout)

    def test_bot_reply_payload_does_not_use_markdown_parse_mode(self):
        payload = build_bot_reply_payload(123, "Опубликовано. Telegram message_id: 42")

        self.assertEqual(payload["chat_id"], 123)
        self.assertEqual(payload["text"], "Опубликовано. Telegram message_id: 42")
        self.assertNotIn("parse_mode", payload)


if __name__ == "__main__":
    unittest.main()
