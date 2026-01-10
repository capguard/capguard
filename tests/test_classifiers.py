import pytest
from unittest.mock import MagicMock, patch
from capguard.core.registry import ToolRegistry, create_tool_definition
from capguard.classifiers import RuleBasedClassifier, EmbeddingClassifier, LLMClassifier
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

# --- Embedding Tests ---

def test_embedding_classifier(registry):
    # Mock SentenceTransformer to avoid loading heavy model in unit tests
    with patch("capguard.classifiers.embedding_based.SentenceTransformer") as MockST:
        mock_model = MockST.return_value
        # Mock encoding: return distinct vectors
        # "Read website" tool description -> [1.0, 0.0]
        # "Send email" tool description -> [0.0, 1.0]
        # User "read" -> [0.9, 0.1] (close to read)
        
        def mock_encode(text, convert_to_tensor=True):
            s = str(text).lower()
            if "read website" in s: return [1.0, 0.0]  # Tool desc
            if "send email" in s: return [0.0, 1.0]    # Tool desc
            if "read url" in s: return [1.0, 0.1]      # User query
            return [0.0, 0.0]
            
        mock_model.encode.side_effect = mock_encode
        
        # Need to patch cos_sim as well since we are using lists not tensors
        with patch("capguard.classifiers.embedding_based.util.cos_sim") as mock_sim:
            def simple_sim(a, b):
                # dot product for dummy vectors
                val = a[0]*b[0] + a[1]*b[1]
                return MagicMock(item=lambda: val)
            mock_sim.side_effect = simple_sim
            
            clf = EmbeddingClassifier(registry, model_name="dummy", threshold=0.5)
            
            token = clf.classify("read url")
            
            # Should match read_web (1.0*1.0) and not send_email
            assert token.granted_tools.get("read_web") == True
            assert token.granted_tools.get("send_email") == False

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
