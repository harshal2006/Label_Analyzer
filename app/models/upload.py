"""
Upload ORM model.

Each row represents a single image upload.  The ``user_id`` column is
nullable to support anonymous uploads during development.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
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
    user = relationship("User", back_populates="uploads", lazy="selectin")
    analysis = relationship(
        "AnalysisResult",
        back_populates="upload",
        uselist=False,  # one-to-one
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Upload id={self.id} path={self.image_path!r}>"
