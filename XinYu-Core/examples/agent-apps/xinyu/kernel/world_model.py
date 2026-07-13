"""World Model with generative predictions for Cognitive Kernel (K-007).

The World Model is owned by Self and represents its internal generative model of "how the world (and Self in it) works".

Key responsibilities:
- Maintain key facts, causal relations, and expectations (derived from Beliefs + Experiences).
- Generate predictions, including hypothetical or longer-horizon ones.
- Reorganize itself based on significant Prediction Errors (model update / belief revision).
- Provide rich context to Prediction, Attention, Goals, and future layers.

This enables "mental simulation" and long-term consistency.

Design:
- Composed of "WorldFacts" (from beliefs/experiences) and simple generative rules.
- Updates are proposals from high-error or new high-importance data.
- All changes traceable and owned by Self.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field



class WorldFact(BaseModel):
    """A piece of the World Model."""
    fact_id: str
    content: str = Field(min_length=3, max_length=300)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence: list[str] = Field(default_factory=list)  # event_ids or belief_ids
    category: Literal["fact", "causal", "expectation", "self_in_world"] = "fact"
    last_updated: str | None = None


class WorldModel:
    """Generative World Model owned by a Self."""

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.facts: list[WorldFact] = []
        self.pending_review_facts: list[WorldFact] = []  # for owner review gate
        self.generative_rules: list[str] = []  # Simple textual rules for simulation (e.g. "If I break promise, trust drops")

    def add_fact(self, content: str, confidence: float = 0.5, evidence: list[str] | None = None, category: str = "fact", review_status: str = "stable") -> WorldFact:
        fact = WorldFact(
            fact_id=f"fact-{self.self_id[:8]}-{len(self.facts) + len(self.pending_review_facts)}",
            content=content[:300],
            confidence=confidence,
            evidence=evidence or [],
            category=category,  # type: ignore
        )
        if review_status == "review_only":
            self.pending_review_facts.append(fact)
        else:
            self.facts.append(fact)
        return fact

    def generate_prediction(self, context: str = "", horizon: str = "short", max_facts: int = 5) -> dict[str, Any]:
        """Generative prediction.

        Uses current facts + rules to simulate a possible future.
        horizon: "short" | "medium" | "hypothetical"
        """
        relevant = sorted(self.facts, key=lambda f: f.confidence, reverse=True)[:max_facts]
        facts_text = " | ".join(f.content for f in relevant)

        rules_text = " ".join(self.generative_rules[:3]) if self.generative_rules else ""

        prediction = {
            "statement": f"Based on my world model: {facts_text}. {rules_text} {context}. Expected outcome for {horizon} horizon.",
            "confidence": sum(f.confidence for f in relevant) / max(1, len(relevant)),
            "supporting_facts": [f.fact_id for f in relevant],
            "horizon": horizon,
        }
        return prediction

    def generate_hypothetical(self, premise: str, steps: int = 2) -> dict[str, Any]:
        """Strengthened generative: simulate a short chain of implications.

        Applies rules and facts to a premise to produce possible outcomes.
        This makes the World Model more "generative" for mental simulation.
        """
        sims = [premise]
        current = premise
        for i in range(steps):
            matched_rule = None
            for rule in self.generative_rules:
                if any(word in current.lower() for word in rule.lower().split()[:3]):
                    matched_rule = rule
                    break
            if matched_rule:
                next_step = f"If {current[:50]}, then {matched_rule}."
            else:
                # Fall back to high confidence fact
                high_fact = next((f.content for f in sorted(self.facts, key=lambda x: -x.confidence) if f.content.lower() not in current.lower()), "")
                next_step = f"Considering {current[:50]} leads to {high_fact[:60]}."
            sims.append(next_step)
            current = next_step
        return {
            "premise": premise,
            "steps": sims,
            "confidence": 0.6,
            "supporting_rules": self.generative_rules[:2],
        }

    def derive_new_expectation(self, from_belief: str, from_goal: str = "") -> str:
        """Generative: derive a new expectation/fact from belief + goal."""
        base = f"Given {from_belief}"
        if from_goal:
            base += f" and goal to {from_goal}"
        return base + ", I expect interactions to become more predictable over time."

    def learn_rule_from_belief_and_goal(self, belief_content: str, goal_description: str) -> str | None:
        """更完整的 generative simulation: 从信念和目标自动学习/派生规则。"""
        belief_lower = belief_content.lower()
        goal_lower = goal_description.lower()
        if "honesty" in belief_lower or "trust" in belief_lower:
            if "maintain" in goal_lower or "build" in goal_lower:
                rule = "If I break a promise or am dishonest, trust decreases and future interactions require more verification."
                self.add_generative_rule(rule)
                return rule
        if "clarity" in belief_lower or "direct" in belief_lower:
            rule = "Clear direct communication leads to better alignment with goals."
            self.add_generative_rule(rule)
            return rule
        # generic
        if "expect" in belief_lower:
            rule = f"Based on {belief_content[:50]}, I will simulate outcomes before acting on {goal_description[:40]}."
            self.add_generative_rule(rule)
            return rule
        return None

    def simulate_with_beliefs_goals(self, premise: str, active_beliefs: list[str], active_goals: list[str], steps: int = 3) -> list[dict]:
        """加强的 generative simulation: 结合信念和目标驱动的规则学习和模拟。

        Returns structured steps with confidence deltas and affected elements.
        This is the core of K-007 generative capability.
        """
        sim_steps = [{"step": 0, "description": premise, "confidence_delta": 0.0, "affected": []}]
        current = premise
        learned_rules = []
        for i in range(1, steps + 1):
            affected = []
            delta = 0.0
            for b in active_beliefs:
                for g in active_goals:
                    learned = self.learn_rule_from_belief_and_goal(b, g)
                    if learned and learned not in learned_rules:
                        learned_rules.append(learned)
                        self.add_generative_rule(learned)
                        current = f"Applying learned rule from belief+goal: {learned} to {current}"
                        affected.append("learned_rule")
                        delta += 0.05
            for rule in self.generative_rules:
                if any(kw in current.lower() for kw in rule.lower().split()[:4]):
                    current = f"Sim step: {rule} leads to => {current[:40]} evolves to new state"
                    affected.append("rule_applied")
                    delta -= 0.02  # slight uncertainty
                    break
            sim_steps.append({
                "step": i,
                "description": current[:180],
                "confidence_delta": round(delta, 3),
                "affected": affected
            })
        return sim_steps

    def update_from_error(self, error: dict[str, Any], new_facts: list[str] | None = None) -> list[str]:
        """Reorganize model based on Prediction Error.

        Returns list of affected/added fact_ids.
        """
        affected = []
        mag = error.get("error_magnitude", 0)

        if mag > 0.6:
            # Revise expectations
            for fact in self.facts:
                if any(imp in fact.content.lower() for imp in error.get("impact_on_self", [])):
                    fact.confidence = max(0.3, fact.confidence - 0.2)
                    fact.last_updated = error.get("source_event_id")
                    affected.append(fact.fact_id)

        if new_facts:
            for content in new_facts:
                review = "review_only" if error.get("error_magnitude", 0) > 0.75 else "stable"
                f = self.add_fact(content, confidence=0.7, evidence=[error.get("source_event_id", "")], category="expectation", review_status=review)
                affected.append(f.fact_id)

        return affected

    def sync_with_self_state(self, self_model: dict, active_beliefs: list[dict], active_goals: list[dict]):
        """补细节: 从 Self 当前状态同步 World Model。
        提取核心信念和目标作为 facts/rules。
        """
        # Sync core statements as self_in_world facts
        for stmt in self_model.get("core_statements", []):
            content = stmt.get("content", "")
            if content and not any(f.content == content for f in self.facts):
                self.add_fact(content, confidence=stmt.get("confidence", 0.6), category="self_in_world")

        # Derive rules from high confidence beliefs
        for b in active_beliefs:
            if b.get("confidence", 0) > 0.7:
                for g in active_goals:
                    if g.get("status") == "active":
                        self.learn_rule_from_belief_and_goal(b.get("content", ""), g.get("description", ""))

    def reorganize(self, errors: list[dict], new_beliefs: list[dict] = None, new_goals: list[dict] = None) -> dict[str, Any]:
        """补细节: 更完整的重组方法。
        整合多个 error、belief、goal 来更新 WM。
        返回变更摘要。
        """
        affected = []
        for err in errors:
            aff = self.update_from_error(err)
            affected.extend(aff)

        if new_beliefs:
            for b in new_beliefs:
                if b.get("confidence", 0) > 0.65:
                    self.add_fact(b.get("content", ""), confidence=b.get("confidence"), evidence=b.get("evidence_event_ids", []), category="fact")

        # Re-learn rules
        if new_goals:
            for g in new_goals:
                for b in (new_beliefs or []):
                    learned = self.learn_rule_from_belief_and_goal(b.get("content", ""), g.get("description", ""))
                    if learned:
                        affected.append("new_rule")

        return {
            "affected": list(set(affected)),
            "total_facts": len(self.facts),
            "total_rules": len(self.generative_rules)
        }

    def add_generative_rule(self, rule: str) -> None:
        if rule not in self.generative_rules:
            self.generative_rules.append(rule[:200])

    def apply_reviewed_fact(self, fact_id: str) -> bool:
        """Owner review gate action: move from pending to active facts."""
        for i, f in enumerate(self.pending_review_facts):
            if f.fact_id == fact_id:
                self.facts.append(self.pending_review_facts.pop(i))
                return True
        return False

    def get_pending_review_facts(self) -> list[WorldFact]:
        return list(self.pending_review_facts)

    def get_context(self, max_items: int = 4) -> str:
        """Compact world model summary for other layers."""
        top = sorted(self.facts, key=lambda f: f.confidence, reverse=True)[:max_items]
        rules = " Rules: " + " ".join(self.generative_rules[:2]) if self.generative_rules else ""
        return "World: " + " | ".join(f.content for f in top) + rules

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "facts": [f.model_dump() for f in self.facts],
            "pending_review_facts": [f.model_dump() for f in self.pending_review_facts],
            "generative_rules": self.generative_rules,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldModel":
        wm = cls(self_id=data.get("self_id"))
        for f in data.get("facts", []):
            wm.facts.append(WorldFact.model_validate(f))
        for f in data.get("pending_review_facts", []):
            wm.pending_review_facts.append(WorldFact.model_validate(f))
        wm.generative_rules = data.get("generative_rules", [])
        return wm
