"""Localization loader.

The UI strings used to live in a single 1174-line Python dict. They now
live as per-language JSON files under ``amr_ui/locales/``. This module
loads all of them once at import time and exposes the same ``TEXT`` dict
that the rest of the codebase expects, so every caller that does
``TEXT[st.session_state.language]`` keeps working unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_LOCALES_DIR = Path(__file__).parent.parent / "locales"

# Display name (used as the session-state language key) -> locale filename stem.
_LANGUAGE_FILES = {
    "繁體中文": "zh_TW",
    "日本語": "ja",
    "한국어": "ko",
    "English": "en",
}


def _load_locale(code: str) -> dict:
    path = _LOCALES_DIR / f"{code}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


TEXT: Dict[str, dict] = {
    display_name: _load_locale(code) for display_name, code in _LANGUAGE_FILES.items()
}
