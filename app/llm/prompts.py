"""
Prompt loading utilities.

Loads prompt text from the prompts/ directory via the config helper.
"""

from app.core.config import settings


def planner_system_prompt() -> str:
    return settings.get_prompt("planner_system.txt")


def responder_system_prompt() -> str:
    return settings.get_prompt("responder_system.txt")


def safety_rules_text() -> str:
    return settings.get_prompt("safety_rules.txt")


def evaluation_prompt() -> str:
    return settings.get_prompt("evaluation_prompt.txt")
