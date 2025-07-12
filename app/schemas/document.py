from pydantic import BaseModel
from datetime import datetime

class DocumentInfo(BaseModel):
    id: str
    filename: str
    upload_date: datetime

class DocumentDetail(DocumentInfo):
    username: str
    file_size: int | None = None