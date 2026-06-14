from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import cast

from src.domain.enums import FormalLifecycleState, ProposalLifecycleState


class DomainLifecycleTransitionError(ValueError):
    pass


class LifecycleTransitionValidator:
    def __init__(self) -> None:
        self._formal_transitions: dict[FormalLifecycleState, frozenset[FormalLifecycleState]] = {
            FormalLifecycleState.draft: frozenset({FormalLifecycleState.in_review, FormalLifecycleState.rejected}),
            FormalLifecycleState.in_review: frozenset(
                {FormalLifecycleState.approved, FormalLifecycleState.rejected, FormalLifecycleState.draft}
            ),
            FormalLifecycleState.approved: frozenset(
                {FormalLifecycleState.published, FormalLifecycleState.archived, FormalLifecycleState.rejected}
            ),
            FormalLifecycleState.published: frozenset(
                {FormalLifecycleState.superseded, FormalLifecycleState.archived}
            ),
            FormalLifecycleState.superseded: frozenset({FormalLifecycleState.archived}),
            FormalLifecycleState.archived: frozenset(),
            FormalLifecycleState.rejected: frozenset(),
        }
        self._proposal_transitions: dict[ProposalLifecycleState, frozenset[ProposalLifecycleState]] = {
            ProposalLifecycleState.draft: frozenset(
                {ProposalLifecycleState.in_review, ProposalLifecycleState.rejected}
            ),
            ProposalLifecycleState.in_review: frozenset(
                {ProposalLifecycleState.accepted, ProposalLifecycleState.rejected, ProposalLifecycleState.draft}
            ),
            ProposalLifecycleState.accepted: frozenset(
                {ProposalLifecycleState.archived, ProposalLifecycleState.superseded}
            ),
            ProposalLifecycleState.rejected: frozenset({ProposalLifecycleState.archived}),
            ProposalLifecycleState.archived: frozenset(),
            ProposalLifecycleState.superseded: frozenset({ProposalLifecycleState.archived}),
        }

    def _mapping_for(self, state: Enum) -> Mapping[Enum, frozenset[Enum]]:
        if isinstance(state, FormalLifecycleState):
            return cast(Mapping[Enum, frozenset[Enum]], self._formal_transitions)
        if isinstance(state, ProposalLifecycleState):
            return cast(Mapping[Enum, frozenset[Enum]], self._proposal_transitions)
        raise DomainLifecycleTransitionError(f"unsupported lifecycle enum: {type(state).__name__}")

    def can_transition(self, from_state: Enum, to_state: Enum) -> bool:
        transitions = self._mapping_for(from_state)
        return to_state in transitions[from_state]

    def validate(self, from_state: Enum, to_state: Enum) -> None:
        if not self.can_transition(from_state, to_state):
            raise DomainLifecycleTransitionError(f"invalid lifecycle transition: {from_state} -> {to_state}")

    def validate_proposal_acceptance_target(self, target_state: FormalLifecycleState) -> None:
        if target_state is not FormalLifecycleState.draft:
            raise DomainLifecycleTransitionError(
                f"accepted proposals may create draft versions only, got {target_state}"
            )
