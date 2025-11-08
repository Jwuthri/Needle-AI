"""
NLP analysis tools for LlamaIndex workflow.

These tools are designed to work with dataset names rather than actual data.
The data retrieval happens separately based on the dataset_name parameter.
"""

from typing import Any, Dict
from pydantic import BaseModel, Field
from llama_index.core.tools import FunctionTool

from app import get_logger

logger = get_logger(__name__)


class NLPToolCall(BaseModel):
    """Base model for NLP tool call parameters."""
    dataset_name: str = Field(..., description="Name of the dataset to analyze (e.g., 'user_reviews', 'feedback_data')")


class TFIDFParams(NLPToolCall):
    """Parameters for TF-IDF analysis."""
    text_column: str = Field(..., description="Column containing text data (e.g., 'review_text', 'feedback')")
    top_n: int = Field(default=10, description="Number of top terms to return")
    min_df: int = Field(default=2, description="Minimum document frequency")
    max_df: float = Field(default=0.8, description="Maximum document frequency (0.0-1.0)")
    ngram_range: list[int] = Field(default=[1, 2], description="N-gram range as [min, max], e.g., [1, 2] for unigrams and bigrams")


class ClusteringParams(NLPToolCall):
    """Parameters for clustering analysis."""
    text_column: str = Field(..., description="Column containing text data")
    num_clusters: int = Field(default=5, description="Number of clusters to create")
    method: str = Field(default="kmeans", description="Clustering method: kmeans, hierarchical, dbscan")
    id_column: str = Field(default="id", description="Column containing unique identifiers")
    include_metadata: list[str] = Field(default_factory=list, description="Additional columns to include (e.g., ['rating', 'date'])")


class SentimentParams(NLPToolCall):
    """Parameters for sentiment analysis."""
    text_column: str = Field(..., description="Column containing text data")
    rating_column: str = Field(default="rating", description="Column containing rating/score")
    include_distribution: bool = Field(default=True, description="Include rating distribution")
    group_by: str | None = Field(default=None, description="Column to group by (e.g., 'product', 'category')")


class FeatureParams(NLPToolCall):
    """Parameters for feature extraction."""
    text_column: str = Field(..., description="Column containing text data")
    min_frequency: int = Field(default=2, description="Minimum frequency for feature requests")
    rating_column: str = Field(default="rating", description="Column containing rating/score")
    id_column: str = Field(default="id", description="Column containing unique identifiers")
    extract_pain_points: bool = Field(default=True, description="Extract pain points in addition to features")
    extract_product_gaps: bool = Field(default=True, description="Extract product gaps")


