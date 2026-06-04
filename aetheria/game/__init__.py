"""The playable command-line client for Aetheria."""

from .factory import create_player
from .cli import Game

__all__ = ["Game", "create_player"]
