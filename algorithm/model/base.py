"""Shared interface for candidate route scoring models."""

from __future__ import annotations

from typing import Protocol

from algorithm.model.contracts import ModelScoringRequest, ScoreResult


class RouteScoringModel(Protocol):
    """Common contract implemented by all route scoring backends."""

    model_key: str
    model_name: str
    model_version: str

    def score_route(self, route, *, preference: str) -> ScoreResult:
        """Score one preprocessed route."""

    def score_routes_typed(self, request: ModelScoringRequest) -> dict:
        """Score a validated model request."""

