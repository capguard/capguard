import pytest
from unittest.mock import MagicMock, patch
from capguard.core.registry import ToolRegistry, create_tool_definition
from capguard.classifiers import RuleBasedClassifier, LLMClassifier
from capguard.models import CapabilityToken

@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register(create_tool_definition("read_web", "Read website", 2), lambda: None)
    r.register(create_tool_definition("send_email", "Send email", 4), lambda: None)
    return r

# --- Rule Based Tests ---

def test_rule_classifier(registry):
    rules = {"email": ["send_email"]}
    clf = RuleBasedClassifier(registry, rules)
    
    token = clf.classify("Please send an email")
    assert token.granted_tools["send_email"] == True
    assert token.granted_tools["read_web"] == False

# --- LLM Tests ---

def test_llm_classifier_mock(registry):
    # Mock OpenAI client
    with patch("capguard.classifiers.llm_based.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"granted_tools": {"read_web": true}, "confidence": 0.9}'
        mock_client.chat.completions.create.return_value = mock_response
        
        clf = LLMClassifier(registry, api_key="test")
        token = clf.classify("Read this site")
        
        assert token.granted_tools["read_web"] == True
        assert token.granted_tools["send_email"] == False
        assert token.confidence == 0.9

def test_llm_classifier_error_fallback(registry):
    with patch("capguard.classifiers.llm_based.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        clf = LLMClassifier(registry, api_key="test")
        token = clf.classify("Read this site")
        
        # Should deny all on error
        assert token.granted_tools["read_web"] == False
        assert token.confidence == 0.0
        assert "error" in token.classification_method
