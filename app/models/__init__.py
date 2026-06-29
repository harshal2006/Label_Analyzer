"""
SQLAlchemy ORM models package.

Importing all models here ensures they are registered with the Base metadata
before create_all() is called.
"""

from app.models.analysis import AnalysisResult  # noqa: F401
from app.models.upload import Upload  # noqa: F401
