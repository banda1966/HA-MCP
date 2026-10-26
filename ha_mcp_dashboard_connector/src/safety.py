"""Safety primitives for proposals. No Home Assistant write operation is implemented."""
from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    target: str
    diff: str
    created_at: float
    expires_at: float
    digest: str


class ProposalStore:
    """In-memory proposal store with exact-proposal, expiring, one-use confirmation."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._proposals: Dict[str, Proposal] = {}
        self._confirmed: set[str] = set()

    @staticmethod
    def _digest(target: str, diff: str) -> str:
        return hashlib.sha256((target + "\0" + diff).encode("utf-8")).hexdigest()

    def create(self, target: str, diff: str, now: float | None = None) -> Proposal:
        if not target.strip() or not diff.strip():
            raise ValueError("target and diff must not be empty")
        current = time.time() if now is None else now
        proposal = Proposal(
            proposal_id=secrets.token_urlsafe(18),
            target=target,
            diff=diff,
            created_at=current,
            expires_at=current + self.ttl_seconds,
            digest=self._digest(target, diff),
        )
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def confirm(self, proposal_id: str, target: str, diff: str, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal_id in self._confirmed:
            return False
        if current > proposal.expires_at:
            self._proposals.pop(proposal_id, None)
            return False
        if not secrets.compare_digest(proposal.digest, self._digest(target, diff)):
            return False
        self._confirmed.add(proposal_id)
        return True

    def consume_confirmation(self, proposal_id: str, target: str, diff: str) -> bool:
        """Consume a prior confirmation once; currently only useful for future write paths."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal_id not in self._confirmed:
            return False
        if not secrets.compare_digest(proposal.digest, self._digest(target, diff)):
            return False
        self._confirmed.remove(proposal_id)
        self._proposals.pop(proposal_id, None)
        return True
