"""
Upload ORM model.

Each row represents a single image upload.  The ``user_id`` column stores
the Supabase Auth UUID as a plain string reference (no local FK).
It is nullable to support legacy rows and anonymous development uploads.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis = relationship(
        "AnalysisResult",
        back_populates="upload",
        uselist=False,  # one-to-one
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Upload id={self.id} user_id={self.user_id!r} path={self.image_path!r}>"
