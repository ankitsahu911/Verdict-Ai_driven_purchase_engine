from typing import Protocol, runtime_checkable
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore


@runtime_checkable
class AxisScorer(Protocol):
    def score(self, candidate_item_id: int, db: Session) -> AxisScore:
        ...
