from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import Batch, Rider, RiderStatus, Shelter, ShelterStatus
from .safety_engine import LastSafeDecisionClock, SafetyEngine, SafetyEvaluationReport


@dataclass(frozen=True)
class CandidateAssignment:
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int
    travel_minutes: int
    handoff_minutes: int
    feasible: bool
    evaluation: SafetyEvaluationReport
    safety_clock: LastSafeDecisionClock
    score: float = 0.0
    rank: int = 0
    ranking_explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "rider_id": self.rider_id,
            "shelter_id": self.shelter_id,
            "quantity": self.quantity,
            "travel_minutes": self.travel_minutes,
            "handoff_minutes": self.handoff_minutes,
            "feasible": self.feasible,
            "score": round(self.score, 2),
            "rank": self.rank,
            "ranking_explanation": self.ranking_explanation,
            "evaluation": self.evaluation.to_dict(),
            "safety_clock": self.safety_clock.to_dict(),
        }


@dataclass(frozen=True)
class BatchSplitPlan:
    """A feasible multi-rider allocation plan for oversized batches."""

    batch_id: str
    total_batch_quantity: int
    allocated_quantity: int
    remaining_unallocated: int
    assignments: list[CandidateAssignment]
    is_fully_allocated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_batch_quantity": self.total_batch_quantity,
            "allocated_quantity": self.allocated_quantity,
            "remaining_unallocated": self.remaining_unallocated,
            "is_fully_allocated": self.is_fully_allocated,
            "assignments": [a.to_dict() for a in self.assignments],
        }


@dataclass(frozen=True)
class CandidateGenerationResult:
    batch_id: str
    feasible_candidates: list[CandidateAssignment]
    rejected_candidates: list[CandidateAssignment]
    split_plan: BatchSplitPlan | None
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "feasible_count": len(self.feasible_candidates),
            "rejected_count": len(self.rejected_candidates),
            "feasible_candidates": [c.to_dict() for c in self.feasible_candidates],
            "rejected_candidates": [c.to_dict() for c in self.rejected_candidates],
            "split_plan": self.split_plan.to_dict() if self.split_plan else None,
            "generated_at": self.generated_at.isoformat(),
        }


