from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping


class UserVisibleError(Exception):
    """Error that can be safely shown to a Telegram user."""


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_channel_id: str
    glm_api_key: str
    glm_model: str
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


@dataclass(frozen=True)
class SavedPost:
    path: Path
    status: str


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = env if env is not None else os.environ
    missing = [
        name
        for name in (
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHANNEL_ID",
            "GLM_API_KEY",
            "GLM_MODEL",
        )
        if not source.get(name)
    ]
    if missing:
        raise UserVisibleError(
            "Не настроены переменные окружения: " + ", ".join(missing)
        )
    return Settings(
        telegram_bot_token=source["TELEGRAM_BOT_TOKEN"],
        telegram_channel_id=source["TELEGRAM_CHANNEL_ID"],
        glm_api_key=source["GLM_API_KEY"],
        glm_model=source["GLM_MODEL"],
        glm_base_url=source.get(
            "GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        ),
    )


class BotFlow:
    def __init__(self, generator, brief_text: str):
        self.generator = generator
        self.brief_text = brief_text
        self.idea: str | None = None
        self.directions: list[dict] = []
        self.hooks: list[dict] = []

    def start_idea(self, idea: str) -> dict:
        clean_idea = idea.strip()
        if not clean_idea:
            raise UserVisibleError("Пришли идею поста одним сообщением.")

        directions = self.generator.directions(clean_idea, self.brief_text)
        hooks = self.generator.hooks(clean_idea, directions, self.brief_text)
        self._require_count(directions, 3, "GLM должен вернуть 3 направления.")
        self._require_count(hooks, 3, "GLM должен вернуть 3 хука.")

        self.idea = clean_idea
        self.directions = directions
        self.hooks = hooks
        return {"directions": directions, "hooks": hooks}

    def create_post(self, direction_id: str, hook_id: str) -> dict:
        if self.idea is None:
            raise UserVisibleError("Сначала пришли идею поста.")

        direction = self._find_by_id(self.directions, direction_id, "направление")
        hook = self._find_by_id(self.hooks, hook_id, "хук")
        post = dict(
            self.generator.post(self.idea, direction, hook, self.brief_text)
        )
        body = str(post.get("body", "")).strip()
        hook_text = str(hook.get("text", "")).strip()
        if hook_text and not body.startswith(hook_text):
            body = f"{hook_text}\n\n{body}"
        post["body"] = body
        return post

    @staticmethod
    def _require_count(items: list[dict], expected: int, message: str) -> None:
        if len(items) != expected:
            raise UserVisibleError(message)

    @staticmethod
    def _find_by_id(items: list[dict], item_id: str, label: str) -> dict:
        for item in items:
            if item.get("id") == item_id:
                return item
        raise UserVisibleError(f"Не найден выбранный {label}.")


class PostStore:
    def __init__(self, root: Path):
        self.root = root

    def save(self, post: Mapping[str, object], date: str | None) -> SavedPost:
        if not _is_iso_date(date):
            raise UserVisibleError("Напиши дату публикации в формате YYYY-MM-DD.")

        status = "scheduled"
        post_dir = self.root / "posts" / "scheduled"
        post_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(str(post["title"]))
        path = _unique_path(post_dir / f"{date}-{slug}.md")

        tags = post.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        body = str(post.get("body", "")).strip()
        markdown = _render_post_markdown(
            title=str(post["title"]),
            publication_date=str(date),
            status=status,
            topic=str(post.get("topic", post["title"])),
            tags=[str(tag) for tag in tags],
            body=body,
        )
        path.write_text(markdown, encoding="utf-8")
        self._update_content_plan(str(date), post, path)
        return SavedPost(path=path, status=status)

    def _update_content_plan(
        self, publication_date: str, post: Mapping[str, object], path: Path
    ) -> None:
        plan_path = self.root / "content-plan" / "content-plan.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        if plan_path.exists():
            existing = plan_path.read_text(encoding="utf-8").rstrip()
        else:
            existing = (
                "| Дата | Нед. | Тип | Завтрак | Обед | Заметка | Статус | Файл |"
            )
        rel_path = path.relative_to(self.root)
        row = (
            f"| {publication_date} | — | пост | — | — | "
            f"{post.get('topic', post.get('title', 'пост'))} | scheduled | {rel_path} |"
        )
        plan_path.write_text(f"{existing}\n{row}\n", encoding="utf-8")


def publish_now(
    post: Mapping[str, object], *, publisher, confirmed: bool
) -> Mapping[str, object]:
    if not confirmed:
        raise UserVisibleError("Подтверди публикацию перед отправкой в канал.")
    return publisher.publish(str(post["body"]))


def _render_post_markdown(
    *,
    title: str,
    publication_date: str,
    status: str,
    topic: str,
    tags: list[str],
    body: str,
) -> str:
    tags_value = "[" + ", ".join(tags) + "]"
    return (
        "---\n"
        f'title: "{title}"\n'
        f"date: {publication_date}\n"
        f"status: {status}\n"
        f'topic: "{topic}"\n'
        f"tags: {tags_value}\n"
        'source: "telegram-bot"\n'
        f"created: {date.today().isoformat()}\n"
        "---\n\n"
        f"{body}\n"
    )


def _is_iso_date(value: str | None) -> bool:
    if value is None:
        return False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _slugify(value: str) -> str:
    translit = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    normalized = "".join(translit.get(char, char) for char in value.lower())
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "telegram-post"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise UserVisibleError("Не удалось подобрать имя файла для поста.")
