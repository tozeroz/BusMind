from __future__ import annotations

import importlib
import inspect
from typing import Any, Callable


class OptionalPredictor:
    """Loads a data-engineer predictor lazily without coupling module ownership."""

    def __init__(self, dotted_path: str) -> None:
        self.dotted_path = dotted_path
        self._resolved = False
        self._callable: Callable[..., Any] | None = None

    def _resolve(self) -> Callable[..., Any] | None:
        if self._resolved:
            return self._callable
        self._resolved = True
        try:
            module_path, function_name = self.dotted_path.split(":", 1)
            module = importlib.import_module(module_path)
            candidate = getattr(module, function_name)
            if callable(candidate):
                self._callable = candidate
        except (ImportError, AttributeError, ValueError):
            self._callable = None
        return self._callable

    async def predict(self, features: dict[str, Any]) -> Any | None:
        predictor = self._resolve()
        if predictor is None:
            return None
        try:
            result = predictor(features)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception:
            # The rule-based service remains available when a model artifact is
            # missing, incompatible or temporarily fails.
            return None
