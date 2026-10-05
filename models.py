import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_job_idempotency_key"
        ),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    idempotency_key: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    job_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    parameters: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String,
        default="PENDING"
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    error: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )