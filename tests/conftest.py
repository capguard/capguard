"""
Pytest configuration and fixtures for LLMClassifier integration tests.

This module provides a provider-agnostic test architecture using:
- Factory pattern for creating classifiers
- Pytest parametrization for running same tests across providers
- Environment-based configuration for credentials

Supported Providers:
- ollama: Local Ollama instance (free, requires Docker)
- openai: OpenAI API (requires OPENAI_API_KEY)
- (extensible for future providers)

Usage:
    # Run with Ollama only:
    RUN_OLLAMA_TESTS=true pytest tests/test_llm_classifier.py -v -s
    
    # Run with OpenAI only:
    OPENAI_API_KEY=sk-xxx pytest tests/test_llm_classifier.py -v -s
    
    # Run with both:
    RUN_OLLAMA_TESTS=true OPENAI_API_KEY=sk-xxx pytest tests/test_llm_classifier.py -v -s
"""

import os
import pytest
from dataclasses import dataclass
from typing import Optional, Callable, List

from capguard import ToolRegistry, ToolDefinition, ToolParameter
from capguard.classifiers import LLMClassifier


# =============================================================================
# Provider Configuration
# =============================================================================

@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    model: str
    base_url: Optional[str]
    api_key: str
    enabled_check: Callable[[], bool]
    
    def is_enabled(self) -> bool:
        """Check if this provider is enabled for testing."""
        return self.enabled_check()
    
    def create_classifier(self, registry: ToolRegistry) -> LLMClassifier:
        """Factory method to create a classifier for this provider."""
        return LLMClassifier(
            tool_registry=registry,
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0.0
        )


# Define available providers
PROVIDERS = {
    "ollama": LLMProviderConfig(
        name="ollama",
        model=os.getenv("OLLAMA_MODEL", "llama3"),
        base_url=os.getenv("OLLAMA_URL", "http://localhost:11434/v1"),
        api_key="ollama",
        enabled_check=lambda: os.getenv("RUN_OLLAMA_TESTS", "").lower() == "true"
    ),
    "openai": LLMProviderConfig(
        name="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=None,  # Uses default OpenAI URL
        api_key=os.getenv("OPENAI_API_KEY", ""),
        enabled_check=lambda: bool(os.getenv("OPENAI_API_KEY"))
    ),
    "groq": LLMProviderConfig(
        name="groq",
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY", ""),
        enabled_check=lambda: bool(os.getenv("GROQ_API_KEY"))
    ),
}


def get_enabled_providers() -> List[str]:
    """Get list of enabled provider names."""
    return [name for name, config in PROVIDERS.items() if config.is_enabled()]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def standard_tool_registry():
    """
    Create a standard tool registry with common tools for testing.
    
    Tools included:
    - read_website (risk=2): Read-only web access
    - search_emails (risk=3): Search user emails
    - send_email (risk=4): Can exfiltrate data
    - delete_file (risk=5): Destructive operation
    """
    registry = ToolRegistry()
    
    registry.register(
        ToolDefinition(
            name="read_website",
            description="Read content from a URL",
            parameters=[ToolParameter(name="url", type="string", description="The URL")],
            risk_level=2
        ),
        lambda url: f"Content of {url}"
    )
    
    registry.register(
        ToolDefinition(
            name="search_emails",
            description="Search user's emails for a query",
            parameters=[ToolParameter(name="query", type="string", description="Query")],
            risk_level=3
        ),
        lambda query: f"Results for {query}"
    )
    
    registry.register(
        ToolDefinition(
            name="send_email",
            description="Send an email to a recipient",
            parameters=[
                ToolParameter(name="to", type="string", description="Recipient"),
                ToolParameter(name="subject", type="string", description="Subject"),
                ToolParameter(name="body", type="string", description="Body")
            ],
            risk_level=4
        ),
        lambda to, subject, body: f"Sent to {to}"
    )
    
    registry.register(
        ToolDefinition(
            name="delete_file",
            description="Delete a file from the filesystem",
            parameters=[ToolParameter(name="path", type="string", description="Path")],
            risk_level=5
        ),
        lambda path: f"Deleted {path}"
    )
    
    return registry


@pytest.fixture(params=get_enabled_providers() or ["skip"])
def llm_classifier(request, standard_tool_registry):
    """
    Parametrized fixture that yields classifiers for all enabled providers.
    
    Tests using this fixture will run once per enabled provider.
    """
    provider_name = request.param
    
    if provider_name == "skip":
        pytest.skip("No LLM providers enabled. Set RUN_OLLAMA_TESTS=true or OPENAI_API_KEY=xxx")
    
    config = PROVIDERS[provider_name]
    classifier = config.create_classifier(standard_tool_registry)
    
    # Attach provider name for test output
    classifier._provider_name = provider_name
    
    return classifier


@pytest.fixture
def ollama_classifier(standard_tool_registry):
    """Fixture specifically for Ollama tests."""
    config = PROVIDERS["ollama"]
    if not config.is_enabled():
        pytest.skip("Ollama tests disabled. Set RUN_OLLAMA_TESTS=true")
    return config.create_classifier(standard_tool_registry)


@pytest.fixture
def openai_classifier(standard_tool_registry):
    """Fixture specifically for OpenAI tests."""
    config = PROVIDERS["openai"]
    if not config.is_enabled():
        pytest.skip("OpenAI tests disabled. Set OPENAI_API_KEY")
    return config.create_classifier(standard_tool_registry)


# =============================================================================
# Test Case Definitions (for parametrization)
# =============================================================================

# Define test cases as (prompt, expected_granted, expected_denied)
CLASSIFICATION_TEST_CASES = [
    pytest.param(
        "Summarize the article at http://example.com",
        ["read_website"],
        ["send_email", "delete_file"],
        id="summarize_website"
    ),
    pytest.param(
        "Send an email to john@example.com saying hello",
        ["send_email"],
        ["read_website", "delete_file"],
        id="send_email"
    ),
    pytest.param(
        "Find emails about the project and forward them to manager@corp.com",
        ["search_emails", "send_email"],
        ["delete_file"],
        id="search_and_forward"
    ),
    pytest.param(
        "Read https://news.com and email me a summary",
        ["read_website", "send_email"],
        ["delete_file"],
        id="read_and_email"
    ),
]
