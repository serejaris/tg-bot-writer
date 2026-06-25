import importlib
import os
import tempfile
import unittest
from pathlib import Path


def load_adapters():
    try:
        return importlib.import_module("tg_bot_writer.adapters")
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "Ожидается модуль tg_bot_writer.adapters для внешних API"
        ) from exc


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.response


class AdapterTests(unittest.TestCase):
    def test_glm_generator_parses_three_directions_from_json_response(self):
        adapters = load_adapters()
        http = FakeHttpClient(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"directions": ['
                                '{"id":"d1","title":"A","summary":"a"},'
                                '{"id":"d2","title":"B","summary":"b"},'
                                '{"id":"d3","title":"C","summary":"c"}]}'
                            )
                        }
                    }
                ]
            }
        )
        generator = adapters.GLMJsonGenerator(
            api_key="key", model="glm-5.2", http_client=http
        )

        directions = generator.directions("идея", "brief")

        self.assertEqual(len(directions), 3)
        self.assertEqual(directions[0]["id"], "d1")
        self.assertIn("Bearer key", http.calls[0]["headers"]["Authorization"])
        self.assertEqual(http.calls[0]["payload"]["model"], "glm-5.2")
        self.assertGreaterEqual(http.calls[0]["payload"]["max_tokens"], 4096)

    def test_glm_generator_wraps_invalid_json_as_user_visible_error(self):
        adapters = load_adapters()
        http = FakeHttpClient(
            {"choices": [{"message": {"content": "это не json"}}]}
        )
        generator = adapters.GLMJsonGenerator(
            api_key="key", model="glm-5.2", http_client=http
        )

        with self.assertRaises(adapters.UserVisibleError) as ctx:
            generator.hooks("идея", [], "brief")

        self.assertEqual(str(ctx.exception), "Не получилось получить текст от GLM. Попробуй ещё раз.")

    def test_telegram_publisher_sends_message_to_channel(self):
        adapters = load_adapters()
        http = FakeHttpClient({"ok": True, "result": {"message_id": 7}})
        publisher = adapters.TelegramPublisher(
            bot_token="token", channel_id="channel", http_client=http
        )

        result = publisher.publish("готовый пост")

        self.assertEqual(result["message_id"], 7)
        self.assertTrue(http.calls[0]["url"].endswith("/bottoken/sendMessage"))
        self.assertEqual(http.calls[0]["payload"]["chat_id"], "channel")
        self.assertEqual(http.calls[0]["payload"]["text"], "готовый пост")

    def test_load_dotenv_reads_file_without_printing_secrets(self):
        adapters = load_adapters()
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=token\nGLM_MODEL=glm-5.2\n",
                encoding="utf-8",
            )
            original = dict(os.environ)
            try:
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("GLM_MODEL", None)
                loaded = adapters.load_dotenv(env_path)
            finally:
                os.environ.clear()
                os.environ.update(original)

        self.assertEqual(loaded, ["TELEGRAM_BOT_TOKEN", "GLM_MODEL"])


if __name__ == "__main__":
    unittest.main()
