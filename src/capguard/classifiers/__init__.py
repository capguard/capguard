"""Classifiers for intent classification."""

from .rule_based import RuleBasedClassifier, create_default_rules

__all__ = [
    'RuleBasedClassifier',
    'create_default_rules',
]
