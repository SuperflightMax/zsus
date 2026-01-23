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
