"""
审核 Schema
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditRequest(BaseModel):
    product_id: int
    approved: bool
    comment: Optional[str] = None


class AuditResponse(BaseModel):
    id: int
    product_id: int
    status: str  # pending / approved / rejected
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
