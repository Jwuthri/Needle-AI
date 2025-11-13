"""
Generic dataset analysis service that accepts SQL queries from LLM.

The LLM provides SQL queries, we execute them, then analyze results
to detect column types and apply appropriate ML analysis.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field
from scipy import stats
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SeverityLevel(str, Enum):
    """Severity levels for gaps/issues."""
    high = "high"
    medium = "medium"
    low = "low"


class GapAnalysisItem(BaseModel):
    """Single gap/issue analysis item."""
    title: str = Field(..., description="Brief theme name (3-5 words)")
    description: str = Field(..., description="One sentence description of the issue")
    severity: SeverityLevel = Field(..., description="Severity level: high, medium, or low")


class GapAnalysisResponse(BaseModel):
    """Response containing list of gap analysis items."""
    gaps: List[GapAnalysisItem] = Field(..., description="List of identified gaps/issues")


class ClusterThemeItem(BaseModel):
    """Theme for a single cluster."""
    cluster_id: int = Field(..., description="Cluster ID")
    theme: str = Field(..., description="Concise theme name (2-4 words)")


class ClusterThemesResponse(BaseModel):
    """Response containing themes for all clusters."""
    themes: List[ClusterThemeItem] = Field(..., description="List of cluster themes")


class DatasetAnalysisService:
    """Service for analyzing any dataset using LLM-provided SQL queries."""
    
    def __init__(self, db: AsyncSession):
        """Initialize dataset analysis service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self._llm = None
        self._embedding_model = None
    
    def _get_llm(self):
        """Get LLM client for generating insights."""
        if self._llm is None:
            from llama_index.llms.openai import OpenAI
            api_key = settings.get_secret("openai_api_key")
            self._llm = OpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=api_key,
                max_tokens=1000
            )
        return self._llm
    
    def _get_embedding_model(self):
        """Get sentence transformer model for embeddings."""
        if self._embedding_model is None:
            # Use all-MiniLM-L6-v2: small, fast, 384 dimensions
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._embedding_model
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts using sentence-transformers.
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        model = self._get_embedding_model()
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings
    
    
    async def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dicts.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            List of row dictionaries
        """
        try:
            result = await self.db.execute(text(sql_query))
            rows = result.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for col in row.keys():
                    row_dict[col] = getattr(row, col)
                data.append(row_dict)
            
            return data
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    async def analyze_sentiment(
        self,
        user_id: str,
        sql_query: str,
        rating_column: str
    ) -> Dict[str, Any]:
        """Analyze sentiment from query results.
        
        Args:
            user_id: User ID
            sql_query: SQL query provided by LLM
            rating_column: Column name containing ratings/scores
        """
        data = await self.execute_query(sql_query)
        
        if not data:
            return {
                "user_id": user_id,
                "sentiment_analysis": {
                    "overall_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                },
            }
        
        ratings = [float(row.get(rating_column, 0)) for row in data if row.get(rating_column) is not None]
        
        if not ratings:
            return {
                "user_id": user_id,
                "sentiment_analysis": {
                    "overall_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                },
            }
        
        # Detect rating scale from actual data
        min_rating = min(ratings)
        max_rating = max(ratings)
        rating_range = max_rating - min_rating
        
        if rating_range == 0:
            # All same rating
            return {
                "user_id": user_id,
                "sentiment_analysis": {
                    "overall_sentiment": {"positive": 0, "neutral": 100, "negative": 0},
                },
            }
        
        # Categorize based on detected scale
        # Use percentiles: top 33% = positive, middle 33% = neutral, bottom 33% = negative
        sorted_ratings = sorted(ratings)
        n = len(sorted_ratings)
        
        # Calculate thresholds
        positive_threshold = sorted_ratings[int(n * 0.67)] if n > 0 else max_rating
        negative_threshold = sorted_ratings[int(n * 0.33)] if n > 0 else min_rating
        
        positive = sum(1 for r in ratings if r >= positive_threshold)
        negative = sum(1 for r in ratings if r <= negative_threshold)
        neutral = len(ratings) - positive - negative
        
        total = len(ratings)
        
        return {
            "user_id": user_id,
            "sentiment_analysis": {
                "overall_sentiment": {
                    "positive": round(positive * 100 / total, 1) if total > 0 else 0,
                    "neutral": round(neutral * 100 / total, 1) if total > 0 else 0,
                    "negative": round(negative * 100 / total, 1) if total > 0 else 0,
                },
            },
        }
    
    async def detect_trends(
        self,
        user_id: str,
        sql_query: str,
        date_column: str,
        metric_column: str,
        period: str = "month"
    ) -> Dict[str, Any]:
        """Detect trends from query results.
        
        Args:
            user_id: User ID
            sql_query: SQL query provided by LLM
            date_column: Column name containing dates
            metric_column: Column name containing metric values
            period: Time period grouping (day, week, month)
        """
        data = await self.execute_query(sql_query)
        
        if not data:
            return {
                "user_id": user_id,
                "trends": [],
                "overall_trend": "insufficient_data",
            }
        
        # Sort by date
        sorted_data = sorted(
            [row for row in data if row.get(date_column) and row.get(metric_column)],
            key=lambda x: x[date_column] if isinstance(x[date_column], datetime) else str(x[date_column])
        )
        
        if len(sorted_data) < 2:
            return {
                "user_id": user_id,
                "trends": [],
                "overall_trend": "insufficient_data",
            }
        
        trends = []
        for row in sorted_data:
            date_val = row[date_column]
            if isinstance(date_val, datetime):
                period_str = date_val.strftime("%Y-%m-%d")
            else:
                period_str = str(date_val)
            
            trends.append({
                "period": period_str,
                "average_rating": float(row[metric_column]),
                "value": float(row[metric_column]),
            })
        
        # Calculate trend
        values = [t["value"] for t in trends]
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        if slope > 0.01:
            overall_trend = "improving"
        elif slope < -0.01:
            overall_trend = "declining"
        else:
            overall_trend = "stable"
        
        r_squared = r_value ** 2
        if r_squared > 0.7:
            trend_strength = "strong"
        elif r_squared > 0.4:
            trend_strength = "moderate"
        else:
            trend_strength = "weak"
        
        return {
            "user_id": user_id,
            "time_field": date_column,
            "metric": metric_column,
            "trends": trends,
            "overall_trend": overall_trend,
            "trend_strength": trend_strength,
        }
    
    async def detect_product_gaps(
        self,
        user_id: str,
        sql_query: str,
        text_column: str,
        min_frequency: int = 3,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """Detect product gaps from query results.
        
        Args:
            user_id: User ID
            sql_query: SQL query provided by LLM
            text_column: Column name containing text content
            min_frequency: Minimum cluster size
            top_n: Number of top gaps to return
        """
        data = await self.execute_query(sql_query)
        
        if not data:
            return {
                "user_id": user_id,
                "gaps_detected": [],
                "total_gaps": 0,
                "analysis_date": datetime.utcnow().isoformat(),
            }
        
        texts = [str(row.get(text_column, "")) for row in data if row.get(text_column)]
        texts = [t for t in texts if len(t) > 20]
        
        if len(texts) < 5:
            return {
                "user_id": user_id,
                "gaps_detected": [],
                "total_gaps": 0,
                "analysis_date": datetime.utcnow().isoformat(),
            }
        
        # Get embeddings using sentence-transformers
        try:
            embeddings = self._get_embeddings(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "user_id": user_id,
                "gaps_detected": [],
                "total_gaps": 0,
                "analysis_date": datetime.utcnow().isoformat(),
            }
        
        # Use HDBSCAN - automatically finds number of clusters
        # min_cluster_size: minimum points to form a cluster
        # min_samples: conservative estimate for noise detection
        min_cluster_size = max(3, min_frequency)
        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=max(2, min_cluster_size - 1),
            metric='euclidean',
            cluster_selection_method='eom'
        )
        cluster_labels = clusterer.fit_predict(embeddings)
        
        # Get unique cluster IDs (excluding noise points labeled as -1)
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise label
        
        # Collect all clusters for batch analysis
        cluster_data_list = []
        for cluster_id in unique_clusters:
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            cluster_texts = [texts[idx] for idx in cluster_indices]
            
            if len(cluster_texts) < min_frequency:
                continue
            
            sample_size = min(5, len(cluster_texts))
            sample_texts = cluster_texts[:sample_size]
            
            cluster_data_list.append({
                "cluster_id": cluster_id,
                "total_records": len(cluster_texts),
                "sample_texts": sample_texts,
                "all_texts": cluster_texts,
            })
        
        if not cluster_data_list:
            return {
                "user_id": user_id,
                "gaps_detected": [],
                "total_gaps": 0,
                "analysis_date": datetime.utcnow().isoformat(),
            }
        
        # Use structured LLM output to analyze all clusters at once
        llm = self._get_llm()
        structured_llm = llm.as_structured_llm(output_cls=GapAnalysisResponse)
        
        prompt = f"""Analyze these {len(cluster_data_list)} groups of records and identify the common theme/issue for each group.

