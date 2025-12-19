# 📄 ARCHITECTURE.md  
_(как устроен код и классы, по-человечески)_

```md
# Code Architecture Guide

Этот документ описывает структуру кода и принципы,
которых необходимо придерживаться при разработке.

---

## Base language - PYTHON

---

## Общая структура проекта

```mermaid
src/
├─ core/ # бизнес-логика
├─ llm/ # интерпретация намерений
├─ media/ # аудио и изображения
├─ knowledge/ # доменные знания
├─ interfaces/ # CLI, боты, приложения
└─ infra/ # хранилища, registry
tests/
├─ core/
├─ scenarios/
└─ media/
```
---

## core/

Содержит **только бизнес-логику**.
```mermaid
- entities/
  - Item
  - Location
  - Movement
- services/
  - IntakeService
  - MoveService
  - SearchService
- repository/
  - StorageRepository
- engine.py
  - точка входа для команд
```
core не импортирует ничего из llm, media или interfaces.

---

## llm/

Отвечает за:
- интерпретацию текста
- работу с изображениями
- формирование предложений и команд
- fallback-ответы

Содержит:
- Interpreter
- IntentResolver
- ProposalBuilder
- ConfirmationState

---

## media/

Отвечает за:
- хранение файлов
- транскрипцию аудио
- выдачу URL

core не знает о media.

---

## knowledge/

Статические и расширяемые знания:
- items.yaml
- synonyms.yaml
- locations.yaml

Используются LLM-слоем.

---

## interfaces/

Тонкие адаптеры:
- cli/
- telegram/ (future)
- whatsapp/ (future)

Они:
- принимают ввод
- передают его в общий пайплайн
- форматируют ответы

---

## infra/

- registry складов
- создание и удаление БД
- управление путями и окружением

---

## Основные запреты

- интерфейсы не содержат бизнес-логики
- LLM не вызывает core напрямую
- core не знает про LLM
- никакой логики «на глазок»

---

## Философия

Если система не уверена — она ничего не делает.
Если есть сомнение — задаётся вопрос.
Если нет подтверждения после вопроса — нет изменений.
