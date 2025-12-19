# Core Command Contracts

Все изменения состояния склада выполняются **только через ядро**
путём передачи структурированных команд.

Ядро не принимает:
- текст
- изображения
- аудио
- неструктурированные данные

---

## Общий формат команды

```json
{
  "storage_id": "string",
  "command": "string",
  "payload": { }
}
```
---

### Команда: create_storage

Создание нового склада (используется тестами и инфраструктурой).

```json
{
  "command": "create_storage",
  "payload": {
    "storage_id": "test_storage_1"
  }
}
```
---

### Команда: delete_storage

```json
{
  "command": "delete_storage",
  "payload": {
    "storage_id": "test_storage_1"
  }
}
```
---

### Команда: intake

```json
{
  "command": "intake",
  "payload": {
    "items": [
      { "item_id": "pm_pistol", "qty": 1, "location": "сейф в кабинете" },
      { "item_id": "9mm_ammo", "qty": 28, "location": null }
    ]
  }
}
```

Инварианты (MVP):
- `items` — непустой массив
- `qty` для каждой позиции — строго `> 0`
- `location` может быть `null` (предмет без размещения)
- `item_id` создаётся в справочнике при первом появлении

---

### Команда: move

Перемещение предмета.

```json
{
  "command": "move",
  "payload": {
    "item_id": "radio",
    "qty": 2,
    "from": null,
    "to": "A1"
  }
}
```

Инварианты (MVP):
- `qty > 0`
- предмет должен существовать и иметь достаточный остаток на `from`
- при отсутствии предмета или недостаточном остатке ядро возвращает ошибку
- локации `from` и `to` могут быть `null` (перемещение с/без размещения)

---

### Команда: find

Поиск предмета.

```json
{
  "command": "find",
  "payload": {
    "item_id": "radio"
  }
}
```

---

### Ответ ядра (общий)

```json
{
  "status": "ok | error",
  "data": { }
}
```
Ядро не формирует человеко-читаемые тексты.
