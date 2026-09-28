"""Scaling-mana registry (v4.76.0, WP1) -- see registry.py / definitions.json."""
from .registry import (  # noqa: F401
    DEFINITIONS, match_card, reload, resolve_mana_options, text_without_scaling_lines,
)
from . import handlers  # noqa: F401  (registers the handlers)
