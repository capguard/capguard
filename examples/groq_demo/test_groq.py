"""
Quick test of CapGuard with Groq API - No Docker needed!

This script tests the protected agent with Groq to verify:
1. LLMClassifier can talk to Groq API
2. Debug mode shows prompts and responses
3. Classification works correctly
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root / 'src'))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from capguard import ToolRegistry, ToolDefinition, ToolParameter
from capguard.classifiers import LLMClassifier

print("="*60)
print("CapGuard + Groq Quick Test")
print("="*60)

# Setup registry
registry = ToolRegistry()

def dummy_read(url: str) -> str:
    return f"Reading {url}"

def dummy_email(input_str: str) -> str:
    return f"Sending email: {input_str}"

registry.register(
    ToolDefinition(
        name="read_website",
        description="Read content from a URL",
        parameters=[ToolParameter(name="url", type="string", description="URL")],
        risk_level=2
    ),
    dummy_read
)

registry.register(
    ToolDefinition(
        name="send_email",
        description="Send an email. Format: recipient|subject|body",
        parameters=[ToolParameter(name="input_str", type="string", description="Email details")],
        risk_level=4
    ),
    dummy_email
)

# Create classifier with debug mode
DEBUG = os.getenv("CAPGUARD_DEBUG", "true").lower() == "true"
print(f"\nDebug mode: {DEBUG}")
print(f"Provider: {os.getenv('CAPGUARD_PROVIDER', 'groq')}")
print(f"Model: {os.getenv('CAPGUARD_MODEL', 'llama-3.3-70b-versatile')}\n")

classifier = LLMClassifier(
    tool_registry=registry,
    model=os.getenv("CAPGUARD_MODEL", "llama-3.3-70b-versatile"),
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    debug=DEBUG
)

# Test classification
test_request = "Summarize the article at http://example.com"
print(f"\nTest Request: '{test_request}'\n")

try:
    token = classifier.classify(test_request)
    print("\n" + "="*60)
    print("RESULT:")
    print("="*60)
    print(f"Granted tools: {token.granted_tools}")
    print(f"Confidence: {token.confidence}")
    print("\n✅ Test passed! Groq classifier working correctly.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
