# Работа с AI-агентом через задачи Resources

## Knowledge

- [GitHub Docs: About issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)
  Официальная документация GitHub: issues подходят для планирования, обсуждения и отслеживания работы; большие задачи можно разбивать на sub-issues.
- [GitHub Docs: REST API endpoints for sub-issues](https://docs.github.com/en/rest/issues/sub-issues)
  Официальная документация GitHub по parent/sub-issue связям. Использовать для оформления настоящей иерархии задач.
- [Anthropic Claude Code Docs: common workflows](https://code.claude.com/docs/en/common-workflows)
  Практики работы с агентом в кодовой базе: найти контекст, исправлять баги через воспроизводимые ошибки, писать и запускать тесты, делать изменения малыми проверяемыми шагами.
- [OpenAI API Docs: Using tools](https://developers.openai.com/api/docs/guides/tools)
  Официальная документация по инструментам для агентных сценариев: web search, function calling, remote MCP, shell, computer use и другие tool-based workflows.
- [Python Docs: unittest](https://docs.python.org/3/library/unittest.html)
  Официальная документация Python по встроенному test framework. Использовать для красных/зелёных тестов в этом проекте.
- [Issue #9: серверный бот 24/7](https://github.com/serejaris/tg-bot-writer/issues/9)
  Главный кейс урока: parent issue, sub-issues, фиксация прогресса, E2E и закрытие.
- [Issue #21: уроки работы с агентом](https://github.com/serejaris/tg-bot-writer/issues/21)
  Учебный follow-up по итогам сессии: GitHub issue как центр управления, контракты перед кодом, красные тесты, Telethon E2E, fix-issues и push перед закрытием.

## Wisdom (Communities)

- GitHub Issues текущего проекта
  Главная рабочая среда для закрепления навыка: каждый следующий проект можно вести тем же способом.

## Reusable practices

- Начинать не с кода, а с parent issue и критериев готовности.
- Разбивать большие цели на sub-issues через Relationships.
- Описывать контракты до тестов и реализации.
- Требовать красные тесты до кода и зелёные тесты после минимальной реализации.
- Проверять интеграции настоящим E2E-сценарием, а не только unit-тестами.
- Оформлять найденные E2E-проблемы отдельными fix-issues.
- Не закрывать issue до push и финального комментария с результатом.
- Не хранить секреты в git, issue, README, PRD, комментариях и логах.

## Gaps

- Нужен следующий урок про то, как самому писать хороший parent issue для агента.
- Нужен отдельный мини-гайд про безопасную работу с секретами в серверных агентных пайплайнах.
- Нужен отдельный мини-гайд про E2E-проверку Telegram-ботов через Telethon и тестовые аккаунты.