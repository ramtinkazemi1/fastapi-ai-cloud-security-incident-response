"""SQLAlchemy model for normalized security alerts."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    """Persisted vendor-neutral security alert."""

    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Database constraints defend invariants for every write path.
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_alert_source_external_id",
        ),
        CheckConstraint(
            "severity >= 0 AND severity <= 10",
            name="ck_alert_severity_range",
        ),
        CheckConstraint(
            "status IN ('new', 'investigating', 'resolved', 'dismissed')",
            name="ck_alert_status",
        ),
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    severity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="new",
        index=True,
    )
    account_id: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
    )
    region: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    resource: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    recommended_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
