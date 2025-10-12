"""
NLP Tool - Performs natural language processing on text data.
Includes TF-IDF, keyword extraction, and text analysis.
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("nlp_tool")


class NLPTool(BaseTool):
    """
    Performs natural language processing operations on text data.
    
    Features:
    - TF-IDF keyword extraction
    - Text similarity
    - Keyword frequency analysis
    - Sentiment-aware keyword extraction
    """
    
    @property
    def name(self) -> str:
        return "nlp_analysis"
    
    @property
    def description(self) -> str:
        return """Perform NLP analysis on text data to extract insights.

Use this tool when you need to:
- Extract important keywords from text (TF-IDF)
- Find common themes or topics
- Analyze text patterns
- Get keyword frequencies

Parameters:
- texts: List of text strings to analyze
- operation: Type of NLP operation (tfidf, keywords, themes)
- top_k: Number of top results to return (default 10)
- column: Column name containing text (when data is provided)

Returns extracted keywords, themes, and insights.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of text strings to analyze"
                },
                "data": {
                    "type": "array",
                    "description": "Alternative: list of data rows with text column"
                },
                "column": {
                    "type": "string",
                    "description": "Column name containing text (when using data)"
                },
                "operation": {
                    "type": "string",
                    "enum": ["tfidf", "keywords", "themes", "ngrams"],
                    "description": "Type of NLP operation",
                    "default": "tfidf"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results",
                    "default": 10
                }
            }
        }
    
    async def execute(
        self,
        texts: Optional[List[str]] = None,
        data: Optional[List[Dict[str, Any]]] = None,
        column: Optional[str] = None,
        operation: str = "tfidf",
        top_k: int = 10,
        **kwargs
    ) -> ToolResult:
        """
        Perform NLP analysis on text data.
        
        Args:
            texts: List of text strings
            data: Alternative - list of data rows
            column: Column containing text
            operation: Type of operation
            top_k: Number of results
            
        Returns:
            ToolResult with NLP analysis results
        """
        try:
            # Extract texts from data if provided
            if data and column:
                texts = [row.get(column, "") for row in data if row.get(column)]
            
            if not texts:
                return ToolResult(
                    success=False,
                    summary="No text data provided",
                    error="texts or (data + column) required"
                )
            
            # Filter empty texts
            texts = [t for t in texts if t and isinstance(t, str)]
            
            if not texts:
                return ToolResult(
                    success=False,
                    summary="No valid text data found",
                    error="All texts are empty or invalid"
                )
            
            if operation == "tfidf":
                result = self._tfidf_analysis(texts, top_k)
            elif operation == "keywords":
                result = self._keyword_extraction(texts, top_k)
            elif operation == "themes":
                result = self._theme_extraction(texts, top_k)
            elif operation == "ngrams":
                result = self._ngram_analysis(texts, top_k)
            else:
                return ToolResult(
                    success=False,
                    summary=f"Unknown operation: {operation}",
                    error=f"Operation '{operation}' not supported"
                )
            
            return ToolResult(
                success=True,
                data=result,
                summary=self._generate_summary(operation, result),
                metadata={
                    "operation": operation,
                    "texts_analyzed": len(texts),
                    "total_words": sum(len(t.split()) for t in texts)
                }
            )
            
        except ImportError as e:
            return ToolResult(
                success=False,
                summary="NLP analysis unavailable - scikit-learn not installed",
                error=str(e)
            )
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"NLP analysis failed: {str(e)}",
                error=str(e)
            )
    
    def _tfidf_analysis(self, texts: List[str], top_k: int) -> Dict[str, Any]:
        """Extract keywords using TF-IDF."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # Initialize TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=top_k * 3,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,
            max_df=0.8
        )
        
        # Fit and transform
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # Get top keywords per document
        keywords_per_doc = []
        for doc_idx in range(len(texts)):
            doc_vector = tfidf_matrix[doc_idx].toarray()[0]
            top_indices = doc_vector.argsort()[-top_k:][::-1]
            doc_keywords = [
                {
                    "keyword": feature_names[idx],
                    "score": float(doc_vector[idx])
                }
                for idx in top_indices if doc_vector[idx] > 0
            ]
            keywords_per_doc.append(doc_keywords)
        
        # Get global top keywords (average across docs)
        avg_scores = tfidf_matrix.mean(axis=0).A1
        top_global_indices = avg_scores.argsort()[-top_k:][::-1]
        global_keywords = [
            {
                "keyword": feature_names[idx],
                "score": float(avg_scores[idx])
            }
            for idx in top_global_indices if avg_scores[idx] > 0
        ]
        
        return {
            "global_keywords": global_keywords,
            "keywords_per_document": keywords_per_doc,
            "total_features": len(feature_names)
        }
    
    def _keyword_extraction(self, texts: List[str], top_k: int) -> Dict[str, Any]:
        """Simple keyword extraction by frequency."""
        from collections import Counter
        import re
        
        # Common stop words
        stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        ])
        
        # Extract words
        all_words = []
        for text in texts:
            # Simple word tokenization
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            all_words.extend([w for w in words if w not in stop_words])
        
        # Count frequencies
        word_counts = Counter(all_words)
        top_keywords = [
            {"keyword": word, "count": count}
            for word, count in word_counts.most_common(top_k)
        ]
        
        return {
            "keywords": top_keywords,
            "total_unique_words": len(word_counts),
            "total_words": len(all_words)
        }
    
    def _theme_extraction(self, texts: List[str], top_k: int) -> Dict[str, Any]:
        """Extract common themes using keyword clustering."""
        # Use TF-IDF as base
        tfidf_result = self._tfidf_analysis(texts, top_k)
        keywords = [kw["keyword"] for kw in tfidf_result["global_keywords"]]
        
        # Simple theme grouping by word similarity
        themes = {}
        
        # Predefined theme categories (can be enhanced with clustering)
        theme_patterns = {
            "Product Features": ["feature", "function", "capability", "option", "tool"],
            "Performance": ["fast", "slow", "speed", "performance", "efficient", "quick"],
            "Usability": ["easy", "difficult", "simple", "complex", "intuitive", "user"],
            "Quality": ["quality", "good", "bad", "excellent", "poor", "best", "worst"],
            "Support": ["support", "help", "service", "customer", "response"],
            "Price": ["price", "cost", "expensive", "cheap", "value", "affordable"]
        }
        
        for theme_name, patterns in theme_patterns.items():
            matching_keywords = [
                kw for kw in keywords
                if any(pattern in kw.lower() for pattern in patterns)
            ]
            if matching_keywords:
                themes[theme_name] = matching_keywords
        
        # Uncategorized keywords
        categorized = set()
        for keywords_list in themes.values():
            categorized.update(keywords_list)
        
        uncategorized = [kw for kw in keywords if kw not in categorized]
        if uncategorized:
            themes["Other"] = uncategorized[:5]
        
        return {
            "themes": themes,
            "theme_count": len(themes)
        }
    
    def _ngram_analysis(self, texts: List[str], top_k: int) -> Dict[str, Any]:
        """Extract common n-grams (phrases)."""
        from collections import Counter
        import re
        
        # Extract bigrams and trigrams
        bigrams = []
        trigrams = []
        
        for text in texts:
            words = re.findall(r'\b[a-z]+\b', text.lower())
            
            # Bigrams
            for i in range(len(words) - 1):
                bigrams.append(f"{words[i]} {words[i+1]}")
            
            # Trigrams
            for i in range(len(words) - 2):
                trigrams.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        top_bigrams = [
            {"phrase": phrase, "count": count}
            for phrase, count in Counter(bigrams).most_common(top_k)
        ]
        
        top_trigrams = [
            {"phrase": phrase, "count": count}
            for phrase, count in Counter(trigrams).most_common(top_k)
        ]
        
        return {
            "top_bigrams": top_bigrams,
            "top_trigrams": top_trigrams,
            "total_bigrams": len(set(bigrams)),
            "total_trigrams": len(set(trigrams))
        }
    
    def _generate_summary(self, operation: str, result: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        if operation == "tfidf":
            keyword_count = len(result.get("global_keywords", []))
            if keyword_count > 0:
                top_keyword = result["global_keywords"][0]["keyword"]
                return f"Extracted {keyword_count} keywords, top: '{top_keyword}'"
            return "No keywords extracted"
        
        elif operation == "keywords":
            keyword_count = len(result.get("keywords", []))
            if keyword_count > 0:
                top_keyword = result["keywords"][0]["keyword"]
                count = result["keywords"][0]["count"]
                return f"Found {keyword_count} keywords, most common: '{top_keyword}' ({count}x)"
            return "No keywords found"
        
        elif operation == "themes":
            theme_count = result.get("theme_count", 0)
            themes = list(result.get("themes", {}).keys())
            if themes:
                return f"Identified {theme_count} themes: {', '.join(themes[:3])}"
            return "No themes identified"
        
        elif operation == "ngrams":
            bigram_count = len(result.get("top_bigrams", []))
            if bigram_count > 0:
                top_phrase = result["top_bigrams"][0]["phrase"]
                return f"Found {bigram_count} common phrases, top: '{top_phrase}'"
            return "No common phrases found"
        
        return "Analysis complete"

