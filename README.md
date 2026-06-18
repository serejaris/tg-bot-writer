# tg-bot-writer

Контент-завод для Telegram-канала: идеи превращаются в тексты постов, складываются в репозиторий и готовятся к ежедневной публикации по расписанию.

Сейчас работает **этап 1** — тексты и контент-план. Автопубликация — следующий этап.

## Пайплайн

```mermaid
flowchart TB
    subgraph input["Вход"]
        U[("👤 Автор")]
        I["Идея / тема / набросок"]
    end

    subgraph config["Конфигурация"]
        B["channel-brief.md<br/>аудитория, тон, ограничения"]
    end

    subgraph agent["Агент (Cursor)"]
        R["Читает brief и контент-план"]
        Q{"Нужны<br/>уточнения?"}
        W["Пишет текст поста"]
        V["Проверяет формат и тон"]
    end

    subgraph storage["Репозиторий"]
        CP["content-plan/<br/>YYYY-MM.md"]
        D["posts/drafts/"]
        S["posts/scheduled/"]
        P["posts/published/"]
    end

    subgraph future["Этап 2 — планируется"]
        CRON["Планировщик"]
        BOT["Telegram Bot API"]
        CH[("📢 Канал")]
    end

    U --> I
    I --> R
    B --> R
    CP --> R
    R --> Q
    Q -->|да| U
    Q -->|нет| W
    W --> V
    V --> D
    V --> S
    V --> CP

    S -.->|по расписанию| CRON
    CRON -.-> BOT
    BOT -.-> CH
    CH -.-> P

    D -->|"редактура, дата назначена"| S
    S -->|"опубликовано"| P
```

## Жизненный цикл поста

```mermaid
stateDiagram-v2
    [*] --> idea: новая тема
    idea --> draft: агент написал текст
    draft --> scheduled: дата публикации назначена
    scheduled --> published: пост вышел в канал
    draft --> draft: правки
    scheduled --> draft: перенос / доработка
    published --> [*]
```

## Структура репозитория

```mermaid
flowchart LR
    ROOT["tg-bot-writer/"]

    ROOT --> AGENTS["AGENTS.md<br/>правила для агента"]
    ROOT --> BRIEF["channel-brief.md<br/>профиль канала"]
    ROOT --> PLAN["content-plan/<br/>план тем по месяцам"]
    ROOT --> POSTS["posts/"]

    POSTS --> DRAFTS["drafts/<br/>черновики"]
    POSTS --> SCHEDULED["scheduled/<br/>готовые с датой"]
    POSTS --> PUBLISHED["published/<br/>архив"]
```

## Как пользоваться

1. Заполни `channel-brief.md` — профиль канала.
2. Открой папку в Cursor и опиши идею: *«Напиши пост про … на завтра»*.
3. Агент сохранит файл в `posts/drafts/` или `posts/scheduled/` и обновит `content-plan/`.
4. Проверь превью, при необходимости попроси правки.

Правила работы агента — в [`AGENTS.md`](AGENTS.md).
