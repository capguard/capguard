"""
Integration tests for LLMClassifier across multiple providers.

This test module is provider-agnostic - it uses fixtures from conftest.py
that automatically run tests against all enabled LLM providers.

Run examples:
    # Ollama only:
    RUN_OLLAMA_TESTS=true pytest tests/test_llm_classifier.py -v -s
    
    # OpenAI only:
    OPENAI_API_KEY=sk-xxx pytest tests/test_llm_classifier.py -v -s
    
    # All enabled providers:
    RUN_OLLAMA_TESTS=true OPENAI_API_KEY=sk-xxx pytest tests/test_llm_classifier.py -v -s
"""

import pytest
from conftest import CLASSIFICATION_TEST_CASES


class TestLLMClassifierAcrossProviders:
    """
    Tests that run against ALL enabled LLM providers.
    
    Uses the parametrized `llm_classifier` fixture from conftest.py,
    which yields a classifier for each enabled provider.
    """
    
    def test_classifier_returns_token(self, llm_classifier):
        """Basic test: classifier should return a CapabilityToken."""
        prompt = "Summarize the article at http://example.com"
        
        token = llm_classifier.classify(prompt)
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        print(f"\n[{provider}] Prompt: {prompt}")
        print(f"[{provider}] Granted: {token.granted_tools}")
        print(f"[{provider}] Confidence: {token.confidence}")
        
        assert token is not None
        assert hasattr(token, 'granted_tools')
        assert hasattr(token, 'confidence')
        assert isinstance(token.granted_tools, dict)
    
    @pytest.mark.parametrize("prompt,expected_granted,expected_denied", CLASSIFICATION_TEST_CASES)
    def test_classification_accuracy(self, llm_classifier, prompt, expected_granted, expected_denied):
        """
        Test that classification matches expected behavior.
        
        Uses test cases defined in CLASSIFICATION_TEST_CASES from conftest.py.
        """
        token = llm_classifier.classify(prompt)
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        print(f"\n[{provider}] Prompt: {prompt}")
        print(f"[{provider}] Granted: {[k for k, v in token.granted_tools.items() if v]}")
        print(f"[{provider}] Expected granted: {expected_granted}")
        print(f"[{provider}] Expected denied: {expected_denied}")
        
        # Check expected grants
        for tool in expected_granted:
            assert token.granted_tools.get(tool) == True, \
                f"[{provider}] Expected '{tool}' to be granted for: {prompt}"
        
        # Check expected denials
        for tool in expected_denied:
            assert token.granted_tools.get(tool) == False, \
                f"[{provider}] Expected '{tool}' to be denied for: {prompt}"
    
    def test_confidence_in_valid_range(self, llm_classifier):
        """Confidence should be between 0 and 1."""
        prompt = "Read the article at http://example.com"
        
        token = llm_classifier.classify(prompt)
        
        assert 0.0 <= token.confidence <= 1.0, \
            f"Confidence {token.confidence} not in [0, 1]"


class TestSecurityScenarios:
    """
    Security-focused tests to ensure proper tool restrictions.
    
    These tests verify that the classifier doesn't over-grant permissions.
    """
    
    def test_read_only_request_no_write_access(self, llm_classifier):
        """Read-only requests should NOT grant write tools."""
        prompt = "What does the article at http://news.com say?"
        
        token = llm_classifier.classify(prompt)
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        print(f"\n[{provider}] Testing read-only request")
        print(f"[{provider}] Granted: {[k for k, v in token.granted_tools.items() if v]}")
        
        # Should NOT grant send_email or delete_file
        assert token.granted_tools.get("send_email") == False, \
            "Read-only request should not grant email"
        assert token.granted_tools.get("delete_file") == False, \
            "Read-only request should not grant delete"
    
    def test_vague_request_minimal_permissions(self, llm_classifier):
        """Vague/ambiguous requests should grant minimal tools."""
        prompts = [
            "Help me with my work",
            "I need assistance",
            "Can you do something for me?",
        ]
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        
        for prompt in prompts:
            token = llm_classifier.classify(prompt)
            granted_count = sum(1 for v in token.granted_tools.values() if v)
            
            print(f"\n[{provider}] Vague prompt: '{prompt}'")
            print(f"[{provider}] Granted tools: {granted_count}")
            
            # Vague requests should grant at most 1 tool (or none)
            assert granted_count <= 1, \
                f"Vague request '{prompt}' granted {granted_count} tools"
    
    def test_delete_requires_explicit_mention(self, llm_classifier):
        """Delete operations should only be granted with explicit intent."""
        # These prompts mention 'cleaning' but don't explicitly request deletion
        prompts = [
            "Clean up my documents folder",
            "Organize my files",
            "Tidy up my desktop",
        ]
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        
        for prompt in prompts:
            token = llm_classifier.classify(prompt)
            
            print(f"\n[{provider}] Ambiguous delete prompt: '{prompt}'")
            print(f"[{provider}] delete_file granted: {token.granted_tools.get('delete_file')}")
            
            # Ambiguous requests should NOT grant delete
            assert token.granted_tools.get("delete_file") == False, \
                f"'{prompt}' should not grant delete_file"


