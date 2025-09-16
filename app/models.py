from sqlalchemy.orm import Mapped, mapped_column
import enum
from sqlalchemy import Column, String, Text, Enum, Float
from app.db import Base


class DocumentStatus(str, enum.Enum):
    """
    Enum for document processing status
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Document(Base):
    """
    SQLAlchemy model for documents
    1. document_uuid: Primary key, unique identifier for the document
    2. name: Name of the document, must be unique
    3. url: URL of the document, must be unique
    4. status: Status of the document processing (PENDING, RUNNING, SUCCESS, FAILED)
    5. summary: Text summary of the document
    6. data_progress: Float indicating progress of data processing (0.0 to 1.0)
    7. error: Text field to store error messages if processing fails
    """

    __tablename__ = "documents"
    document_uuid = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    url = Column(String, unique=True, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    summary = Column(Text)
    data_progress = Column(Float, default=0.0)
    error = Column(Text)
