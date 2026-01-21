from pathlib import Path

from src.llm.prompt_loader import PromptLoader


def test_prompt_loader_reads_files():
    loader = PromptLoader(base_dir=Path("prompts"))
    system_prompt = loader.load("interpret.system.md")
    user_prompt = loader.load("interpret.user.md")

    assert "DraftCommand" in system_prompt
    assert "Останній запит" in user_prompt