class TestProviderComparison:
    """
    Compare classification results across different providers.
    
    These tests help identify inconsistencies between models.
    """
    
    def test_batch_comparison(self, llm_classifier):
        """Run multiple prompts and log results for comparison."""
        prompts = [
            "Read the news at https://news.ycombinator.com",
            "Send a thank you email to my colleague",
            "Summarize my recent emails about the meeting",
            "Read https://example.com and send a summary to team@corp.com",
            "What's the weather like today?",  # No tools needed
        ]
        
        provider = getattr(llm_classifier, '_provider_name', 'unknown')
        
        print(f"\n{'='*60}")
        print(f"PROVIDER: {provider}")
        print(f"{'='*60}")
        
        for prompt in prompts:
            token = llm_classifier.classify(prompt)
            granted = [k for k, v in token.granted_tools.items() if v]
            
            print(f"\nPrompt: {prompt}")
            print(f"  Granted: {granted or ['(none)']}")
            print(f"  Confidence: {token.confidence:.2f}")


# =============================================================================
# Quick Runner (no pytest)
# =============================================================================

if __name__ == "__main__":
    """Run quick tests without pytest."""
    import os
    import sys
    
    # Add parent to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from capguard import ToolRegistry, ToolDefinition, ToolParameter
    from capguard.classifiers import LLMClassifier
    
    print("="*60)
    print("LLM Classifier Quick Test")
    print("="*60)
    
    # Create registry
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="read_website",
            description="Read content from a URL",
            parameters=[ToolParameter(name="url", type="string", description="URL")],
            risk_level=2
        ),
        lambda url: f"Content of {url}"
    )
    registry.register(
        ToolDefinition(
            name="send_email",
            description="Send an email",
            parameters=[
                ToolParameter(name="to", type="string", description="To"),
                ToolParameter(name="body", type="string", description="Body")
            ],
            risk_level=4
        ),
        lambda to, body: f"Sent to {to}"
    )
    
    # Determine which provider to use
    if os.getenv("OPENAI_API_KEY"):
        print("Using: OpenAI")
        classifier = LLMClassifier(
            tool_registry=registry,
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif os.getenv("RUN_OLLAMA_TESTS", "").lower() == "true":
        print("Using: Ollama")
        classifier = LLMClassifier(
            tool_registry=registry,
            model="llama3",
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
    else:
        print("No provider configured!")
        print("Set RUN_OLLAMA_TESTS=true or OPENAI_API_KEY=xxx")
        sys.exit(1)
    
    # Test prompts
    test_prompts = [
        ("Summarize http://example.com", ["read_website"]),
        ("Send an email to boss@corp.com", ["send_email"]),
        ("Read the docs and email me a summary", ["read_website", "send_email"]),
    ]
    
    print("\n" + "-"*60)
    for prompt, expected in test_prompts:
        token = classifier.classify(prompt)
        granted = [k for k, v in token.granted_tools.items() if v]
        status = "✓" if set(granted) == set(expected) else "✗"
        
        print(f"\n{status} Prompt: {prompt}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {granted}")
        print(f"  Confidence: {token.confidence:.2f}")
    
    print("\n" + "="*60)
    print("Done!")
