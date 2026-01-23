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

# VPS quick scripts (Ubuntu 24.04, prototype-friendly)

- Bootstrap (creates `.venv`, installs deps, copies `.env` if missing):
  - `./boot.sh`
- Update from git + reinstall + log deploy:
  - `./update.sh`
- Run CLI (passes through args):
  - `./cli.sh --help`
- Check environment health:
  - `./doctor.sh`

Sample queries (UA/RU/surzhyk):
- “що є на складі?”
- “де всі каністри?”
- “я забрав усі фляги”
- “поклади всі бинти в аптечку”
- “додай 5 рукавиць на склад”
- “медичне що є?”
