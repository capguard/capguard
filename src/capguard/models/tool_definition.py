"""Tool definition models."""

from typing import Optional, Any, List
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    
    name: str
    type: str  # "str", "int", "float", "bool", etc.
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """
    Definition of a tool that agents can use.
    
    Includes metadata for security decisions (risk_level),
    user experience (description), and enforcement (parameters).
    """
    
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="What this tool does")
    parameters: List[ToolParameter] = Field(
        default_factory=list,
        description="Tool parameters"
    )
    risk_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Risk level: 1=safe (read-only), 5=critical (irreversible)"
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Should user confirm before execution?"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "send_email",
                "description": "Send an email message",
                "parameters": [
                    {"name": "to", "type": "str", "description": "Recipient", "required": True},
                    {"name": "subject", "type": "str", "description": "Subject", "required": True},
                    {"name": "body", "type": "str", "description": "Body", "required": True}
                ],
                "risk_level": 4,
                "requires_confirmation": True
            }
        }
