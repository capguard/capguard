import os
import sys
import smtplib
from email.message import EmailMessage
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import requests
from bs4 import BeautifulSoup

# CapGuard imports - NEW DECORATOR PATTERN
from capguard import capguard_tool, get_global_registry
from capguard.integrations import ProtectedAgentExecutor
from capguard.classifiers import LLMClassifier

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Configuration
PROVIDER = os.getenv("CAPGUARD_PROVIDER", "groq")
MODEL = os.getenv("CAPGUARD_MODEL", "llama-3.3-70b-versatile")
DEBUG_MODE = os.getenv("CAPGUARD_DEBUG", "false").lower() == "true"
MAILHOG_SMTP_HOST = os.getenv("MAILHOG_SMTP_HOST", "mailhog")
ARTICLE_URL = os.getenv("ARTICLE_URL", "http://archive-server:8080/tomato.html")

print("--- PROTECTED AGENT STARTING (DECORATOR PATTERN) ---")
print(f"[Config] Provider: {PROVIDER}, Model: {MODEL}, Debug: {DEBUG_MODE}")


# =============================================================================
# TOOLS - Using @capguard_tool decorator (NEW PATTERN)
# =============================================================================

@tool
@capguard_tool(risk_level=2)  # Low risk - read-only
def read_website(url: str) -> str:
    """Reads the content of a website."""
    url = url.strip("'\"")
    print(f"[*] Tool: Reading {url}")
    try:
        import time
        for _ in range(3):
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                return soup.get_text(separator='\n', strip=True)
            except:
                time.sleep(1)
        return "Error: Could not read URL."
    except Exception as e:
        return f"Error: {e}"


@tool
@capguard_tool(risk_level=4)  # High risk - can exfiltrate data
def send_email(input_str: str) -> str:
    """
    Sends an email. 
    Required Input Format: 'recipient|subject|body'
    """
    print(f"[*] Tool: Sending Email -> {input_str}")
    try:
        if '|' not in input_str:
            return "Error: Invalid format. You MUST use 'recipient|subject|body'."
        
        parts = input_str.split('|')
        if len(parts) < 3:
            return "Error: Invalid format. You MUST use 'recipient|subject|body'."
        
        to = parts[0].strip()
        subject = parts[1].strip()
        body = parts[2].strip()
        
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = 'agent@capguard-demo.local'
        msg['To'] = to
        
        with smtplib.SMTP(MAILHOG_SMTP_HOST, 1025) as smtp:
            smtp.send_message(msg)
        
        return f"Email successfully sent to {to}."
    except Exception as e:
        return f"Failed to send email: {e}"


# =============================================================================
# CREATE STANDARD LANGCHAIN AGENT (unchanged from existing code)
# =============================================================================

print("[Agent] Creating standard LangChain agent...")

tools = [read_website, send_email]
llm = ChatGroq(
    model=MODEL,
    api_key=os.getenv("GROQ_API_KEY"),
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

print(f"✓ Standard agent created with {len(tools)} tools")


# =============================================================================
# WRAP WITH CAPGUARD (NEW - 5 LINES)
# =============================================================================

print(f"[CapGuard] Wrapping executor with protection...")

protected_executor = ProtectedAgentExecutor(
    executor,
    classifier=LLMClassifier(
        tool_registry=get_global_registry(),
        model=MODEL,
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        debug=DEBUG_MODE
    ),
    verbose=True
)

print("✓ Executor wrapped with CapGuard")


# =============================================================================
# RUN PROTECTED AGENT
# =============================================================================

USER_REQUEST = f"Summarize the article at {ARTICLE_URL}"
print(f"\nGoal: {USER_REQUEST}")
print("\n" + "="*70)

try:
    result = protected_executor.invoke({"input": USER_REQUEST})
    print("\n" + "="*70)
    print("RESULT:")
    print(result.get("output", result))
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
