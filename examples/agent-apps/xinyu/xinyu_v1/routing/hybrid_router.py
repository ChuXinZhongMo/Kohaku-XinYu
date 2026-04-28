"""Fast/Slow route selection."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..gateway.models import InboundTurn
from ..types import RouteConfidence, RouteName
from .classifier import TurnClassification, TurnClassifier
from .policy import RoutingPolicy
from .risk import RiskScore, score_turn_risk


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: RouteName
    confidence: RouteConfidence
    classification: TurnClassification
    risk: RiskScore
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_fast_path(self) -> bool:
        return self.route is RouteName.FAST_PATH

    @property
    def is_slow_path(self) -> bool:
        return self.route is RouteName.SLOW_PATH


class HybridRouter:
    def __init__(self, classifier: TurnClassifier | None = None, policy: RoutingPolicy | None = None) -> None:
        self._classifier = classifier or TurnClassifier()
        self._policy = policy or RoutingPolicy()

    def decide(self, turn: InboundTurn) -> RouteDecision:
        classification = self._classifier.classify(turn)
        risk = score_turn_risk(turn, classification)
        reasons = [f"hint:{classification.route_hint.value}", f"risk:{risk.score:.2f}", *risk.reasons]

        if classification.route_hint is RouteName.MAINTENANCE:
            return RouteDecision(RouteName.MAINTENANCE, RouteConfidence.HIGH, classification, risk, tuple(reasons))
        if classification.route_hint is RouteName.BLOCKED:
            return RouteDecision(RouteName.BLOCKED, RouteConfidence.HIGH, classification, risk, tuple(reasons))
        if classification.route_hint is RouteName.SLOW_PATH:
            return RouteDecision(RouteName.SLOW_PATH, RouteConfidence.HIGH, classification, risk, tuple(reasons))
        if risk.score >= self._policy.slow_path_min_risk:
            return RouteDecision(RouteName.SLOW_PATH, RouteConfidence.MEDIUM, classification, risk, tuple(reasons))
        if classification.salience <= self._policy.fast_path_max_salience and not classification.needs_model:
            return RouteDecision(RouteName.FAST_PATH, RouteConfidence.HIGH, classification, risk, tuple(reasons))
        return RouteDecision(RouteName.SLOW_PATH, RouteConfidence.MEDIUM, classification, risk, tuple(reasons))

