"""Classifiers for intent classification."""

from .rule_based import RuleBasedClassifier, create_default_rules
from .llm_based import LLMClassifier

# EmbeddingClassifier has heavy optional dependencies (sentence-transformers)
# Import it lazily to avoid errors when dependencies aren't installed
def __getattr__(name):
    if name == "EmbeddingClassifier":
        from .embedding_based import EmbeddingClassifier
        return EmbeddingClassifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'RuleBasedClassifier',
    'LLMClassifier',
    'EmbeddingClassifier',  # Available but lazy-loaded
    'create_default_rules',
]
