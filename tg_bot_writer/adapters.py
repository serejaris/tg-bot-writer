from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Mapping

from .bot_core import UserVisibleError


class UrlLibHttpClient:
    def post_json(self, url: str, headers: Mapping[str, str], payload: Mapping) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise UserVisibleError("Не получилось получить ответ от внешнего сервиса.") from exc


class GLMJsonGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        http_client=None,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    ):
        self.api_key = api_key
        self.model = model
        self.http_client = http_client or UrlLibHttpClient()
        self.base_url = base_url

    def directions(self, idea: str, brief: str) -> list[dict]:
        payload = self._chat_payload(
            "Верни JSON с ключом directions: ровно 3 объекта id,title,summary.",
            idea,
            brief,
        )
        data = self._request_json(payload)
        return data["directions"]

    def hooks(self, idea: str, directions: list[dict], brief: str) -> list[dict]:
        payload = self._chat_payload(
            "Верни JSON с ключом hooks: ровно 3 объекта id,text. Хук это первые 1-2 строки поста.",
            json.dumps({"idea": idea, "directions": directions}, ensure_ascii=False),
            brief,
        )
        data = self._request_json(payload)
        return data["hooks"]

    def post(self, idea: str, direction: dict, hook: dict, brief: str) -> dict:
        payload = self._chat_payload(
            "Верни JSON с ключами title, topic, tags, body. Body должен быть готовым Telegram-постом без markdown-заголовков #.",
            json.dumps(
                {"idea": idea, "direction": direction, "hook": hook},
                ensure_ascii=False,
            ),
            brief,
        )
        return self._request_json(payload)

    def _chat_payload(self, instruction: str, user_content: str, brief: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты пишешь для Telegram-канала по правилам brief. "
                        "Отвечай только валидным JSON. "
                        f"Brief:\n{brief}"
                    ),
                },
                {"role": "user", "content": f"{instruction}\n\n{user_content}"},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }

    def _request_json(self, payload: Mapping) -> dict:
        response = self.http_client.post_json(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )
        try:
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise UserVisibleError("Не получилось получить текст от GLM. Попробуй ещё раз.") from exc


class TelegramPublisher:
    def __init__(self, *, bot_token: str, channel_id: str, http_client=None):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.http_client = http_client or UrlLibHttpClient()

    def publish(self, text: str) -> dict:
        response = self.http_client.post_json(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            headers={"Content-Type": "application/json"},
            payload={
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        )
        if not response.get("ok"):
            raise UserVisibleError("Не получилось опубликовать пост. Проверь права бота в канале.")
        result = response.get("result", {})
        return {"message_id": result.get("message_id")}


def load_dotenv(path: Path) -> list[str]:
    loaded = []
    if not path.exists():
        return loaded
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())
        loaded.append(key)
    return loaded


def read_brief(root: Path) -> str:
    brief_path = root / "channel-brief.md"
    if not brief_path.exists():
        raise UserVisibleError("Не найден channel-brief.md.")
    return brief_path.read_text(encoding="utf-8")
