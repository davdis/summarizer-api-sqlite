from pydantic import BaseModel, HttpUrl


class DocumentCreate(BaseModel):
    name: str
    url: HttpUrl
