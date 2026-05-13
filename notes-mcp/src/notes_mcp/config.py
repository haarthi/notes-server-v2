"""Settings + .categories.yaml loader.

Settings come from env (with `.env` support). `.categories.yaml` is the source
of truth for category names and their `file_unit` patterns. Both are loaded
eagerly at startup so missing/malformed config exits non-zero rather than
producing confusing errors on first tool call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

FileUnit = Literal["topic-based", "monthly-bucket", "entry-based", "mixed"]


class Settings(BaseSettings):
    """Server settings.

    Override via env vars or a local `.env` file. Tests construct directly
    with explicit values.
    """

    notes_home: Path = Field(default_factory=lambda: Path.home() / "Notes")
    host: str = "localhost"
    port: int = 8765
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("notes_home", mode="before")
    @classmethod
    def _expand(cls, v):
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class CategoryConfig(BaseModel):
    """Per-category config inside `.categories.yaml`."""

    file_unit: FileUnit
    # `mixed` uses rules like {"articles": "entry-based", "threads": "topic-based"}.
    rules: dict[str, str] | None = None

    @field_validator("rules")
    @classmethod
    def _validate_rules(cls, v, info):
        if v is None:
            return v
        valid = {"topic-based", "monthly-bucket", "entry-based"}
        for k, rule in v.items():
            if rule not in valid:
                raise ValueError(
                    f"rules['{k}'] = '{rule}' is not one of {sorted(valid)}"
                )
        return v


class CategoriesConfig(BaseModel):
    instance: str
    categories: dict[str, CategoryConfig]


def load_categories(notes_home: Path) -> CategoriesConfig:
    """Load and validate `.categories.yaml` from the notes home directory.

    Raises FileNotFoundError if missing, ValueError if malformed.
    """
    path = notes_home / ".categories.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f".categories.yaml not found at {path} — "
            f"NOTES_HOME may be unset or pointing at the wrong directory"
        )
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f".categories.yaml is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(".categories.yaml must be a YAML mapping at the top level")
    return CategoriesConfig(**raw)
