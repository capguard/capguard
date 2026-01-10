"""Base classifier interface for intent classification."""

from abc import ABC, abstractmethod
from typing import Optional
from .models import CapabilityToken
from .registry import ToolRegistry


class IntentClassifier(ABC):
    """
    Abstract base class for all intent classifiers.
    
    Classifiers analyze the user's request and determine which tools
    should be granted. This happens BEFORE the agent sees any external data.
    
    Security Property:
        Classifiers ONLY receive the original user request - never external
        content that might contain malicious payloads.
    """
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        Initialize classifier.
        
        Args:
            tool_registry: Registry of available tools (optional for some classifiers)
        """
        self.tool_registry = tool_registry
    
    @abstractmethod
    def classify(self, user_request: str) -> CapabilityToken:
        """
        Classify user intent and generate capability token.
        
        Args:
            user_request: The original user request (ONLY - no external data)
            
        Returns:
            CapabilityToken specifying granted tools and constraints
            
        Example:
            >>> classifier = RuleBasedClassifier(...)
            >>> token = classifier.classify("Summarize http://example.com")
            >>> token.granted_tools
            {"read_website": True, "send_email": False}
        """
        pass
    
    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        if self.tool_registry is None:
            return []
        return self.tool_registry.list_tools()
