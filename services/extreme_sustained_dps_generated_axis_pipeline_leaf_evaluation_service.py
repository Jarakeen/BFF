from __future__ import annotations

"""Exact-leaf bridge from the generated axis pipeline to canonical runtime evaluation."""

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierNode,
)
from services.extreme_sustained_dps_generated_search_evidence_adapter_service import (
    ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService,
)


class ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService:
    """Extract the final assembled witness and run canonical exact simulation.

    Final build/progression come from the assembled late-stage candidate so Champion
    Point, potion selection, passive-rank, and skill-bar mutations reach simulation.
    When a finalized-potion stage exists its exact plan supersedes the runtime-policy
    plan; otherwise the runtime-policy candidate remains the final plan.
    """

    def __init__(self, *, runtime_evaluation: object) -> None:
        self.runtime_evaluation = runtime_evaluation

    @staticmethod
    def _incomplete(
        node: ExtremeSustainedDPSGeneratedFrontierNode,
        message: str,
    ) -> ExtremeSustainedDPSExactLeafEvaluation:
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=None,
            duration_seconds=None,
            mechanic_complete=False,
            evidence=tuple(node.evidence),
            unresolved=(str(message),),
        )

    def evaluate(
        self,
        node: ExtremeSustainedDPSGeneratedFrontierNode,
        *,
        runtime_snapshot: object,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
    ) -> ExtremeSustainedDPSExactLeafEvaluation:
        if not isinstance(node, ExtremeSustainedDPSGeneratedFrontierNode):
            raise TypeError("generated leaf evaluation requires canonical frontier node")
        state = node.state
        runtime_choice = getattr(state, "runtime_state_choice", None)
        complete = getattr(state, "complete", False)
        if not isinstance(complete, bool):
            raise TypeError("generated leaf complete flag must be boolean")
        if not complete:
            return self._incomplete(
                node,
                "Generated axis pipeline leaf is incomplete",
            )

        gear = getattr(state, "gear", None)
        late = getattr(state, "late", None)
        runtime = getattr(state, "runtime", None)
        finalized_potion = getattr(state, "finalized_potion", None)
        assembled = getattr(late, "assembled", None)
        runtime_policy_candidate = getattr(runtime, "current_candidate", None)
        finalized_potion_candidate = getattr(finalized_potion, "candidate", None)
        final_policy_candidate = (
            finalized_potion_candidate
            if finalized_potion_candidate is not None
            else runtime_policy_candidate
        )

        build = getattr(assembled, "build", None)
        progression = getattr(assembled, "progression", None)
        gear_state = getattr(gear, "gear_state", None)
        plan = getattr(final_policy_candidate, "plan", None)

        missing = tuple(
            label
            for label, value in (
                ("assembled build", build),
                ("generated progression", progression),
                ("dual-bar gear state", gear_state),
                ("final generated plan", plan),
            )
            if value is None
        )
        if missing:
            return self._incomplete(
                node,
                "Generated axis pipeline leaf is missing " + ", ".join(missing),
            )

        if runtime_choice is not None and getattr(runtime_choice, "unresolved", ()):
            return self._incomplete(
                node,
                "Generated runtime-state choice is unresolved: "
                + "; ".join(str(item) for item in runtime_choice.unresolved),
            )

        effective_runtime_snapshot = (
            getattr(runtime_choice, "snapshot")
            if runtime_choice is not None
            else runtime_snapshot
        )
        runtime_choice_evidence = ()
        if runtime_choice is not None:
            runtime_choice_evidence = getattr(runtime_choice, "evidence", ())
            if not isinstance(runtime_choice_evidence, tuple):
                raise TypeError("runtime-state choice evidence must be a tuple")

        runtime_kwargs = {
            "progression": progression,
            "gear_state": gear_state,
            "plan": plan,
            "runtime_snapshot": effective_runtime_snapshot,
            "target_health": target_health,
            "target_resistance": target_resistance,
            "target_name": target_name,
            "initial_bar": initial_bar,
        }
        if runtime_choice is not None:
            runtime_kwargs["runtime_effects"] = tuple(
                getattr(runtime_choice, "effects", ())
            )

        if isinstance(target_health, bool) or not isinstance(target_health, int):
            raise TypeError("generated leaf target health must be an integer")
        if isinstance(target_resistance, bool) or not isinstance(target_resistance, (int, float)):
            raise TypeError("generated leaf target resistance must be numeric")
        result = self.runtime_evaluation.evaluate(
            build,
            **runtime_kwargs,
        )
        exact = ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService.exact_leaf(
            node.candidate_key,
            result,
        )
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=exact.candidate_key,
            modeled_dps=exact.modeled_dps,
            duration_seconds=exact.duration_seconds,
            mechanic_complete=exact.mechanic_complete,
            evidence=tuple(
                (*node.evidence, *runtime_choice_evidence, *exact.evidence)
            ),
            unresolved=tuple(exact.unresolved),
            relevance=getattr(state, "relevance", None),
            scaling=getattr(state, "scaling", None),
        )

    def evaluator(
        self,
        *,
        runtime_snapshot: object,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
    ):
        def evaluate(
            node: ExtremeSustainedDPSGeneratedFrontierNode,
        ) -> ExtremeSustainedDPSExactLeafEvaluation:
            return self.evaluate(
                node,
                runtime_snapshot=runtime_snapshot,
                target_health=target_health,
                target_resistance=target_resistance,
                target_name=target_name,
                initial_bar=initial_bar,
            )

        return evaluate


__all__ = [
    "ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService",
]
