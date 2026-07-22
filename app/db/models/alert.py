"""SQLAlchemy model for normalized security alerts."""

import uuid

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
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

    # adding constraints
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
    )

    # adding columns
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

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
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
