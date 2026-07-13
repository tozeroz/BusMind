"""Compatibility wrapper for the default route scoring entrypoints."""

from algorithm.model.register import score_routes, score_routes_typed
from algorithm.model.utils.score_mixing import PREFERENCE_MIX

__all__ = ["PREFERENCE_MIX", "score_routes", "score_routes_typed"]

