"""LLM-based classifier using OpenAI-compatible APIs."""

import json
from typing import Optional

from ..models import CapabilityToken
from ..core.classifier import IntentClassifier
from ..core.registry import ToolRegistry
from ..prompts import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT_TEMPLATE


class LLMClassifier(IntentClassifier):
    """
    LLM-based intent classifier using OpenAI-compatible APIs.
    
    Works with:
    - OpenAI (GPT-4, GPT-4o-mini, etc.)
    - Ollama (local, in Docker)
    - Any OpenAI-compatible endpoint
    
    This is provider-agnostic - just change base_url and model.
    
    Example (Ollama):
        >>> classifier = LLMClassifier(
        ...     registry=registry,
        ...     baseurl="http://localhost:11434/v1",
        ...     model="llama3",
        ...     api_key="ollama"
        ... )
        >>> token = classifier.classify("Summarize http://example.com")
        
    Example (OpenAI):
        >>> classifier = LLMClassifier(
        ...     registry=registry,
        ...     model="gpt-4o-mini",
        ...     api_key=os.getenv("OPENAI_API_KEY")
        ... )
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        api_key: str = "required",
        temperature: float = 0.0,
        max_tokens: int = 500,
        debug: bool = False,
    ):
        """
        Initialize LLM classifier.
        
        Args:
            tool_registry: Registry of available tools
            model: Model name (e.g., "gpt-4o-mini", "llama3")
            base_url: API base URL (None for OpenAI, "http://localhost:11434/v1" for Ollama)
            api_key: API key (or "ollama" for local Ollama)
            temperature: LLM temperature (0.0 = deterministic)
            max_tokens: Max tokens in response
            debug: If True, log prompts and responses (default: False)
        """
        super().__init__(tool_registry)
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.debug = debug
        
        # Setup debug logging
        if self.debug:
            import logging
            self.logger = logging.getLogger(f"capguard.classifier.{model}")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.DEBUG)
        else:
            self.logger = None
        
        
        # Import OpenAI lazily (optional dependency)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "LLMClassifier requires 'openai' package. "
                "Install with: pip install 'capguard[llm]'"
            )

        # Create OpenAI client (works with Ollama too!)
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
    
    def classify(self, user_request: str) -> CapabilityToken:
        """
        Classify user intent using LLM.
        
        Sends the user request + tool descriptions to the LLM,
        which returns which tools are needed.
        
        Security: LLM ONLY sees user request, never external data.
        """
        # 1. Format available tools
        tools_description = self._format_tools()
        
        # 2. Build prompt
        user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
            tools_description=tools_description,
            user_request=user_request
        )
        
        if self.debug and self.logger:
            self.logger.debug("=" * 60)
            self.logger.debug("SYSTEM PROMPT:")
            self.logger.debug(CLASSIFICATION_SYSTEM_PROMPT)
            self.logger.debug("-" * 60)
            self.logger.debug("USER PROMPT:")
            self.logger.debug(user_prompt)
            self.logger.debug("=" * 60)
        
        # 3. Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # 4. Parse response
            content = response.choices[0].message.content
            
            if self.debug and self.logger:
                self.logger.debug("LLM RAW RESPONSE:")
                self.logger.debug(content)
                self.logger.debug("=" * 60)
            
            result = json.loads(content)
            
            granted_tools = result.get("granted_tools", {})
            confidence = result.get("confidence", 0.5)
            reasoning = result.get("reasoning", "No reasoning provided")
            
            if self.debug and self.logger:
                self.logger.debug("Parsed Token:")
                self.logger.debug(f"  Granted: {granted_tools}")
                self.logger.debug(f"  Confidence: {confidence}")
                self.logger.debug(f"  Reasoning: {reasoning}")
            
            # 5. Ensure all tools are represented (default to False)
            for tool_name in self.get_available_tools():
                if tool_name not in granted_tools:
                    granted_tools[tool_name] = False
            
            return CapabilityToken(
                user_request=user_request,
                granted_tools=granted_tools,
                confidence=float(confidence),
                classification_method=f"llm-{self.model}"
            )
            
        except Exception as e:
            # Fallback: deny all tools on error
            return CapabilityToken(
                user_request=user_request,
                granted_tools={tool: False for tool in self.get_available_tools()},
                confidence=0.0,
                classification_method=f"llm-{self.model}-error: {str(e)}"
            )
    
    def _format_tools(self) -> str:
        """Format tool registry as text for LLM prompt."""
        if not self.tool_registry:
            return "No tools available."
        
        lines = []
        for tool_name, definition in self.tool_registry.get_all_definitions().items():
            params = ", ".join([
                p.name for p in definition.parameters
            ]) if definition.parameters else "none"
            
            lines.append(
                f"- {tool_name} (risk={definition.risk_level}): "
                f"{definition.description} [params: {params}]"
            )
        
        return "\n".join(lines)
