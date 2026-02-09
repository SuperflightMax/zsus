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

# Запуск HTTP-сервера (прототип)

HTTP сервер поднимается самим проектом на отдельном порту (по умолчанию 8123).

Конфиг порта опционально через .env:

ZSUS_HTTP_HOST=0.0.0.0
ZSUS_HTTP_PORT=8123

Запуск:
cd ~/zsus
bash http.sh

Проверка:
curl http://127.0.0.1:8123/health

Пример запроса:
curl -X POST http://127.0.0.1:8123/chat
 -H "Content-Type: application/json" -d '{"text":"покажи все что есть"}'


 **“Если потрібно доступ ззовні: відкрити порт у UFW: sudo ufw allow 8123/tcp”**

# VPS quick scripts (Ubuntu 24.04, prototype-friendly)

- Bootstrap (creates `.venv`, installs deps, copies `.env` if missing):
  - `./boot.sh`
- Update from git + reinstall + log deploy:
  - `./update.sh`
- Start HTTP server in background with PID/logs:
  - `./start.sh`
- Stop HTTP server:
  - `./stop.sh`
- Restart HTTP server:
  - `./restart.sh`
- Check HTTP server status:
  - `./status.sh`
- Run CLI (passes through args):
  - `./cli.sh --help`
- Check environment health:
  - `./doctor.sh`

# деплой на VPS (Ubuntu 24.04)

Робоча папка: ~/zsus/
Режим: прототип, без systemd/pm2
Перезапуск сервера = втрата контексту (це ок)

## Підготовка VPS (один раз)

Оновити систему та встановити базові пакети:

sudo apt update
sudo apt install -y git python3 python3-venv unzip

Отримання коду в ~/zsus/

Варіант А — клонувати конкретну гілку:

mkdir -p ~/zsus
cd ~
git clone -b НАЗВА_ГІЛКИ --single-branch URL_РЕПОЗИТОРІЮ zsus


cd ~/zsus

Приклад:
git clone -b dev --single-branch https://github.com/SuperflightMax/zsus zsus
 zsus

Варіант Б — якщо репозиторій уже є:

cd ~/zsus
git status
git pull --rebase

## Перший запуск (один раз для VPS)

Запустити bootstrap-скрипт:

cd ~/zsus
bash boot.sh

Скрипт:
створить .venv (якщо його нема)
встановить залежності
створить папку logs/
скопіює env.example → .env (якщо .env не існує)

Після цього відредагувати .env:
nano .env

Мінімально необхідно:
OPENAI_API_KEY=ваш_ключ

## Перевірка середовища

Запустити перевірку:

cd ~/zsus
bash doctor.sh

Очікування:
скрипт виведе OK / FAIL для кожного пункту
код виходу 0, якщо критичних проблем немає

## Запуск CLI

cd ~/zsus
bash cli.sh

## Android client (APK)

Android client lives in `/android` within this repository.

Build APK using Android Studio:
1. Open Android Studio.
2. Open the `/android` directory as a project.
3. Wait for Gradle sync to finish.
4. Build APK: `Build > Build Bundle(s) / APK(s) > Build APK`.

The resulting debug APK is stored under:
`/android/app/build/outputs/apk/debug/app-debug.apk`

Notes:
- APK is installed manually.
- Rebuild + reinstall is expected for config changes.
- No Play Store publishing is used.


## Оновлення коду

Коли потрібно підтягнути зміни:

cd ~/zsus
bash update.sh
bash doctor.sh
bash cli.sh

update.sh:

виконує git pull --rebase
перевстановлює залежності
записує дату та git hash у logs/deploy.log
якщо HTTP сервер працює, зупиняє його перед оновленням і запускає після (можна вимкнути через ZSUS_NO_RESTART=1)

## Логи

logs/deploy.log
історія деплоїв (дата + git hash)

logs/actions.log
лог виконаних команд/операцій (прототипний аудит)

## Типові проблеми

Скрипти не запускаються (permission denied):

