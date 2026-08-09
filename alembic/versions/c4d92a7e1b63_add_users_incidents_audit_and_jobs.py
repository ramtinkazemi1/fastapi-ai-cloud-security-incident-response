"""Add users, incidents, audit events, and analysis jobs.

Revision ID: c4d92a7e1b63
Revises: 8f3b1c9a2d40
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d92a7e1b63"
down_revision: str | None = "8f3b1c9a2d40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the small analyst and incident-response workflow."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="analyst",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('analyst', 'admin')",
            name="ck_user_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity >= 0 AND severity <= 10",
            name="ck_incident_severity_range",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'contained', 'closed')",
            name="ck_incident_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_incidents_status",
        "incidents",
        ["status"],
        unique=False,
    )

    op.add_column(
        "alerts",
        sa.Column("incident_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_alerts_incident_id_incidents",
        "alerts",
        "incidents",
        ["incident_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_alerts_incident_id",
        "alerts",
        ["incident_id"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_created_at",
        "audit_events",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_analysis_job_status",
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_jobs_alert_id",
        "analysis_jobs",
        ["alert_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the analyst and incident-response workflow."""
    op.drop_index("ix_analysis_jobs_alert_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_alerts_incident_id", table_name="alerts")
    op.drop_constraint(
        "fk_alerts_incident_id_incidents",
        "alerts",
        type_="foreignkey",
    )
    op.drop_column("alerts", "incident_id")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
