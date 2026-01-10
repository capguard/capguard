"""Rule-based classifier - simple keyword matching."""

from typing import Dict, List
from ..core.classifier import IntentClassifier
from ..core.models import CapabilityToken
from ..core.registry import ToolRegistry


class RuleBasedClassifier(IntentClassifier):
    """
    Simple rule-based classifier using keyword matching.
    
    Fast, deterministic, no dependencies on external LLMs.
    Perfect for POC and common use cases.
    
    Example:
        >>> rules = {
        ...     "summarize": ["read_website"],
        ...     "email": ["read_website", "send_email"],
        ...     "search email": ["search_emails"]
        ... }
        >>> classifier = RuleBasedClassifier(registry, rules)
        >>> token = classifier.classify("Summarize this URL")
        >>> token.granted_tools
        {"read_website": True, "send_email": False, "search_emails": False}
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        rules: Dict[str, List[str]]
    ):
        """
        Initialize rule-based classifier.
        
        Args:
            tool_registry: Registry of available tools
            rules: Map of keywords to tool names
                   Example: {"summarize": ["read_website"]}
        """
        super().__init__(tool_registry)
        self.rules = rules
    
    def classify(self, user_request: str) -> CapabilityToken:
        """
        Classify using keyword matching.
        
        Checks if any keyword appears in the user request (case-insensitive).
        All tools start as denied, only granted if keyword matches.
        """
        request_lower = user_request.lower()
        granted: Dict[str, bool] = {}
        
        # Initialize all tools as denied
        for tool_name in self.get_available_tools():
            granted[tool_name] = False
        
        # Grant tools based on keyword matches
        matched_keywords = []
        for keyword, tool_names in self.rules.items():
            if keyword in request_lower:
                matched_keywords.append(keyword)
                for tool_name in tool_names:
                    granted[tool_name] = True
        
        # Confidence based on whether we matched anything
        confidence = 1.0 if matched_keywords else 0.5
        
        return CapabilityToken(
            user_request=user_request,
            granted_tools=granted,
            confidence=confidence,
            classification_method="rule-based"
        )


def create_default_rules() -> Dict[str, List[str]]:
    """
    Create default rules for common use cases.
    
    Returns:
        Default keyword -> tools mapping
    """
    return {
        # Web reading
        "summarize": ["read_website"],
        "fetch": ["read_website"],
        "read url": ["read_website"],
        "visit": ["read_website"],
        
        # Email sending
        "email me": ["read_website", "send_email"],
        "send email": ["send_email"],
        "forward": ["send_email"],
        
        # Email search
        "search email": ["search_emails"],
        "find email": ["search_emails"],
        "look for email": ["search_emails"],
        
        # File operations
        "read file": ["read_file"],
        "open file": ["read_file"],
        "write file": ["write_file"],
        "save file": ["write_file"],
    }
