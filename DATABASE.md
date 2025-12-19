# Database Model (per storage)

Каждый склад использует собственную базу данных.
База данных одного склада не содержит данных других складов.

---

## items

Справочник предметов, которые присутствовали на складе.
```
| field       | type       | description              |
|-------------|------------|--------------------------|
| id          | string     | нормализованный item_id  |
| name        | string     | человеко-читаемое имя    |
| created_at  | datetime   | дата первого появления   |
```
---

## locations

Справочник локаций внутри склада.
```
| field       | type     | description   |
|-------------|----------|---------------|
| id          | string   | location_id   |
| name        | string   | имя локации   |
| created_at  | datetime | дата создания |
```
---

## stock

Текущее состояние склада (остатки).
```
| field       | type     | description               |
|-------------|----------|---------------------------|
| item_id     | string   | ссылка на items.id        |
| location_id | string \ | null | null = без локации |
| qty         | integer  | количество                |
```
**Уникальный ключ:** `(item_id, location_id)`

---

## movements

История движений (журнал операций).
```
| field         | type     | description |
|---------------|----------|-------------|
| id            | integer  | primary key |
| type          | string   | intake / move / etc |
| item_id       | string   | предмет |
| qty           | integer  | количество |
| from_location | string \ | null | откуда |
| to_location   | string \ | null | куда |
| created_at    | datetime | время операции |
| meta          | json     | источник (text/image/audio) |
```
---

## meta (опционально)

Технические данные склада.
```
| field | type   | description |
|-------|--------|-------------|
| key   | string |             |
| value | string |             |

```

---

# Database Schema (per Storage)

Каждый склад использует **отдельную базу данных**.
Схема одинакова для SQLite и PostgreSQL.

База данных одного склада:
- не содержит данных других складов
- может быть создана и удалена независимо
- используется ядром через репозитории

---

## Общие принципы

- все идентификаторы (`item_id`, `location_id`) — строковые
- `NULL` используется как валидное состояние
- текущее состояние и история разделены
- все изменения фиксируются в журнале движений
- схема ориентирована на аудит и расширение

---

## Таблица: items

Справочник предметов, которые **когда-либо появлялись** на складе.

```sql
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
id — нормализованный item_id (используется ядром)
name — опционально, для удобства
предмет создаётся при первом intake, если отсутствует

---

## Таблица: locations

Справочник локаций внутри склада.

```sql
CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
отсутствие записи = локация не используется
предмет может существовать без локации (NULL)

---

## Таблица: stock

Текущее состояние склада (остатки).

```sql
CREATE TABLE stock (
    item_id TEXT NOT NULL,
    location_id TEXT NULL,
    qty INTEGER NOT NULL CHECK (qty >= 0),

    PRIMARY KEY (item_id, location_id),

    FOREIGN KEY (item_id) REFERENCES items(id)
        ON DELETE CASCADE,

    FOREIGN KEY (location_id) REFERENCES locations(id)
        ON DELETE SET NULL
);
```
location_id = NULL → предмет просто на складе
уникальность (item_id, location_id)
всегда хранит текущее состояние

---

## Таблица: movements

Журнал всех операций (аудит).

```sql
CREATE TABLE movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- SQLite
    -- id BIGSERIAL PRIMARY KEY           -- PostgreSQL

    type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),

    from_location TEXT NULL,
    to_location TEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    meta JSON
);
```
type: intake, move, adjust, etc
from_location и to_location могут быть NULL

meta:
источник (text / image / audio)
confidence LLM
raw input (по желанию)
SQLite: JSON хранится как TEXT
Postgres: JSONB (желательно)

Индексы (рекомендуемые)

CREATE INDEX idx_stock_item ON stock(item_id);
CREATE INDEX idx_movements_item ON movements(item_id);
CREATE INDEX idx_movements_created ON movements(created_at);

---

## Таблица: meta (техническая)

Хранение служебной информации склада.

```sql
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```
Примеры:
версия схемы
дата создания склада
произвольные флаги
Жизненный цикл данных

При **intake**
проверяется наличие item_id в items
при отсутствии — создаётся
обновляется stock
добавляется запись в movements

При **move**
уменьшается stock для from_location
увеличивается stock для to_location
добавляется запись в movements

При **ошибке**
изменения в stock не применяются
запись в movements не создаётся
(атомарность обеспечивается транзакцией)

---

**Почему такая схема**
одинаково работает в SQLite и Postgres
легко читать и отлаживать
предметы без локации — нативно
аудит встроен
готово к отчётам и мониторингу
не привязано к LLM или интерфейсам

**Что НЕ делается на этом этапе**
мягкое удаление
версии предметов
партии / серийники
сложные агрегации

Это сознательно отложено до следующих этапов.