def compute_tfidf_analysis(
    dataset_name: str,
    text_column: str,
    top_n: int = 10,
    min_df: int = 2,
    max_df: float = 0.8,
    ngram_range: list[int] = [1, 2]
) -> Dict[str, Any]:
    """
    Compute TF-IDF to find most important terms in text data.
    
    This tool identifies the most statistically significant terms in the dataset.
    Use this when you need to understand key topics or important words.
    
    Args:
        dataset_name: Name of the dataset to analyze (e.g., 'user_reviews', 'feedback_data')
        text_column: Column containing text data (e.g., 'review_text', 'feedback', 'comment')
        top_n: Number of top terms to return (default: 10)
        min_df: Minimum document frequency - ignore terms appearing in fewer docs (default: 2)
        max_df: Maximum document frequency - ignore terms appearing in more than this % (default: 0.8)
        ngram_range: N-gram range as [min, max] - e.g., [1, 2] for unigrams and bigrams (default: [1, 2])
    
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"TF-IDF tool called: dataset={dataset_name}, text_column={text_column}, top_n={top_n}")
    
    # Note: This returns metadata for now - actual execution happens in workflow
    # when data is available
    return {
        "tool": "compute_tfidf",
        "dataset_name": dataset_name,
        "parameters": {
            "text_column": text_column,
            "top_n": top_n,
            "min_df": min_df,
            "max_df": max_df,
            "ngram_range": tuple(ngram_range) if isinstance(ngram_range, list) else ngram_range,
        }
    }


def cluster_reviews_analysis(
    dataset_name: str,
    text_column: str,
    num_clusters: int = 5,
    method: str = "kmeans",
    id_column: str = "id",
    include_metadata: list[str] | None = None
) -> Dict[str, Any]:
    """
    Cluster similar text entries by theme or topic.
    
    This tool groups similar reviews/feedback into thematic clusters.
    Use this when you need to identify common themes or group similar feedback.
    
    Args:
        dataset_name: Name of the dataset to analyze
        text_column: Column containing text data to cluster
        num_clusters: Number of clusters to create (default: 5)
        method: Clustering method - 'kmeans', 'hierarchical', or 'dbscan' (default: 'kmeans')
        id_column: Column containing unique identifiers (default: 'id')
        include_metadata: Additional columns to include in results (e.g., ['rating', 'date', 'user_id'])
    
    Returns:
        Dictionary with tool call parameters for execution
    """
    if include_metadata is None:
        include_metadata = []
    
    logger.info(f"Clustering tool called: dataset={dataset_name}, text_column={text_column}, num_clusters={num_clusters}")
    
    return {
        "tool": "cluster_reviews",
        "dataset_name": dataset_name,
        "parameters": {
            "text_column": text_column,
            "num_clusters": num_clusters,
            "method": method,
            "id_column": id_column,
            "include_metadata": include_metadata,
        }
    }


def analyze_sentiment_analysis(
    dataset_name: str,
    text_column: str,
    rating_column: str = "rating",
    include_distribution: bool = True,
    group_by: str | None = None
) -> Dict[str, Any]:
    """
    Analyze sentiment and rating distribution in the data.
    
    This tool analyzes sentiment patterns and rating distributions.
    Use this when you need to understand overall sentiment or rating trends.
    
    Args:
        dataset_name: Name of the dataset to analyze
        text_column: Column containing text data for sentiment analysis
        rating_column: Column containing rating/score (default: 'rating')
        include_distribution: Include detailed rating distribution (default: True)
        group_by: Optional column to group results by (e.g., 'product', 'category', 'date')
    
    Returns:
        Dictionary with tool call parameters for execution
    """
    logger.info(f"Sentiment tool called: dataset={dataset_name}, text_column={text_column}, rating_column={rating_column}")
    
    return {
        "tool": "analyze_sentiment",
        "dataset_name": dataset_name,
        "parameters": {
            "text_column": text_column,
            "rating_column": rating_column,
            "include_distribution": include_distribution,
            "group_by": group_by,
        }
    }


def identify_features_analysis(
    dataset_name: str,
    text_column: str,
    min_frequency: int = 2,
    rating_column: str = "rating",
    id_column: str = "id",
    extract_pain_points: bool = True,
    extract_product_gaps: bool = True
) -> Dict[str, Any]:
    """
    Identify feature requests, pain points, and product gaps from text data.
    
    This tool extracts and categorizes feature requests and pain points.
    Use this when you need to find what users are asking for or complaining about.
    
    Args:
        dataset_name: Name of the dataset to analyze
        text_column: Column containing text data to analyze
        min_frequency: Minimum frequency for feature requests (default: 2)
        rating_column: Column containing rating/score for context (default: 'rating')
        id_column: Column containing unique identifiers (default: 'id')
        extract_pain_points: Extract pain points in addition to features (default: True)
        extract_product_gaps: Extract product gaps (default: True)
    
    Returns:
        Dictionary with tool call parameters for execution
    """
    logger.info(f"Feature identification tool called: dataset={dataset_name}, text_column={text_column}, min_frequency={min_frequency}")
    
    return {
        "tool": "identify_features",
        "dataset_name": dataset_name,
        "parameters": {
            "text_column": text_column,
            "min_frequency": min_frequency,
            "rating_column": rating_column,
            "id_column": id_column,
            "extract_pain_points": extract_pain_points,
            "extract_product_gaps": extract_product_gaps,
        }
    }


# ============================================================================
# NLP Implementation Functions
# ============================================================================

def execute_tfidf(data: list[dict], text_column: str, top_n: int = 10, min_df: int = 2, max_df: float = 0.8, ngram_range: tuple[int, int] = (1, 2)) -> Dict[str, Any]:
    """Execute TF-IDF analysis on the data."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    import pandas as pd
    
    df = pd.DataFrame(data)
    texts = df[text_column].fillna("").astype(str).tolist()
    
    vectorizer = TfidfVectorizer(
        max_features=top_n * 3,
        min_df=min_df,
        max_df=max_df,
        ngram_range=ngram_range,
        stop_words='english'
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()
    
    # Get average TF-IDF scores
    avg_scores = tfidf_matrix.mean(axis=0).A1
    top_indices = avg_scores.argsort()[-top_n:][::-1]
    
    top_terms = [
        {"term": feature_names[i], "score": round(float(avg_scores[i]), 5)}
        for i in top_indices
    ]
    
    return {
        "top_terms": top_terms,
        "total_documents": len(texts),
        "vocabulary_size": len(feature_names)
    }


def execute_clustering(data: list[dict], text_column: str, num_clusters: int = 5, method: str = "kmeans", id_column: str = "id", include_metadata: list[str] = None) -> Dict[str, Any]:
    """Execute clustering analysis on the data."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    import pandas as pd
    
    if include_metadata is None:
        include_metadata = []
    
    df = pd.DataFrame(data)
    texts = df[text_column].fillna("").astype(str).tolist()
    
    # Vectorize texts
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # Cluster
    if method == "kmeans":
        clusterer = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        labels = clusterer.fit_predict(tfidf_matrix)
    else:
        raise ValueError(f"Clustering method '{method}' not implemented")
    
    df['cluster'] = labels
    
    # Build cluster summaries
    clusters = []
    for cluster_id in range(num_clusters):
        cluster_df = df[df['cluster'] == cluster_id]
        cluster_texts = cluster_df[text_column].tolist()
        
        cluster_info = {
            "cluster_id": int(cluster_id),
            "size": len(cluster_df),
            "sample_texts": cluster_texts[:10],
        }
        
        # Add metadata if requested
        for meta_col in include_metadata:
            if meta_col in cluster_df.columns:
                cluster_info[f"{meta_col}_distribution"] = cluster_df[meta_col].value_counts().head(5).to_dict()
        
        clusters.append(cluster_info)
    
    return {
        "clusters": clusters,
        "num_clusters": num_clusters,
        "total_documents": len(df)
    }


def execute_sentiment_analysis(data: list[dict], text_column: str, rating_column: str = "rating", include_distribution: bool = True, group_by: str = None) -> Dict[str, Any]:
    """Execute sentiment analysis on the data."""
    import pandas as pd
    
    df = pd.DataFrame(data)
    
    result = {
        "total_reviews": len(df)
    }
    
    # Rating statistics
    if rating_column in df.columns:
        result["rating_stats"] = {
            "mean": float(df[rating_column].mean()),
            "median": float(df[rating_column].median()),
            "std": float(df[rating_column].std()),
            "min": float(df[rating_column].min()),
            "max": float(df[rating_column].max())
        }
        
        if include_distribution:
            result["rating_distribution"] = df[rating_column].value_counts().sort_index().to_dict()
        
        # Simple sentiment classification based on ratings
        df['sentiment'] = df[rating_column].apply(
            lambda x: 'positive' if x >= 4 else ('negative' if x <= 2 else 'neutral')
        )
        result["sentiment_distribution"] = df['sentiment'].value_counts().to_dict()
        
        # # Group by analysis
        # if group_by and group_by in df.columns:
        #     grouped = df.groupby(group_by)[rating_column].agg(['mean', 'count']).to_dict('index')
        #     result["grouped_analysis"] = grouped
    else:
        # No rating column - use TextBlob for sentiment analysis
        try:
            from textblob import TextBlob
            
            logger.info(f"No rating column found, using TextBlob for sentiment analysis")
            
            sentiments = []
            polarities = []
            
            for text in df[text_column].fillna("").astype(str):
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                polarities.append(polarity)
                
                # Classify sentiment based on polarity
                if polarity > 0.1:
                    sentiments.append('positive')
                elif polarity < -0.1:
                    sentiments.append('negative')
                else:
                    sentiments.append('neutral')
            
            df['sentiment'] = sentiments
            df['sentiment_score'] = polarities
            
            result["sentiment_stats"] = {
                "mean_polarity": float(pd.Series(polarities).mean()),
                "median_polarity": float(pd.Series(polarities).median()),
                "std_polarity": float(pd.Series(polarities).std()),
                "min_polarity": float(pd.Series(polarities).min()),
                "max_polarity": float(pd.Series(polarities).max())
            }
            
            result["sentiment_distribution"] = df['sentiment'].value_counts().to_dict()
            
            if include_distribution:
                # Bin sentiment scores for distribution
                df['sentiment_bin'] = pd.cut(df['sentiment_score'], 
                                            bins=[-1, -0.5, -0.1, 0.1, 0.5, 1],
                                            labels=['very_negative', 'negative', 'neutral', 'positive', 'very_positive'])
                result["sentiment_score_distribution"] = df['sentiment_bin'].value_counts().to_dict()
            
            # # Group by analysis with sentiment
            # if group_by and group_by in df.columns:
            #     grouped = df.groupby(group_by)['sentiment_score'].agg(['mean', 'count']).to_dict('index')
            #     result["grouped_analysis"] = grouped
                
        except ImportError:
            logger.warning("TextBlob not installed, skipping text-based sentiment analysis")
            result["warning"] = "No rating column and TextBlob not available for sentiment analysis"
    
    return result


def execute_feature_extraction(
    data: list[dict], 
    text_column: str, 
    min_frequency: int = 2, 
    rating_column: str = "rating", 
    id_column: str = "id", 
    extract_pain_points: bool = True, 
    extract_product_gaps: bool = True,
    similarity_threshold: float = 0.75
) -> dict:
    """Execute feature extraction using embeddings for semantic understanding (batch processing)."""
    import pandas as pd
    import numpy as np
    from collections import defaultdict
    
    df = pd.DataFrame(data)
    
    # Always try to use embeddings for best results
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        
        logger.info("Loading sentence transformer model for feature extraction")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings_available = True
    except ImportError:
        logger.warning("sentence-transformers not available, falling back to regex patterns")
        embeddings_available = False
    
    # Category definitions with semantic keywords
    categories_config = {
        'features': ['feature request', 'new functionality', 'add feature', 'enhancement', 'would like to see', 'need this feature', 'missing capability'],
        'pain_points': ['bug report', 'error', 'problem', 'issue', 'broken functionality', 'frustrating experience', 'annoying behavior'],
        'product_gaps': ['missing feature', 'lacking functionality', 'cannot do', 'no way to', 'limitation', 'unable to perform', 'does not support']
    }
    
    # Prepare data
    texts = df[text_column].fillna("").astype(str).tolist()
    valid_indices = [i for i, text in enumerate(texts) if len(text.strip()) >= 10]
    valid_texts = [texts[i] for i in valid_indices]
    
    if not valid_texts:
        return {"error": "No valid texts to analyze", "total_analyzed": 0}
    
    categorized = defaultdict(list)
    
    if embeddings_available:
        logger.info(f"Batch encoding {len(valid_texts)} texts")
        # BATCH ENCODE ALL TEXTS AT ONCE - much faster!
        text_embeddings = model.encode(valid_texts, batch_size=32, show_progress_bar=False)
        
        # Pre-compute category keyword embeddings once
        logger.info("Encoding category keywords")
        category_embeddings = {}
        for cat_name, keywords in categories_config.items():
            category_embeddings[cat_name] = model.encode(keywords, show_progress_bar=False)
        
        # Batch categorize all texts
        logger.info("Categorizing texts using batch similarity")
        for idx, text_idx in enumerate(valid_indices):
            text_emb = text_embeddings[idx:idx+1]
            row = df.iloc[text_idx]
            text = texts[text_idx]
            
            base_record = {
                "text": text[:200],
                "full_text": text,
                "rating": row.get(rating_column),
                id_column: row.get(id_column)
            }
            
            # Check similarity with each category
            for cat_name, cat_embs in category_embeddings.items():
                similarities = cosine_similarity(text_emb, cat_embs)[0]
                max_sim = np.max(similarities)
                
                if max_sim > similarity_threshold:
                    if cat_name == 'features':
                        categorized['features'].append(base_record.copy())
                    elif cat_name == 'pain_points' and extract_pain_points:
                        categorized['pain_points'].append(base_record.copy())
                    elif cat_name == 'product_gaps' and extract_product_gaps:
                        categorized['product_gaps'].append(base_record.copy())
    else:
        # Fallback to regex patterns (still batch process)
        import re
        patterns = {
            'features': re.compile(r'\b(need|want|wish|would like|should have|could use|please add|missing|add|feature|request)\b', re.IGNORECASE),
            'pain_points': re.compile(r'\b(problem|issue|bug|broken|doesn\'?t work|not working|fails?|crash|error|frustrat\w+|annoy\w+)\b', re.IGNORECASE),
            'product_gaps': re.compile(r'\b(lack|missing|no |without|doesn\'?t have|can\'?t|unable to|impossible to)\b', re.IGNORECASE)
        }
        
        for text_idx in valid_indices:
            row = df.iloc[text_idx]
            text = texts[text_idx]
            text_lower = text.lower()
            
            base_record = {
                "text": text[:200],
                "full_text": text,
                "rating": row.get(rating_column),
                id_column: row.get(id_column)
            }
            
            if patterns['features'].search(text_lower):
                categorized['features'].append(base_record.copy())
            if extract_pain_points and patterns['pain_points'].search(text_lower):
                categorized['pain_points'].append(base_record.copy())
            if extract_product_gaps and patterns['product_gaps'].search(text_lower):
                categorized['product_gaps'].append(base_record.copy())
    
    # Smart clustering using batch embeddings
    def cluster_items(items, min_freq):
        """Cluster similar items using batch embeddings."""
        if not items or len(items) < 2:
            return items[:10], len(items)
        
        if embeddings_available:
            # BATCH ENCODE all item texts at once
            texts = [item['full_text'] for item in items]
            logger.info(f"Batch encoding {len(texts)} items for clustering")
            embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
            
            # Compute similarity matrix in one go
            similarity_matrix = cosine_similarity(embeddings)
            
            # Simple clustering: group items with high similarity
            visited = set()
            clusters = []
            
            for i, item in enumerate(items):
                if i in visited:
                    continue
                
                cluster = [item]
                cluster_indices = [i]
                visited.add(i)
                
                # Find similar items using pre-computed similarity matrix
                for j in range(i + 1, len(items)):
                    if j not in visited and similarity_matrix[i][j] > similarity_threshold:
                        cluster.append(items[j])
                        cluster_indices.append(j)
                        visited.add(j)
                
                if len(cluster) >= min_freq:
                    # Representative: item with worst rating in cluster
                    rep = min(cluster, key=lambda x: x['rating'] if x['rating'] else float('inf'))
                    rep['frequency'] = len(cluster)
                    rep['cluster_size'] = len(cluster)
                    clusters.append(rep)
            
            clusters.sort(key=lambda x: (-x['frequency'], x['rating'] if x['rating'] else float('inf')))
            return clusters[:10], len(clusters)
        
        else:
            # Fallback: simple text prefix grouping
            import re
            groups = defaultdict(list)
            for item in items:
                key = re.sub(r'\s+', ' ', item['text'].lower()[:100]).strip()
                groups[key].append(item)
            
            frequent = []
            for group_items in groups.values():
                if len(group_items) >= min_freq:
                    best = min(group_items, key=lambda x: x['rating'] if x['rating'] else float('inf'))
                    best['frequency'] = len(group_items)
                    frequent.append(best)
            
            frequent.sort(key=lambda x: (-x['frequency'], x['rating'] if x['rating'] else float('inf')))
            return frequent[:10], len(groups)
    
    # Build results
    frequent_features, unique_features = cluster_items(categorized['features'], min_frequency)
    
    result = {
        "feature_requests": {
            "count": len(categorized['features']),
            "frequent": frequent_features,
            "total_unique": unique_features,
            "method": "embeddings" if embeddings_available else "regex"
        },
        "total_analyzed": len(df)
    }
    
    if extract_pain_points:
        pain_items = categorized['pain_points']
        pain_items.sort(key=lambda x: x['rating'] if x['rating'] else float('inf'))
        result["pain_points"] = {
            "count": len(pain_items),
            "samples": pain_items[:10]
        }
    
    if extract_product_gaps:
        gap_items = categorized['product_gaps']
        gap_items.sort(key=lambda x: x['rating'] if x['rating'] else float('inf'))
        result["product_gaps"] = {
            "count": len(gap_items),
            "samples": gap_items[:10]
        }
    
    return result


def execute_feature_extraction_old(
    data: list[dict], 
    text_column: str, 
    min_frequency: int = 2, 
    rating_column: str = "rating", 
    id_column: str = "id", 
    extract_pain_points: bool = True, 
    extract_product_gaps: bool = True
) -> dict[str, Any]:
    """Execute feature extraction to identify requests and pain points using smarter pattern matching."""
    import pandas as pd
    import re
    from collections import defaultdict
    
    df = pd.DataFrame(data)
    
    # Compile regex patterns once for better performance
    feature_pattern = re.compile(
        r'\b(need|want|wish|would like|should have|could use|please add|missing|add|feature|request)\b',
        re.IGNORECASE
    )
    pain_pattern = re.compile(
        r'\b(problem|issue|bug|broken|doesn\'?t work|not working|fails?|crash|error|frustrat\w+|annoy\w+)\b',
        re.IGNORECASE
    )
    gap_pattern = re.compile(
        r'\b(lack|missing|no |without|doesn\'?t have|can\'?t|unable to|impossible to)\b',
        re.IGNORECASE
    )
    
    # Use defaultdict for cleaner aggregation
    categories = defaultdict(list)
    
    # Single pass through data
    for idx, row in df.iterrows():
        text = str(row.get(text_column, "")).strip()
        if not text:
            continue
            
        text_lower = text.lower()
        rating = row.get(rating_column)
        record_id = row.get(id_column)
        
        # Create base record once
        base_record = {
            "text": text[:200],
            "rating": rating,
            id_column: record_id,
            "full_text": text  # Keep full text for better clustering
        }
        
        # Check patterns and categorize
        if feature_pattern.search(text_lower):
            categories['features'].append(base_record.copy())
        
        if extract_pain_points and pain_pattern.search(text_lower):
            categories['pain_points'].append(base_record.copy())
        
        if extract_product_gaps and gap_pattern.search(text_lower):
            categories['product_gaps'].append(base_record.copy())
    
    # Smart clustering by similar content (simple approach using first 100 chars)
    def cluster_similar(items, min_freq):
        """Group similar items and return frequent ones."""
        if not items:
            return [], 0
        
        # Group by normalized text prefix for basic similarity
        groups = defaultdict(list)
        for item in items:
            # Normalize: lowercase, remove extra spaces, take first 100 chars
            key = re.sub(r'\s+', ' ', item['text'].lower()[:100]).strip()
            groups[key].append(item)
        
        # Get groups meeting minimum frequency
        frequent = []
        for group_items in groups.values():
            if len(group_items) >= min_freq:
                # Take the item with the lowest rating (most critical)
                best_item = min(group_items, key=lambda x: x['rating'] if x['rating'] else float('inf'))
                best_item['frequency'] = len(group_items)
                frequent.append(best_item)
        
        # Sort by frequency and rating
        frequent.sort(key=lambda x: (-x['frequency'], x['rating'] if x['rating'] else float('inf')))
        
        return frequent[:10], len(groups)
    
    # Process features with clustering
    frequent_features, unique_features = cluster_similar(categories['features'], min_frequency)
    
    # Build result
    result = {
        "feature_requests": {
            "count": len(categories['features']),
            "frequent": frequent_features,
            "total_unique": unique_features
        },
        "total_analyzed": len(df)
    }
    
    if extract_pain_points:
        pain_items = categories['pain_points']
        # Sort by rating (worst first)
        pain_items.sort(key=lambda x: x['rating'] if x['rating'] else float('inf'))
        result["pain_points"] = {
            "count": len(pain_items),
            "samples": pain_items[:10]
        }
    
    if extract_product_gaps:
        gap_items = categories['product_gaps']
        gap_items.sort(key=lambda x: x['rating'] if x['rating'] else float('inf'))
        result["product_gaps"] = {
            "count": len(gap_items),
            "samples": gap_items[:10]
        }
    
    return result


# ============================================================================
# Create LlamaIndex FunctionTool instances
# ============================================================================
# Using function docstrings as descriptions (cleaner and avoids duplication)
compute_tfidf_tool = FunctionTool.from_defaults(
    fn=compute_tfidf_analysis,
    name="compute_tfidf"
)

cluster_reviews_tool = FunctionTool.from_defaults(
    fn=cluster_reviews_analysis,
    name="cluster_reviews"
)

analyze_sentiment_tool = FunctionTool.from_defaults(
    fn=analyze_sentiment_analysis,
    name="analyze_sentiment"
)

identify_features_tool = FunctionTool.from_defaults(
    fn=identify_features_analysis,
    name="identify_features"
)
