"""Meeting recordings, transcripts and confirmed protocols."""

import sqlalchemy as sa

from alembic import op

revision = "20260923_protokol_domain"
down_revision = "e0ab44d8ac4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("audio_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("duration_s", sa.Float()),
        sa.Column("language_hint", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "meeting_speakers",
        sa.Column("meeting_id", sa.String(64), sa.ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("speaker_id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
    )
    op.create_table(
        "meeting_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meeting_id", sa.String(64), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("speaker_id", sa.String(64), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("words", sa.JSON(), nullable=False),
    )
    op.create_index("ix_meeting_segments_meeting_idx", "meeting_segments", ["meeting_id", "idx"], unique=True)
    op.create_table(
        "protocols",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("meeting_id", sa.String(64), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(64)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("decisions", sa.JSON(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_protocols_meeting_id", "protocols", ["meeting_id"])
    op.create_table(
        "action_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("protocol_id", sa.String(64), sa.ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_id", sa.String(64), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_key", sa.String(200), nullable=False, unique=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String(200), nullable=False),
        sa.Column("owner_speaker_id", sa.String(64)),
        sa.Column("deadline_text", sa.String(500), nullable=False),
        sa.Column("deadline_date", sa.Date()),
        sa.Column("urgency", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("source_segment_ids", sa.JSON(), nullable=False),
    )
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"])


def downgrade() -> None:
    for name in ("action_items", "protocols", "meeting_segments", "meeting_speakers", "meetings"):
        op.drop_table(name)
