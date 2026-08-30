import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class ExtractionSource(str, enum.Enum):
    AI = "ai"
    MANUAL_OVERRIDE = "manual_override"


class Decision(str, enum.Enum):
    BUY = "buy"
    SKIP = "skip"
    CONSIDER = "consider"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    wardrobe_items: Mapped[list["WardrobeItem"]] = relationship(
        back_populates="user"
    )
    decision_logs: Mapped[list["DecisionLog"]] = relationship(
        back_populates="user"
    )


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    cloudinary_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    cloudinary_public_id: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    is_candidate: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    tryon_render_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    fit_tightness: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    silhouette: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    duplicate_match_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("wardrobe_items.id"), nullable=True
    )
    duplicate_similarity_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="wardrobe_items")
    attributes: Mapped["GarmentAttributes | None"] = relationship(
        back_populates="wardrobe_item",
        uselist=False,
        cascade="all, delete-orphan",
    )
    decision_logs: Mapped[list["DecisionLog"]] = relationship(
        back_populates="wardrobe_item"
    )


class GarmentAttributes(Base):
    __tablename__ = "garment_attributes"
    __table_args__ = (
        UniqueConstraint("wardrobe_item_id", name="uq_garment_attributes_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wardrobe_item_id: Mapped[int] = mapped_column(
        ForeignKey("wardrobe_items.id"), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    season: Mapped[str | None] = mapped_column(String(100), nullable=True)
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extraction_source: Mapped[ExtractionSource | None] = mapped_column(
        Enum(
            ExtractionSource,
            name="extraction_source_enum",
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    wardrobe_item: Mapped[WardrobeItem] = relationship(
        back_populates="attributes"
    )


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    wardrobe_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("wardrobe_items.id"), nullable=True
    )
    decision: Mapped[Decision | None] = mapped_column(
        Enum(Decision, name="decision_enum", values_callable=_enum_values),
        nullable=True,
    )
    buy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="decision_logs")
    wardrobe_item: Mapped[WardrobeItem | None] = relationship(
        back_populates="decision_logs"
    )
