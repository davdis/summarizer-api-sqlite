import enum
from sqlalchemy import Column,String,Text,DateTime,Enum,Float
from datetime import datetime
from app.db import Base
#from .db import Base
class DocumentStatus(str,enum.Enum): PENDING='PENDING';RUNNING='RUNNING';SUCCESS='SUCCESS';FAILED='FAILED'
class Document(Base):
    __tablename__='documents'
    document_uuid=Column(String,primary_key=True)
    name=Column(String,unique=True,index=True)
    url=Column(String,unique=True,index=True)
    status=Column(Enum(DocumentStatus),default=DocumentStatus.PENDING)
    summary=Column(Text)
    data_progress=Column(Float,default=0.0)
    error=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
