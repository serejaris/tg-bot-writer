from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .adapters import GLMJsonGenerator, TelegramPublisher, load_dotenv, read_brief
from .bot_core import BotFlow, PostStore, UserVisibleError, load_settings, publish_now


class TelegramBotClient:
    def __init__(self, bot_token: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict]:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        url = self.base_url + "/getUpdates?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=timeout + 10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("result", [])

    def send_message(self, chat_id: int | str, text: str) -> None:
        payload = json.dumps(
            build_bot_reply_payload(chat_id, text),
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30):
            return


def build_bot_reply_payload(chat_id: int | str, text: str) -> dict:
    return {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }


class LearningBot:
    def __init__(self, *, root: Path):
        load_dotenv(root / ".env")
        self.root = root
        self.settings = load_settings()
        brief = read_brief(root)
        generator = GLMJsonGenerator(
            api_key=self.settings.glm_api_key,
            model=self.settings.glm_model,
            base_url=self.settings.glm_base_url,
        )
        self.flow = BotFlow(generator=generator, brief_text=brief)
        self.store = PostStore(root=root)
        self.publisher = TelegramPublisher(
            bot_token=self.settings.telegram_bot_token,
            channel_id=self.settings.telegram_channel_id,
        )
        self.telegram = TelegramBotClient(self.settings.telegram_bot_token)
        self.current_post: dict | None = None

    def handle_text(self, text: str) -> str:
        clean = text.strip()
        if clean == "/start":
            return (
                "Пришли идею поста. После вариантов ответь так: `choose 1 2`."
            )
        if clean.startswith("choose "):
            return self._handle_choice(clean)
        if clean.startswith("save "):
            return self._handle_save(clean)
        if clean == "publish yes":
            return self._handle_publish()

        result = self.flow.start_idea(clean)
        return _format_options(result["directions"], result["hooks"])

    def _handle_choice(self, text: str) -> str:
        parts = text.split()
        if len(parts) != 3:
            raise UserVisibleError("Напиши выбор в формате: choose 1 2")
        direction_id = f"d{int(parts[1])}"
        hook_id = f"h{int(parts[2])}"
        self.current_post = self.flow.create_post(direction_id, hook_id)
        return (
            f"{self.current_post['body']}\n\n"
            "Что сделать дальше?\n"
            "- `save YYYY-MM-DD` — сохранить в контент-план\n"
            "- `publish yes` — опубликовать сейчас"
        )

    def _handle_save(self, text: str) -> str:
        if self.current_post is None:
            raise UserVisibleError("Сначала выбери направление и хук.")
        parts = text.split(maxsplit=1)
        saved = self.store.save(self.current_post, date=parts[1] if len(parts) == 2 else None)
        return f"Сохранено: `{saved.path}`\nСтатус: {saved.status}"

    def _handle_publish(self) -> str:
        if self.current_post is None:
            raise UserVisibleError("Сначала выбери направление и хук.")
        result = publish_now(self.current_post, publisher=self.publisher, confirmed=True)
        return f"Опубликовано. Telegram message_id: {result.get('message_id')}"

    def run_forever(self) -> None:
        offset = None
        while True:
            try:
                for update in self.telegram.get_updates(offset=offset):
                    offset = update["update_id"] + 1
                    message = update.get("message") or {}
                    chat = message.get("chat") or {}
                    text = message.get("text")
                    chat_id = chat.get("id")
                    if text and chat_id:
                        try:
                            answer = self.handle_text(text)
                        except UserVisibleError as exc:
                            answer = str(exc)
                        self.telegram.send_message(chat_id, answer)
            except Exception as exc:
                print(f"polling error: {exc}", file=sys.stderr)
                time.sleep(5)


def _format_options(directions: list[dict], hooks: list[dict]) -> str:
    direction_lines = [
        f"{index}. **{item['title']}** — {item['summary']}"
        for index, item in enumerate(directions, start=1)
    ]
    hook_lines = [
        f"{index}. {item['text']}" for index, item in enumerate(hooks, start=1)
    ]
    return (
        "**3 направления:**\n"
        + "\n".join(direction_lines)
        + "\n\n**3 хука:**\n"
        + "\n".join(hook_lines)
        + "\n\nОтветь выбором: `choose 1 2`"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    if args.dry_run:
        print("DRY_RUN_OK")
        return 0

    bot = LearningBot(root=Path(args.root).resolve())
    bot.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