cd ~/zsus
chmod +x boot.sh update.sh cli.sh doctor.sh

Потрібно змінити гілку:

cd ~/zsus
git fetch
git checkout НАЗВА_ГІЛКИ

Doctor каже, що нема OPENAI_API_KEY:

nano .env
(додати або виправити ключ)

Проблеми з Python або venv:

cd ~/zsus
rm -rf .venv
bash boot.sh

# Multi-instance VPS (1 склад = 1 сервіс)

Цільовий layout (новий робочий root, старий `~/zsus` поки не чіпаємо):

```
~/zs/instances/uzhas
~/zs/instances/bbs
~/zs/instances/demo
~/zs/update_all.sh
```

`update_all.sh` можна взяти з репозиторію (`ops/update_all.sh`) та скопіювати у `~/zs/`.
Приклади:

- `./update_all.sh` (оновити все)
- `./update_all.sh --no-restart` (оновити без рестартів)
- `./update_all.sh --only demo` (оновити один інстанс)

## Додати новий склад (інстанс) — path-based routing

> Всі інстанси працюють на одному домені через префікс шляху `/zsus/<id>/`.
> Nginx проксіює у localhost, зовнішні порти не відкриваємо.

1. Створити папку інстансу:
   - `mkdir -p ~/zs/instances/<id>`
2. Клонувати репозиторій:
   - `git clone <REPO_URL> ~/zs/instances/<id>`
3. Створити `.env`:
   - `cd ~/zs/instances/<id>`
   - `cp env.example .env`
4. Встановити параметри (приклад):
   - `ZSUS_HTTP_HOST=127.0.0.1`
   - `ZSUS_HTTP_PORT=8123` (унікальний порт для інстансу)
   - `DEFAULT_STORAGE=<id>` (або ім'я складу/профілю)
   - `STORAGE_TITLE=...`
5. Bootstrap:
   - `./boot.sh`
6. Запуск:
   - `./start.sh` (або через PM2)
7. Перевірка локально:
   - `curl http://127.0.0.1:<port>/health`

## Nginx / path-based proxy (поточна схема)

Проксі на інстанси через шлях одного домену:

- `https://superflight.vps.webdock.cloud/zsus/uzhas/` -> `127.0.0.1:8123`
- `https://superflight.vps.webdock.cloud/zsus/bbs/`   -> `127.0.0.1:8124`
- `https://superflight.vps.webdock.cloud/zsus/demo/`  -> `127.0.0.1:8111`
- `/zsus/` -> `301` на `/zsus/uzhas/`

**Важливо:** зовнішні порти 8123/8124/8111 не відкривати. В `.env` кожного інстансу
рекомендується `ZSUS_HTTP_HOST=127.0.0.1`, а nginx проксіює до localhost.

Приклад snippet (всередині `server { ... }`):

```
location = /zsus { return 301 /zsus/; }
location = /zsus/ { return 301 /zsus/uzhas/; }

location /zsus/uzhas/ {
    proxy_pass http://127.0.0.1:8123/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /zsus/bbs/ {
    proxy_pass http://127.0.0.1:8124/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /zsus/demo/ {
    proxy_pass http://127.0.0.1:8111/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Future: migrate to subdomains (коли буде свій домен/DNS)

Зараз піддомени неможливі, бо `*.vps.webdock.cloud` не контролюється нами (DNS wildcard
для `zsusuzhas.*` повертає пусто). Якщо буде власний домен, схема може бути така:

- `uzhas.<your-domain>` -> `127.0.0.1:8123`
- `bbs.<your-domain>`   -> `127.0.0.1:8124`
- `demo.<your-domain>`  -> `127.0.0.1:8111`

Потрібно буде налаштувати DNS записи й сертифікати (Certbot з SAN на всі піддомени).

## PM2 (опційно)

Якщо використовуєте PM2 для керування всіма інстансами:

- `ops/pm2_start_all.sh`
- `ops/pm2_stop_all.sh`
- `ops/pm2_restart_all.sh`
- `ops/pm2_status.sh`
