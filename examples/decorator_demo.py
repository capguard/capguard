"""
Decorator Pattern Demo - 5-Minute CapGuard Integration

This demonstrates how to add CapGuard protection to an existing 
modular LangChain agent with minimal code changes.

Setup time: ~5 minutes
Changes required:
  - 1 line per tool (add @capguard_tool decorator)
  - 4 lines in main (wrap executor)
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2] / 'src'))

# =============================================================================
# PART 1: EXISTING AGENT (Before CapGuard)
# =============================================================================

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
import requests
from bs4 import BeautifulSoup

# --- tools.py (Your existing tools) ---

@tool
def read_website(url: str) -> str:
    """Fetch and read content from a URL"""
    url = url.strip("'\"")
    print(f"  [Tool] Reading {url}")
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n', strip=True)[:500]
    except Exception as e:
        return f"Error: {e}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email"""
    print(f"  [Tool] Sending email to {to}")
    print(f"    Subject: {subject}")
    print(f"    Body: {body[:50]}...")
    return f"Email sent to {to}"

@tool
def search_emails(query: str) -> str:
    """Search user's emails"""
    print(f"  [Tool] Searching emails for: {query}")
    return f"Found 3 emails matching '{query}'"


# --- agent.py (Your existing agent) ---

def create_my_agent():
    """Create a standard LangChain ReAct agent."""
    tools = [read_website, send_email, search_emails]
    
    llm = ChatOllama(
        model="llama3",
        base_url="http://localhost:11434",
        temperature=0
    )
    
    template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    
    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    
    return executor


# =============================================================================
# PART 2: VULNERABLE DEMO (Without CapGuard)
# =============================================================================

def demo_without_capguard():
    """
    Run agent WITHOUT CapGuard protection.
    
    Expected: Agent gets tricked by malicious payload,
    calls send_email even though user only asked for summarization.
    """
    print("\n" + "="*70)
    print("DEMO 1: WITHOUT CapGuard (Vulnerable)")
    print("="*70)
    
    executor = create_my_agent()
    
    # Simulate malicious website payload
    malicious_request = "Summarize important information"
    
    print(f"\nUser Request: '{malicious_request}'")
    print("(Imagine the website contains hidden payload to send emails)\n")
    
    # In a real scenario, the read_website would return content with injection
    # For demo, we'll just show the agent has access to ALL tools
    
    print(f"Agent has access to: {[t.name for t in executor.tools]}")
    print("⚠️  Agent can call send_email even though user only asked for summary!")
    

# =============================================================================
# PART 3: ADD CAPGUARD (5-Minute Integration)
# =============================================================================

print("\n" + "="*70)
print("ADDING CAPGUARD PROTECTION")
print("="*70)

# Step 1: Add @capguard_tool decorator to tools (1 line per tool)
print("\n1. Adding @capguard_tool decorators to tools...")

from capguard import capguard_tool

@tool
@capguard_tool(risk_level=2)  # <-- ADD THIS LINE
def read_website_protected(url: str) -> str:
    """Fetch and read content from a URL"""
    return read_website.func(url)

@tool
@capguard_tool(risk_level=4)  # <-- ADD THIS LINE
def send_email_protected(to: str, subject: str, body: str) -> str:
    """Send an email"""
    return send_email.func(to, subject, body)

@tool
@capguard_tool(risk_level=3)  # <-- ADD THIS LINE
def search_emails_protected(query: str) -> str:
    """Search user's emails"""
    return search_emails.func(query)

print("✓ Tools decorated and registered with CapGuard")


# Step 2: Create agent with decorated tools
def create_protected_agent():
    """Create agent with CapGuard-decorated tools."""
    tools = [read_website_protected, send_email_protected, search_emails_protected]
    
    llm = ChatOllama(
        model="llama3",
        base_url="http://localhost:11434",
        temperature=0
    )
    
    template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    
    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    
    return executor


# Step 3: Wrap with ProtectedAgentExecutor (4 lines)
print("\n2. Wrapping executor with CapGuard protection...")

from capguard.integrations import ProtectedAgentExecutor
from capguard.classifiers import LLMClassifier
from capguard import get_global_registry

executor = create_protected_agent()

# ADD THESE 4 LINES:
protected_executor = ProtectedAgentExecutor(
    executor,
    classifier=LLMClassifier(
        tool_registry=get_global_registry(),
        model="llama3",
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    ),
    verbose=True
)

print("✓ Executor wrapped with CapGuard")


# =============================================================================
# PART 4: PROTECTED DEMO (With CapGuard)
# =============================================================================

def demo_with_capguard():
    """
    Run agent WITH CapGuard protection.
    
    Expected: CapGuard classifies intent, grants only read_website,
    agent cannot call send_email even if payload tries to trick it.
    """
    print("\n" + "="*70)
    print("DEMO 2: WITH CapGuard (Protected)")
    print("="*70)
    
    user_request = "Summarize http://example.com"
    
    print(f"\nUser Request: '{user_request}'")
    print("\nCapGuard will now:")
    print("  1. Classify intent (only needs read_website)")
    print("  2. Grant ONLY read_website")
    print("  3. Agent runs with restricted toolset")
    print("  4. Even if website tries to trick agent, send_email is unavailable!\n")
    
    try:
        result = protected_executor.invoke({"input": user_request})
        print("\n" + "="*70)
        print("RESULT:")
        print("="*70)
        print(result.get("output", result))
    except Exception as e:
        print(f"\nError: {e}")
        print("(Make sure Ollama is running: docker run -d -p 11434:11434 ollama/ollama)")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CAPGUARD DECORATOR PATTERN DEMO")
    print("="*70)
    print("\nThis demonstrates 5-minute integration:")
    print("  1. Add @capguard_tool decorator to each tool")
    print("  2. Wrap executor with ProtectedAgentExecutor")
    print("  3. Use exact same .invoke() API")
    print("="*70)
    
    # Demo 1: Show vulnerability
    demo_without_capguard()
    
    # Demo 2: Show protection
    demo_with_capguard()
    
    print("\n" + "="*70)
    print("COMPARISON:")
    print("="*70)
    print("Without CapGuard: Agent has ALL tools")
    print("With CapGuard:    Agent has ONLY granted tools")
    print("\nTotal code added: ~10 lines")
    print("Integration time: ~5 minutes")
    print("="*70)
