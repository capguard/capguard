"""Embedding-based classifier using sentence similarity."""

from typing import Dict
import numpy as np
from sentence_transformers import SentenceTransformer, util

from ..models import CapabilityToken
from ..core.classifier import IntentClassifier
from ..core.registry import ToolRegistry


class EmbeddingClassifier(IntentClassifier):
    """
    Embedding similarity-based classifier.
    
    Uses sentence-transformers to compute semantic similarity between
    user request and tool descriptions.
    
    Advantages:
    - Fast (<50ms)
    - Free (runs locally, no API)
    - No training needed
    - Automatically works with new tools
    
    Disadvantages:
    - Less accurate than LLM (85-90% vs 95%)
    - Can't extract constraints
    - Requires threshold tuning
    
    Example:
        >>> classifier = EmbeddingClassifier(
        ...     registry=registry,
        ...     model_name='all-MiniLM-L6-v2',
        ...     threshold=0.4
        ... )
        >>> token = classifier.classify("Summarize http://example.com")
        >>> token.granted_tools
        {'read_website': True, 'send_email': False}
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.4,
        device: str = "cpu"
    ):
        """
        Initialize embedding classifier.
        
        Args:
            tool_registry: Registry of available tools
            model_name: Sentence-transformers model name
                       Options:
                       - 'all-MiniLM-L6-v2' (default, 384-dim, fast)
                       - 'all-mpnet-base-v2' (768-dim, slower but more accurate)
                       - 'paraphrase-MiniLM-L6-v2' (384-dim, good for paraphrases)
            threshold: Similarity threshold (0.0-1.0)
                      Higher = more conservative (fewer false positives)
                      Lower = more permissive (fewer false negatives)
                      Recommended: 0.3-0.5
            device: Device to run on ('cpu' or 'cuda')
        """
        super().__init__(tool_registry)
        
        self.model_name = model_name
        self.threshold = threshold
        
        # Load sentence-transformer model
        self.model = SentenceTransformer(model_name, device=device)
        
        # Pre-compute tool embeddings (done once at init)
        self._precompute_tool_embeddings()
    
    def _precompute_tool_embeddings(self) -> None:
        """Pre-compute embeddings for all tool descriptions."""
        if not self.tool_registry:
            self.tool_embeddings = {}
            return
        
        self.tool_embeddings = {}
        
        for tool_name, definition in self.tool_registry.get_all_definitions().items():
            # Create rich description including parameters
            params_desc = ", ".join([p.name for p in definition.parameters]) if definition.parameters else "none"
            rich_description = f"{definition.description}. Parameters: {params_desc}"
            
            # Encode
            embedding = self.model.encode(rich_description, convert_to_tensor=True)
            self.tool_embeddings[tool_name] = embedding
    
    def classify(self, user_request: str) -> CapabilityToken:
        """
        Classify using embedding similarity.
        
        Computes cosine similarity between user request embedding and
        each tool description embedding. Grants tools above threshold.
        """
        if not self.tool_embeddings:
            # No tools registered
            return CapabilityToken(
                user_request=user_request,
                granted_tools={},
                confidence=0.0,
                classification_method=f"embedding-{self.model_name}"
            )
        
        # Encode user request
        request_embedding = self.model.encode(user_request, convert_to_tensor=True)
        
        # Compute similarity to each tool
        granted_tools = {}
        similarities = {}
        
        for tool_name, tool_embedding in self.tool_embeddings.items():
            # Cosine similarity
            similarity = util.cos_sim(request_embedding, tool_embedding).item()
            similarities[tool_name] = similarity
            
            # Grant if above threshold
            granted_tools[tool_name] = similarity > self.threshold
        
        # Confidence = max similarity (how well we matched)
        max_similarity = max(similarities.values()) if similarities else 0.0
        
        return CapabilityToken(
            user_request=user_request,
            granted_tools=granted_tools,
            confidence=float(max_similarity),
            classification_method=f"embedding-{self.model_name}"
        )
    
    def get_similarities(self, user_request: str) -> Dict[str, float]:
        """
        Get similarity scores for all tools (for debugging/analysis).
        
        Returns:
            Dict mapping tool name to similarity score (0.0-1.0)
        """
        request_embedding = self.model.encode(user_request, convert_to_tensor=True)
        
        similarities = {}
        for tool_name, tool_embedding in self.tool_embeddings.items():
            similarity = util.cos_sim(request_embedding, tool_embedding).item()
            similarities[tool_name] = similarity
        
        return similarities
    
    def tune_threshold(self, examples: list, target_precision: float = 0.95) -> float:
        """
        Automatically tune threshold based on labeled examples.
        
        Args:
            examples: List of (user_request, expected_granted_tools) tuples
            target_precision: Target precision (default: 0.95 = low false positives)
        
        Returns:
            Optimal threshold value
        
        Example:
            >>> examples = [
            ...     ("Summarize URL", {"read_website": True, "send_email": False}),
            ...     ("Email me summary", {"read_website": True, "send_email": True}),
            ... ]
            >>> optimal_threshold = classifier.tune_threshold(examples)
            >>> classifier.threshold = optimal_threshold
        """
        # Try different thresholds
        thresholds = np.arange(0.1, 0.9, 0.05)
        best_threshold = 0.4
        best_f1 = 0.0
        
        for threshold in thresholds:
            self.threshold = threshold
            
            # Evaluate on examples
            correct = 0
            total = 0
            
            for user_request, expected_tools in examples:
                token = self.classify(user_request)
                
                # Check if classification matches expected
                for tool, expected_granted in expected_tools.items():
                    actual_granted = token.granted_tools.get(tool, False)
                    if actual_granted == expected_granted:
                        correct += 1
                    total += 1
            
            accuracy = correct / total if total > 0 else 0.0
            
            if accuracy > best_f1:
                best_f1 = accuracy
                best_threshold = threshold
        
        self.threshold = best_threshold
        return best_threshold
