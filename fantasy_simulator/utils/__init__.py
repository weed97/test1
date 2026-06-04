"""Fantasy simulator utilities."""

from utils.dice import roll, roll_d20
from utils.io_helpers import load_json, save_json, load_text
from utils.llm_client import LLMClient, call_claude, call_codex, call_gpt
from utils.llm_router import decide_model_and_prompt, route_action, route_consistency_check, describe_routes
from utils.state_loader import StateLoader
from utils.state_manager import StateManager
from utils.state_store import StateStore

__all__ = [
    "roll",
    "roll_d20",
    "load_json",
    "save_json",
    "load_text",
    "StateLoader",
    "StateStore",
    "StateManager",
    "LLMClient",
    "call_claude",
    "call_codex",
    "call_gpt",
    "route_action",
    "decide_model_and_prompt",
    "route_consistency_check",
    "describe_routes",
]
