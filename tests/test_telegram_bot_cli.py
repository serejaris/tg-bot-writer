import subprocess
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
