"""Fantasy simulator utilities."""

from utils.dice import roll, roll_d20
from utils.io_helpers import load_json, save_json, load_text
from utils.state_loader import StateLoader
from utils.state_store import StateStore
from utils.prompt_router import PromptRouter
from utils.structured_output import StructuredOutputClient, StructuredOutputError, extract_json_object

__all__ = [
    "roll",
    "roll_d20",
    "load_json",
    "save_json",
    "load_text",
    "StateLoader",
    "StateStore",
    "PromptRouter",
    "StructuredOutputClient",
    "StructuredOutputError",
    "extract_json_object",
]
