import importlib
import os
import tempfile
import unittest
from pathlib import Path


def load_bot_core():
    try:
        return importlib.import_module("tg_bot_writer.bot_core")
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "Ожидается модуль tg_bot_writer.bot_core для серверного бота"
        ) from exc


class FakeGenerator:
    def __init__(self):
        self.calls = []

    def directions(self, idea, brief):
        self.calls.append(("directions", idea, brief))
        return [
            {"id": "d1", "title": "Практично", "summary": "Быстро и по делу"},
            {"id": "d2", "title": "Для семьи", "summary": "С фокусом на детей"},
            {"id": "d3", "title": "Экономно", "summary": "Из того, что есть дома"},
        ]

    def hooks(self, idea, directions, brief):
        self.calls.append(("hooks", idea, directions, brief))
        return [
            {"id": "h1", "text": "Остался рис? Это уже завтрак."},
            {"id": "h2", "text": "Пять минут — и дети едят."},
            {"id": "h3", "text": "Завтрак начинается с холодильника."},
        ]

    def post(self, idea, direction, hook, brief):
        self.calls.append(("post", idea, direction, hook, brief))
        return {
            "title": "Быстрый завтрак из риса",
            "topic": "быстрый завтрак из остатков",
            "tags": ["завтрак", "остатки"],
            "body": (
                "Остался рис? Это уже завтрак.\n\n"
                "**Идея:** смешай рис с яйцом и сыром.\n"
                "Готово для Telegram."
            ),
        }


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, text):
        self.messages.append(text)
        return {"ok": True, "message_id": 42}


class BotCoreTests(unittest.TestCase):
    def test_load_settings_reads_required_environment(self):
        bot_core = load_bot_core()

        env = {
            "TELEGRAM_BOT_TOKEN": "telegram-token",
            "TELEGRAM_CHANNEL_ID": "channel-id",
            "GLM_API_KEY": "glm-key",
            "GLM_MODEL": "glm-5.2",
        }

        settings = bot_core.load_settings(env)

        self.assertEqual(settings.telegram_bot_token, "telegram-token")
        self.assertEqual(settings.telegram_channel_id, "channel-id")
        self.assertEqual(settings.glm_api_key, "glm-key")
        self.assertEqual(settings.glm_model, "glm-5.2")

    def test_start_idea_returns_three_directions_and_three_hooks(self):
        bot_core = load_bot_core()
        generator = FakeGenerator()
        flow = bot_core.BotFlow(generator=generator, brief_text="brief")

        result = flow.start_idea("быстрый завтрак из остатков риса")

        self.assertEqual(len(result["directions"]), 3)
        self.assertEqual(len(result["hooks"]), 3)
        self.assertEqual(generator.calls[0][0], "directions")
        self.assertEqual(generator.calls[1][0], "hooks")

    def test_empty_idea_returns_human_readable_error(self):
        bot_core = load_bot_core()
        flow = bot_core.BotFlow(generator=FakeGenerator(), brief_text="brief")

        with self.assertRaises(bot_core.UserVisibleError) as ctx:
            flow.start_idea("   ")

        self.assertEqual(str(ctx.exception), "Пришли идею поста одним сообщением.")

    def test_selected_direction_and_hook_create_one_ready_post(self):
        bot_core = load_bot_core()
        flow = bot_core.BotFlow(generator=FakeGenerator(), brief_text="brief")
        flow.start_idea("быстрый завтрак из остатков риса")

        post = flow.create_post(direction_id="d1", hook_id="h2")

        self.assertEqual(post["title"], "Быстрый завтрак из риса")
        self.assertEqual(post["topic"], "быстрый завтрак из остатков")
        self.assertIn("Пять минут", post["body"])

    def test_save_post_requires_publication_date(self):
        bot_core = load_bot_core()
        flow = bot_core.BotFlow(generator=FakeGenerator(), brief_text="brief")
        flow.start_idea("быстрый завтрак из остатков риса")
        post = flow.create_post(direction_id="d1", hook_id="h1")

        with tempfile.TemporaryDirectory() as tmp:
            store = bot_core.PostStore(root=Path(tmp))
            with self.assertRaises(bot_core.UserVisibleError) as ctx:
                store.save(post, date=None)

        self.assertEqual(str(ctx.exception), "Напиши дату публикации в формате YYYY-MM-DD.")

    def test_save_post_writes_markdown_and_updates_content_plan(self):
        bot_core = load_bot_core()
        flow = bot_core.BotFlow(generator=FakeGenerator(), brief_text="brief")
        flow.start_idea("быстрый завтрак из остатков риса")
        post = flow.create_post(direction_id="d1", hook_id="h1")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content-plan").mkdir()
            (root / "content-plan" / "content-plan.md").write_text(
                "| Дата | Нед. | Тип | Завтрак | Обед | Заметка | Статус | Файл |\n",
                encoding="utf-8",
            )
            saved = bot_core.PostStore(root=root).save(post, date="2026-06-26")

            post_text = saved.path.read_text(encoding="utf-8")
            plan_text = (root / "content-plan" / "content-plan.md").read_text(
                encoding="utf-8"
            )

        self.assertEqual(saved.status, "scheduled")
        self.assertIn("status: scheduled", post_text)
        self.assertIn("date: 2026-06-26", post_text)
        self.assertNotIn("# ", post_text.split("---", 2)[-1])
        self.assertIn("2026-06-26", plan_text)
        self.assertIn(str(saved.path.relative_to(root)), plan_text)

    def test_publish_now_requires_confirmation(self):
        bot_core = load_bot_core()
        publisher = FakePublisher()
        post = {"body": "Готовый пост"}

        with self.assertRaises(bot_core.UserVisibleError) as ctx:
            bot_core.publish_now(post, publisher=publisher, confirmed=False)

        self.assertEqual(str(ctx.exception), "Подтверди публикацию перед отправкой в канал.")
        self.assertEqual(publisher.messages, [])

    def test_publish_now_sends_ready_post_after_confirmation(self):
        bot_core = load_bot_core()
        publisher = FakePublisher()
        post = {"body": "Готовый пост"}

        result = bot_core.publish_now(post, publisher=publisher, confirmed=True)

        self.assertEqual(result["message_id"], 42)
        self.assertEqual(publisher.messages, ["Готовый пост"])


if __name__ == "__main__":
    unittest.main()