Groups to analyze:
{chr(10).join(f'{i+1}. Group {i+1} ({cd["total_records"]} records):{chr(10)}{chr(10).join(f"   - {text[:150]}" for text in cd["sample_texts"][:3])}{chr(10)}' for i, cd in enumerate(cluster_data_list))}

For each group, provide:
- title: Brief theme name (3-5 words)
- description: One sentence description of the issue
- severity: high, medium, or low

Return a list of gap analysis items, one for each group."""
        
        try:
            from llama_index.core.llms import ChatMessage
            messages = [
                ChatMessage(role="system", content="You are an expert at analyzing user feedback and identifying common issues and gaps."),
                ChatMessage(role="user", content=prompt)
            ]
            response = await structured_llm.achat(messages)
            result = response.raw
            
            # Extract gaps from structured response
            gaps = []
            for i, gap_item in enumerate(result.gaps):
                cluster_data = cluster_data_list[i]
                gaps.append({
                    "gap_id": f"gap-{len(gaps) + 1}",
                    "title": gap_item.title,
                    "description": gap_item.description,
                    "frequency": cluster_data["total_records"],
                    "severity": gap_item.severity.value,
                })
        except Exception as e:
            logger.warning(f"LLM failed to generate themes with structured output: {e}")
            # Fallback to individual analysis
            gaps = []
            for i, cluster_data in enumerate(cluster_data_list):
                gaps.append({
                    "gap_id": f"gap-{len(gaps) + 1}",
                    "title": f"Issue Cluster {i + 1}",
                    "description": f"Group of {cluster_data['total_records']} related issues",
                    "frequency": cluster_data["total_records"],
                    "severity": "medium",
                })
        
        gaps.sort(key=lambda x: x["frequency"], reverse=True)
        
        return {
            "user_id": user_id,
            "gaps_detected": gaps[:top_n],
            "total_gaps": len(gaps),
            "analysis_date": datetime.utcnow().isoformat(),
        }
    
    async def cluster_records(
        self,
        user_id: str,
        sql_query: str,
        text_column: str,
        min_cluster_size: int = 3
    ) -> Dict[str, Any]:
        """Cluster records from query results using HDBSCAN.
        
        Args:
            user_id: User ID
            sql_query: SQL query provided by LLM
            text_column: Column name containing text content
            min_cluster_size: Minimum number of points to form a cluster
        """
        data = await self.execute_query(sql_query)
        
        if not data:
            return {
                "user_id": user_id,
                "clusters": [],
                "total_records_clustered": 0,
            }
        
        texts = [str(row.get(text_column, "")) for row in data if row.get(text_column)]
        
        if len(texts) < min_cluster_size:
            return {
                "user_id": user_id,
                "clusters": [],
                "total_records_clustered": 0,
                "error": f"Not enough records (need at least {min_cluster_size})",
            }
        
        # Get embeddings using sentence-transformers
        try:
            embeddings = self._get_embeddings(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "user_id": user_id,
                "clusters": [],
                "total_records_clustered": 0,
            }
        
        # Use HDBSCAN - automatically finds number of clusters
        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=max(2, min_cluster_size - 1),
            metric='euclidean',
            cluster_selection_method='eom'
        )
        cluster_labels = clusterer.fit_predict(embeddings)
        
        # Get unique cluster IDs (excluding noise points labeled as -1)
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise label
        
        # Collect all clusters with examples
        cluster_data_list = []
        for cluster_id in unique_clusters:
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            cluster_texts = [texts[idx] for idx in cluster_indices]
            
            if not cluster_texts:
                continue
            
            # Select n examples from cluster
            sample_size = min(3, len(cluster_texts))
            sample_texts = cluster_texts[:sample_size]
            
            cluster_data_list.append({
                "cluster_id": int(cluster_id),
                "size": len(cluster_texts),
                "examples": sample_texts,
            })
        
        if not cluster_data_list:
            return {
                "user_id": user_id,
                "n_clusters": 0,
                "clusters": [],
                "total_records_clustered": len(texts),
                "noise_points": int(np.sum(cluster_labels == -1)),
            }
        
        # Batch all clusters and send to LLM in one call
        llm = self._get_llm()
        structured_llm = llm.as_structured_llm(output_cls=ClusterThemesResponse)
        
        prompt = f"""Analyze these {len(cluster_data_list)} clusters and generate a concise theme name (2-4 words) for each.

