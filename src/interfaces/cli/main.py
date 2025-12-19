"""Command-line interface stub."""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List

from ...infra import load_config
from ...core.engine import handle_command


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def run() -> None:
    config = load_config()
    configure_logging(config.get("logging", {}).get("level", "INFO"))

    prompt = config.get("cli", {}).get("prompt", "> ")
    json_prompt = config.get("cli", {}).get("json_prompt", "... ")
    exit_commands = config.get("cli", {}).get("exit_commands", ["exit"])

    logging.info("CLI started. Type an exit command to quit.")

    collecting_json = False
    json_lines: List[str] = []
    brace_balance = 0

    try:
        while True:
            user_input = input(json_prompt if collecting_json else prompt)

            if not collecting_json:
                if user_input.strip() in exit_commands:
                    logging.info("Exiting CLI.")
                    break

                logging.info("Received input: %s", user_input)

                if _starts_json(user_input):
                    collecting_json = True
                    json_lines = [user_input]
                    brace_balance = _update_brace_balance(brace_balance, user_input)
                    if _json_complete(brace_balance, user_input):
                        _process_json_block("\n".join(json_lines))
                        collecting_json = False
                        json_lines = []
                        brace_balance = 0
                else:
                    print(user_input)
            else:
                json_lines.append(user_input)
                brace_balance = _update_brace_balance(brace_balance, user_input)

                if _json_complete(brace_balance, user_input):
                    _process_json_block("\n".join(json_lines))
                    collecting_json = False
                    json_lines = []
                    brace_balance = 0

    except KeyboardInterrupt:
        logging.info("CLI interrupted by user.")


def _starts_json(text: str) -> bool:
    """Return True if the input should be treated as JSON."""
    return text.strip().startswith("{")


def _json_complete(brace_balance: int, latest_line: str) -> bool:
    """Determine whether the collected JSON block is complete.

    Completion rules:
    - braces balanced (<= 0 to allow immediate single-line completion)
    - OR empty line
    """

    return brace_balance <= 0 or latest_line.strip() == ""


def _process_json_block(text: str) -> None:
    """Parse and dispatch a collected JSON block."""

    parsed = _try_parse_json(text)
    if parsed is not None:
        response = handle_command(parsed)
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print("Не удалось прочитать JSON. Попробуйте ещё раз.")


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


def _update_brace_balance(current_balance: int, text: str) -> int:
    """Update brace balance counter based on the provided text."""

    return current_balance + text.count("{") - text.count("}")


if __name__ == "__main__":
    run()
