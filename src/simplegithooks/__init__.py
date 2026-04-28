from importlib.metadata import PackageNotFoundError, version

from .colors import (
    bg_green,
    bg_red,
    bg_yellow,
    blink,
    fg_black,
    fg_blue,
    fg_cyan,
    fg_green,
    fg_magenta,
    fg_red,
    fg_reset,
    fg_white,
    fg_yellow,
    reset,
)
from .git_hooks import GitHook, PreCommitConfig, PrePushConfig

__title__ = "simplegithooks"

try:
    __version__ = version(__title__)
except PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "Kamil Cyganowski"
__license__ = "MIT"
__copyright__ = "Copyright 2026 Kamil Cyganowski"
__all__ = [
    "GitHook",
    "PreCommitConfig",
    "PrePushConfig",
    "bg_green",
    "bg_red",
    "bg_yellow",
    "blink",
    "fg_black",
    "fg_blue",
    "fg_cyan",
    "fg_green",
    "fg_magenta",
    "fg_red",
    "fg_reset",
    "fg_white",
    "fg_yellow",
    "reset",
]
