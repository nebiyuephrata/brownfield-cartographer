from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass, make_dataclass
from typing import Any


def Field(default=None, default_factory=None):
    if default_factory is not None:
        return field(default_factory=default_factory)
    return field(default=default)


class BaseModel:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Convert subclass annotations into dataclass fields automatically.
        if not is_dataclass(cls):
            dataclass(cls)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_validate(cls, data: dict[str, Any]):
        return cls(**data)
