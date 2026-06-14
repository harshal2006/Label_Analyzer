"""
AnalysisResult ORM model.

Stores the OCR output and (future) health-score / analysis data for a
given upload.  The ``health_score`` and ``analysis_json`` columns are
nullable placeholders for Week 2+ features.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to the upload
    upload = relationship("Upload", back_populates="analysis", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AnalysisResult id={self.id} upload_id={self.upload_id}>"
