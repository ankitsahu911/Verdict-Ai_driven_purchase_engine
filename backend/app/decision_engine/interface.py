"""
Shared Decision Axis Scorer Protocol Interface (MILESTONE 19).

Defines the Python Protocol interface that every decision axis scorer module
must implement.
"""

from typing import Protocol, runtime_checkable
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore


@runtime_checkable
class AxisScorer(Protocol):
    """Protocol interface that every decision axis scorer must implement."""

    def score(self, candidate_item_id: int, db: Session) -> AxisScore:
        """Evaluate and return the normalized AxisScore for a candidate wardrobe item.

        Args:
            candidate_item_id: Database primary key of the candidate WardrobeItem.
            db: Active SQLAlchemy database session.

        Returns:
            AxisScore instance with normalized score (0-100), plain-English reason,
            source agent identifier, and raw supporting evidence.
        """
        ...
