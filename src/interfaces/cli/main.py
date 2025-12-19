"""Command-line interface stub."""

from __future__ import annotations

import logging

from ...infra import load_config


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
            print(user_input)
    except KeyboardInterrupt:
        logging.info("CLI interrupted by user.")


if __name__ == "__main__":
    run()
