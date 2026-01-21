# ZSUS Storage Bot Core

Storage Bot Core — это движок учёта складов с интеллектуальным интерфейсом. Проект предназначен для работы с несколькими независимыми складами в рамках
одного codebase. Это **не мессенджер-бот** и **не UI-приложение**. Мессенджеры, CLI и будущие приложения — это лишь интерфейсы поверх ядра.

# MANDATORY READING - essential project documentation

## OBEY:

   **GUIDE.md** - guielines, istructions, rules for coding.

## **MUST FOLLOW:** 

     ...and SUGGEST RELEVANT UPDATES

   **DESIGN.md** - описание системы, основные принципы, цели
   **ARCHITECTURE.md** - принципы разработки, структура кода
   **LLM_DESIGN.md** - принципы использования LLM
   **MVP.md** - ограничения и принципы MVP - текущего этапа разработки
   **ROADMAP.md** - этапы разработки 

     ... and UPDATE WHEN NECESSARY

   **COMMANDS.md** - команды ядра
   **TESTS.md** - формат тестов и сценариев
   **CLI.md** - команды базового CLI 

## **MUST UPDATE with each PR**

   **HISTORY.md** - подробное описание изменений 
   **CHANGELOG.md** - журнал изменений, краткие описания 

# Quick run (local CLI + LLM)

1. Copy env template:
   - `cp env.example .env`
2. Set OpenAI credentials in `.env`:
   - `OPENAI_API_KEY=...`
   - `OPENAI_MODEL=gpt-4.1` (or another available model)
3. Run the CLI:
   - `python -m src.interfaces.cli.main`
4. Activate a storage (example):
   - `+activatestorage test_storage`

Sample queries (UA/RU/surzhyk):
- “що є на складі?”
- “де всі каністри?”
- “я забрав усі фляги”
- “поклади всі бинти в аптечку”
- “додай 5 рукавиць на склад”
- “медичне що є?”
