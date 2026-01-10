"""Audit log entry model."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .capability_token import CapabilityToken


class AuditLogEntry(BaseModel):
    """
    Audit log entry for tool execution attempts.
    
    Critical for security monitoring, compliance, and debugging.
    """
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    tool_name: str
    action: str = Field(
        ...,
        description="Action taken: 'granted', 'blocked', 'executed', 'failed'"
    )
    capability_token: CapabilityToken
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None
    potential_attack: bool = Field(
        default=False,
        description="Flag for security team review"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "abc-123",
                "tool_name": "send_email",
                "action": "blocked",
                "capability_token": {"...": "..."},
                "parameters": {"to": "attacker@evil.com"},
                "potential_attack": True
            }
        }
