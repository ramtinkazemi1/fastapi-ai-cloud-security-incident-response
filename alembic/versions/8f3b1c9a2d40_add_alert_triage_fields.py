"""Add alert workflow and AI triage fields.

Revision ID: 8f3b1c9a2d40
Revises: 2877413763ff
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f3b1c9a2d40"
down_revision: str | None = "2877413763ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add investigation context and persisted AI output."""
    op.add_column(
        "alerts",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="new",
            nullable=False,
        ),
    )
    op.add_column(
        "alerts",
        sa.Column("account_id", sa.String(length=12), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("region", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("resource", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("ai_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("recommended_action", sa.Text(), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_alert_status",
        "alerts",
        "status IN ('new', 'investigating', 'resolved', 'dismissed')",
    )
    op.create_index(
        op.f("ix_alerts_status"),
        "alerts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove investigation context and persisted AI output."""
    op.drop_index(op.f("ix_alerts_status"), table_name="alerts")
    op.drop_constraint(
        "ck_alert_status",
        "alerts",
        type_="check",
    )
    op.drop_column("alerts", "analyzed_at")
    op.drop_column("alerts", "recommended_action")
    op.drop_column("alerts", "ai_summary")
    op.drop_column("alerts", "resource")
    op.drop_column("alerts", "region")
    op.drop_column("alerts", "account_id")
    op.drop_column("alerts", "status")
