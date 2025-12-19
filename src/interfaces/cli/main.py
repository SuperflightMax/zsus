"""Command-line interface stub."""

from __future__ import annotations

import logging
import json
from typing import Any, Dict

from ...infra import load_config
from ...core.engine import handle_command


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def run() -> None:
    config = load_config()
    configure_logging(config.get("logging", {}).get("level", "INFO"))

    prompt = config.get("cli", {}).get("prompt", "> ")
    exit_commands = config.get("cli", {}).get("exit_commands", ["exit"])

    logging.info("CLI started. Type an exit command to quit.")

    try:
        while True:
            user_input = input(prompt)
            if user_input.strip() in exit_commands:
                logging.info("Exiting CLI.")
                break

            logging.info("Received input: %s", user_input)

            parsed_json = _try_parse_json(user_input)
            if parsed_json is not None:
                response = handle_command(parsed_json)
                print(json.dumps(response, ensure_ascii=False, indent=2))
            else:
                print(user_input)
    except KeyboardInterrupt:
        logging.info("CLI interrupted by user.")


def _try_parse_json(text: str) -> Dict[str, Any] | None:
    """Attempt to parse JSON input; return None on failure.

    JSON detection is intentionally simple: if the text starts with ``{`` and
    parses successfully, it is treated as a command for the core engine.
    Otherwise, the input is handled as plain text.
    """

    if not text.strip().startswith("{"):
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


if __name__ == "__main__":
    run()