class CandidateEngine:
    """Discovers feasible candidate deliveries, splits oversized batches across multiple riders,
    and produces deterministic, explainable rankings."""

    @classmethod
    def generate_and_rank_candidates(
        cls,
        batch: Batch,
        riders: list[Rider],
        shelters: list[Shelter],
        now: datetime,
        default_travel_minutes: int = 25,
        default_handoff_minutes: int = 10,
    ) -> CandidateGenerationResult:
        feasible: list[CandidateAssignment] = []
        rejected: list[CandidateAssignment] = []

        # 1. Evaluate single assignments
        for rider in riders:
            for shelter in shelters:
                # Feasible assignment quantity is bounded by batch availability, rider capacity, and shelter demand
                max_possible = min(
                    batch.available_quantity,
                    rider.remaining_capacity,
                    shelter.demand_remaining,
                    shelter.receiving_capacity_remaining,
                )
                alloc_qty = max(1, max_possible)

                report = SafetyEngine.evaluate_feasibility(
                    batch=batch,
                    rider=rider,
                    shelter=shelter,
                    quantity=alloc_qty,
                    travel_minutes=default_travel_minutes,
                    handoff_minutes=default_handoff_minutes,
                    now=now,
                )

                clock = SafetyEngine.calculate_last_safe_decision(
                    batch=batch,
                    shelter_id=shelter.id,
                    travel_minutes=default_travel_minutes,
                    handoff_minutes=default_handoff_minutes,
                    now=now,
                )

                candidate = CandidateAssignment(
                    batch_id=batch.id,
                    rider_id=rider.id,
                    shelter_id=shelter.id,
                    quantity=alloc_qty,
                    travel_minutes=default_travel_minutes,
                    handoff_minutes=default_handoff_minutes,
                    feasible=report.feasible,
                    evaluation=report,
                    safety_clock=clock,
                )

                if report.feasible and clock.is_feasible:
                    feasible.append(candidate)
                else:
                    rejected.append(candidate)

        # 2. Score and rank feasible candidates
        ranked_feasible = cls._rank_candidates(feasible)

        # 3. Generate multi-rider batch split plan if batch exceeds single rider capacity
        split_plan = cls._generate_batch_split_plan(
            batch=batch,
            riders=riders,
            shelters=shelters,
            now=now,
            default_travel_minutes=default_travel_minutes,
            default_handoff_minutes=default_handoff_minutes,
        )

        return CandidateGenerationResult(
            batch_id=batch.id,
            feasible_candidates=ranked_feasible,
            rejected_candidates=rejected,
            split_plan=split_plan,
            generated_at=now,
        )

    @classmethod
    def _rank_candidates(cls, candidates: list[CandidateAssignment]) -> list[CandidateAssignment]:
        """Rank feasible candidates deterministically and assign human-readable explanations."""
        scored: list[tuple[float, CandidateAssignment]] = []

        for c in candidates:
            # Score factors:
            # + More quantity delivered = higher utility (+1.0 per unit)
            # + More safe window remaining = lower urgency stress (+0.5 per minute)
            # - More travel time = higher cost (-1.5 per minute)
            score = (
                (c.quantity * 2.0)
                + (c.safety_clock.remaining_decision_window_minutes * 0.5)
                - (c.travel_minutes * 1.5)
            )
            scored.append((score, c))

        # Sort descending by score, deterministic tie-break by (quantity desc, travel_minutes asc, rider_id asc)
        scored.sort(key=lambda item: (-item[0], -item[1].quantity, item[1].travel_minutes, item[1].rider_id))

        ranked: list[CandidateAssignment] = []
        for i, (score, c) in enumerate(scored, 1):
            if i == 1:
                explanation = (
                    f"Top recommendation: delivers {c.quantity} units to {c.shelter_id} in {c.travel_minutes}m "
                    f"with {round(c.safety_clock.remaining_decision_window_minutes)}m decision safety margin."
                )
            else:
                top_c = scored[0][1]
                diff_units = top_c.quantity - c.quantity
                diff_time = c.travel_minutes - top_c.travel_minutes
                explanation = f"Ranked #{i}: delivers {c.quantity} units ({'+' if diff_units < 0 else '-'}{abs(diff_units)} vs #1)."
                if diff_time > 0:
                    explanation += f" Takes {diff_time}m longer in transit."

            ranked.append(
                CandidateAssignment(
                    batch_id=c.batch_id,
                    rider_id=c.rider_id,
                    shelter_id=c.shelter_id,
                    quantity=c.quantity,
                    travel_minutes=c.travel_minutes,
                    handoff_minutes=c.handoff_minutes,
                    feasible=c.feasible,
                    evaluation=c.evaluation,
                    safety_clock=c.safety_clock,
                    score=score,
                    rank=i,
                    ranking_explanation=explanation,
                )
            )
        return ranked

    @classmethod
    def _generate_batch_split_plan(
        cls,
        batch: Batch,
        riders: list[Rider],
        shelters: list[Shelter],
        now: datetime,
        default_travel_minutes: int,
        default_handoff_minutes: int,
    ) -> BatchSplitPlan | None:
        """Solves Chaos Lab Scenario A: Splitting an oversized donation across multiple available riders."""
        available_riders = [
            r for r in riders
            if r.available and r.status in (RiderStatus.AVAILABLE, "AVAILABLE") and r.remaining_capacity > 0
        ]
        open_shelters = [
            s for s in shelters
            if s.open and s.status in (ShelterStatus.OPEN, "OPEN") and s.demand_remaining > 0
        ]

        if not available_riders or not open_shelters:
            return None

        # Sort riders by capacity descending (greedy packing)
        available_riders.sort(key=lambda r: r.remaining_capacity, reverse=True)
        # Sort shelters by demand remaining descending
        open_shelters.sort(key=lambda s: s.demand_remaining, reverse=True)

        remaining_batch = batch.available_quantity
        assignments: list[CandidateAssignment] = []

        shelter_idx = 0
        for rider in available_riders:
            if remaining_batch <= 0:
                break
            if shelter_idx >= len(open_shelters):
                break

            target_shelter = open_shelters[shelter_idx]
            alloc_qty = min(remaining_batch, rider.remaining_capacity, target_shelter.demand_remaining)

            if alloc_qty <= 0:
                shelter_idx += 1
                continue

            report = SafetyEngine.evaluate_feasibility(
                batch=batch,
                rider=rider,
                shelter=target_shelter,
                quantity=alloc_qty,
                travel_minutes=default_travel_minutes,
                handoff_minutes=default_handoff_minutes,
                now=now,
            )

            clock = SafetyEngine.calculate_last_safe_decision(
                batch=batch,
                shelter_id=target_shelter.id,
                travel_minutes=default_travel_minutes,
                handoff_minutes=default_handoff_minutes,
                now=now,
            )

            if report.feasible and clock.is_feasible:
                assignments.append(
                    CandidateAssignment(
                        batch_id=batch.id,
                        rider_id=rider.id,
                        shelter_id=target_shelter.id,
                        quantity=alloc_qty,
                        travel_minutes=default_travel_minutes,
                        handoff_minutes=default_handoff_minutes,
                        feasible=True,
                        evaluation=report,
                        safety_clock=clock,
                        ranking_explanation=f"Batch split segment: {alloc_qty} units assigned to {rider.id}",
                    )
                )
                remaining_batch -= alloc_qty

        allocated = batch.available_quantity - remaining_batch
        return BatchSplitPlan(
            batch_id=batch.id,
            total_batch_quantity=batch.available_quantity,
            allocated_quantity=allocated,
            remaining_unallocated=remaining_batch,
            assignments=assignments,
            is_fully_allocated=(remaining_batch == 0),
        )