Clusters:
{cluster_data_list}

For each cluster, provide a concise theme name that captures the common topic or theme."""
        
        try:
            from llama_index.core.llms import ChatMessage
            messages = [
                ChatMessage(role="system", content="You are an expert at identifying themes and topics in grouped text data."),
                ChatMessage(role="user", content=prompt)
            ]
            response = await structured_llm.achat(messages)
            result = response.raw
            
            # Map themes to clusters
            theme_map = {theme.cluster_id: theme.theme for theme in result.themes}
            
            clusters = []
            for cluster_data in cluster_data_list:
                cluster_id = cluster_data["cluster_id"]
                theme = theme_map.get(cluster_id, f"Cluster {cluster_id}")
                
                clusters.append({
                    "cluster_id": cluster_id,
                    "theme": theme,
                    "size": cluster_data["size"],
                })
        except Exception as e:
            logger.warning(f"LLM failed to generate themes with structured output: {e}")
            # Fallback
            clusters = [
                {
                    "cluster_id": cd["cluster_id"],
                    "theme": f"Cluster {cd['cluster_id']}",
                    "size": cd["size"],
                }
                for cd in cluster_data_list
            ]
        
        clusters.sort(key=lambda x: x["size"], reverse=True)
        
        # Count noise points
        noise_count = int(np.sum(cluster_labels == -1))
        
        return {
            "user_id": user_id,
            "n_clusters": len(clusters),
            "clusters": clusters,
            "total_records_clustered": len(texts),
            "noise_points": noise_count,
        }
    
    async def extract_keywords(
        self,
        user_id: str,
        sql_query: str,
        text_column: str,
        top_n: int = 20
    ) -> Dict[str, Any]:
        """Extract keywords from query results.
        
        Args:
            user_id: User ID
            sql_query: SQL query provided by LLM
            text_column: Column name containing text content
            top_n: Number of keywords to extract
        """
        data = await self.execute_query(sql_query)
        
        if not data:
            return {
                "user_id": user_id,
                "top_keywords": [],
                "total_keywords": 0,
            }
        
        texts = [str(row.get(text_column, "")) for row in data if row.get(text_column)]
        
        if not texts:
            return {
                "user_id": user_id,
                "top_keywords": [],
                "total_keywords": 0,
            }
        
        # Extract keywords using TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=top_n * 2,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2
        )
        
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
        
        count_vectorizer = CountVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2
        )
        count_matrix = count_vectorizer.fit_transform(texts)
        count_feature_names = count_vectorizer.get_feature_names_out()
        frequencies = np.asarray(count_matrix.sum(axis=0)).flatten()
        
        keyword_data = []
        for i, keyword in enumerate(feature_names):
            try:
                freq_idx = list(count_feature_names).index(keyword)
                frequency = int(frequencies[freq_idx])
            except (ValueError, IndexError):
                frequency = 1
            
            keyword_data.append({
                "keyword": keyword,
                "frequency": frequency,
                "relevance_score": round(float(tfidf_scores[i]), 3),
            })
        
        keyword_data.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "user_id": user_id,
            "top_keywords": keyword_data[:top_n],
            "total_keywords": len(keyword_data),
        }
    
    async def semantic_search(
        self,
        user_id: str,
        table_name: str,
        query_text: str,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> Dict[str, Any]:
        """Perform semantic search using pgvector on embedding column.
        
        Args:
            user_id: User ID
            table_name: Table name to search (dynamic table name)
            query_text: Search query text
            limit: Maximum number of results
            min_similarity: Minimum similarity score (0-1)
            
        Returns:
            Dict with search results and similarity scores
        """
        try:
            # Generate embedding for query text using OpenAI
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.generate_embedding(query_text)
            
            if not query_embedding:
                return {
                    "user_id": user_id,
                    "query": query_text,
                    "results": [],
                    "count": 0,
                    "error": "Failed to generate query embedding",
                }
            
            # Convert embedding to string format for pgvector
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Build vector search query using pgvector
            # Using cosine distance (<=>) - lower is more similar
            # Calculate similarity as 1 - distance
            search_query = text(f"""
                SELECT 
                    *,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM "{table_name}"
                WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> :query_embedding::vector) >= :min_similarity
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
            """)
            
            result = await self.db.execute(
                search_query,
                {
                    "query_embedding": embedding_str,
                    "min_similarity": min_similarity,
                    "limit": limit
                }
            )
            rows = result.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for col in row.keys():
                    row_dict[col] = getattr(row, col)
                data.append(row_dict)
            
            return {
                "user_id": user_id,
                "query": query_text,
                "results": data,
                "count": len(data),
            }
            
        except Exception as e:
            logger.error(f"Error executing semantic search: {e}")
            raise ValueError(f"Failed to execute semantic search: {e}")

