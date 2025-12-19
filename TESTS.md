# 📄 TESTS.md  
_(формат тестов и сценариев)_

```md
# Test Scenarios

Система поддерживает сценарные тесты,
которые описывают реальные пользовательские потоки.

---

## Общие принципы

- каждый сценарий создаёт новый склад
- сценарий полностью изолирован
- сценарий может быть запущен:
  - автоматически
  - вручную
  - локально или на сервере

---

## Формат сценария (YAML)

```yaml
name: basic_intake_flow
storage:
  create: true

steps:
  - type: core
    command:
      command: intake
      payload:
        item_id: radio
        qty: 10
        location: null

  - type: user
    input:
      text: "приняв 5 рацій"
      lang: uk
    expect:
      intent: intake

  - type: user
    input:
      image: tests/media/radios.jpg
    expect:
      type: proposal

  - type: user
    input:
      text: "так"
    expect:
      command: intake

assert:
  items:
    radio:
      qty: 15

### Типы шагов:

**type: core**
команда напрямую в ядро
используется для наполнения и быстрых проверок

**type: user**
симулирует пользователя
проходит через LLM и весь пайплайн

## LLM-тесты

Сценарии с LLM могут быть помечены:

```yaml
requires_llm: true

И отключены по умолчанию.