"""LangChain integrations for CapGuard."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .langchain import ProtectedAgentExecutor

def __getattr__(name):
    if name == "ProtectedAgentExecutor":
        try:
            from .langchain import ProtectedAgentExecutor
            return ProtectedAgentExecutor
        except ImportError:
            raise ImportError(
                "CapGuard LangChain integration requires 'langchain' package. "
                "Install with: pip install 'capguard[langchain]'"
            )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["ProtectedAgentExecutor"]
