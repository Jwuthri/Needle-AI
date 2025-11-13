"""
Service for ML-based review analysis using sklearn.

Provides methods for:
- Sentiment analysis aggregation
- Clustering reviews
- Keyword extraction
- Gap detection
- Trend analysis

Uses pre-written SQL queries since we know the review table schema.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ReviewAnalysisService:
    """Service for analyzing reviews using ML techniques with pre-written queries."""
    
    def __init__(self, db: AsyncSession):
        """Initialize review analysis service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self._llm = None
    
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
    
    async def detect_product_gaps(
        self,
        user_id: str,
        table_name: str,
        min_frequency: int = 3,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """Detect product gaps using clustering + LLM for theme generation."""
        try:
            query = text(f"""
                SELECT id, text, rating, source, date, author
                FROM "{table_name}"
                WHERE rating <= 2 AND LENGTH(text) > 20
                ORDER BY date DESC
                LIMIT 500
            """)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return {
                    "user_id": user_id,
                    "gaps_detected": [],
                    "total_gaps": 0,
                    "analysis_date": datetime.utcnow().isoformat(),
                }
            
            reviews_data = [
                {
                    "id": row.id,
                    "text": row.text,
                    "rating": row.rating,
                    "source": row.source,
                    "date": row.date,
                    "author": row.author,
                }
                for row in rows
            ]
            
            texts = [r["text"] for r in reviews_data]
            
            if len(texts) < 5:
                return {
                    "user_id": user_id,
                    "gaps_detected": [],
                    "total_gaps": 0,
                    "analysis_date": datetime.utcnow().isoformat(),
                }
            
            vectorizer = TfidfVectorizer(
                max_features=50,
                ngram_range=(1, 2),
                stop_words='english',
                min_df=2
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
            except ValueError as e:
                logger.warning(f"Not enough data for gap detection: {e}")
                return {
                    "user_id": user_id,
                    "gaps_detected": [],
                    "total_gaps": 0,
                    "analysis_date": datetime.utcnow().isoformat(),
                }
            
            n_clusters = min(5, len(texts) // 3)
            if n_clusters < 2:
                n_clusters = 2
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            gaps = await self._generate_gaps_from_clusters(
                cluster_labels, reviews_data, n_clusters, min_frequency
            )
            
            return {
                "user_id": user_id,
                "gaps_detected": gaps[:top_n],
                "total_gaps": len(gaps),
                "analysis_date": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error detecting product gaps: {e}")
            raise
    
    async def _generate_gaps_from_clusters(
        self,
        cluster_labels: np.ndarray,
        reviews_data: List[Dict],
        n_clusters: int,
        min_frequency: int
    ) -> List[Dict[str, Any]]:
        """Generate gap themes from clusters using LLM."""
        gaps = []
        llm = self._get_llm()
        
        for cluster_id in range(n_clusters):
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            cluster_reviews = [reviews_data[idx] for idx in cluster_indices]
            
            if len(cluster_reviews) < min_frequency:
                continue
            
            sample_size = min(5, len(cluster_reviews))
            sample_reviews = cluster_reviews[:sample_size]
            sample_texts = [r["text"][:200] for r in sample_reviews]
            
            prompt = f"""Analyze these {len(cluster_reviews)} negative product reviews and identify the common theme/issue.

Example reviews from this group:
{chr(10).join(f'{i+1}. {text}' for i, text in enumerate(sample_texts))}

Respond in JSON format:
{{
  "title": "Brief theme name (3-5 words)",
  "description": "One sentence description of the issue",
  "severity": "high|medium|low"
}}"""
            
            try:
                response = await llm.acomplete(prompt)
                import json
                theme_data = json.loads(response.text.strip())
                
                sources = list(set(r["source"] for r in cluster_reviews if r.get("source")))
                
                gaps.append({
                    "gap_id": f"gap-{len(gaps) + 1}",
                    "title": theme_data.get("title", f"Issue Cluster {cluster_id + 1}"),
                    "description": theme_data.get("description", ""),
                    "frequency": len(cluster_reviews),
                    "severity": theme_data.get("severity", "medium"),
                    "sentiment": "negative",
                    "sources": sources,
                    "example_reviews": sample_texts,
                })
            except Exception as e:
                logger.warning(f"LLM failed to generate theme for cluster {cluster_id}: {e}")
                sources = list(set(r["source"] for r in cluster_reviews if r.get("source")))
                gaps.append({
                    "gap_id": f"gap-{len(gaps) + 1}",
                    "title": f"Issue Cluster {cluster_id + 1}",
                    "description": f"Group of {len(cluster_reviews)} related complaints",
                    "frequency": len(cluster_reviews),
                    "severity": "medium",
                    "sentiment": "negative",
                    "sources": sources,
                    "example_reviews": sample_texts,
                })
        
        return sorted(gaps, key=lambda x: x["frequency"], reverse=True)
    
    async def analyze_sentiment_patterns(
        self,
        user_id: str,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment patterns from reviews."""
        filters = filters or {}
        
        try:
            where_clauses = []
            if filters.get("source"):
                where_clauses.append(f"source = '{filters['source']}'")
            if filters.get("date_from"):
                where_clauses.append(f"date >= '{filters['date_from']}'")
            if filters.get("date_to"):
                where_clauses.append(f"date <= '{filters['date_to']}'")
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query = text(f"""
                SELECT 
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as neutral,
                    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative
                FROM "{table_name}"
                {where_sql}
            """)
            
            result = await self.db.execute(query)
            row = result.fetchone()
            
            total = row.total or 0
            if total == 0:
                return {
                    "user_id": user_id,
                    "filters_applied": filters,
                    "sentiment_analysis": {
                        "overall_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                        "by_source": {},
                        "by_rating": {},
                        "trend": "insufficient_data",
                    },
                }
            
            positive = row.positive or 0
            neutral = row.neutral or 0
            negative = row.negative or 0
            
            by_source_query = text(f"""
                SELECT 
                    source,
                    COUNT(*) as total,
                    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as positive,
                    SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as neutral,
                    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as negative
                FROM "{table_name}"
                {where_sql}
                GROUP BY source
            """)
            
            by_source_result = await self.db.execute(by_source_query)
            by_source_rows = by_source_result.fetchall()
            
            by_source = {}
            for row in by_source_rows:
                by_source[row.source] = {
                    "positive": round(row.positive, 1),
                    "neutral": round(row.neutral, 1),
                    "negative": round(row.negative, 1),
                }
            
            trend = await self._determine_sentiment_trend(table_name, where_sql)
            positive_themes, negative_themes = await self._extract_sentiment_themes(
                table_name, where_sql
            )
            
            return {
                "user_id": user_id,
                "filters_applied": filters,
                "sentiment_analysis": {
                    "overall_sentiment": {
                        "positive": round(positive * 100 / total, 1),
                        "neutral": round(neutral * 100 / total, 1),
                        "negative": round(negative * 100 / total, 1),
                    },
                    "by_source": by_source,
                    "by_rating": {
                        "1": {"sentiment": "negative", "count": await self._count_by_rating(table_name, 1, where_sql)},
                        "2": {"sentiment": "negative", "count": await self._count_by_rating(table_name, 2, where_sql)},
                        "3": {"sentiment": "neutral", "count": await self._count_by_rating(table_name, 3, where_sql)},
                        "4": {"sentiment": "positive", "count": await self._count_by_rating(table_name, 4, where_sql)},
                        "5": {"sentiment": "positive", "count": await self._count_by_rating(table_name, 5, where_sql)},
                    },
                    "trend": trend,
                    "key_positive_themes": positive_themes,
                    "key_negative_themes": negative_themes,
                },
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment patterns: {e}")
            raise
    
    async def _determine_sentiment_trend(self, table_name: str, where_sql: str) -> str:
        """Determine if sentiment is improving or declining."""
        try:
            query = text(f"""
                WITH ordered_reviews AS (
                    SELECT rating, ROW_NUMBER() OVER (ORDER BY date) as row_num,
                           COUNT(*) OVER () as total_count
                    FROM "{table_name}"
                    {where_sql}
                )
                SELECT 
                    AVG(CASE WHEN row_num <= total_count/2 THEN rating ELSE NULL END) as first_half_avg,
                    AVG(CASE WHEN row_num > total_count/2 THEN rating ELSE NULL END) as second_half_avg
                FROM ordered_reviews
            """)
            
            result = await self.db.execute(query)
            row = result.fetchone()
            
            if not row or row.first_half_avg is None or row.second_half_avg is None:
                return "stable"
            
            diff = row.second_half_avg - row.first_half_avg
            
            if diff > 0.3:
                return "improving"
            elif diff < -0.3:
                return "declining"
            else:
                return "stable"
                
        except Exception as e:
            logger.warning(f"Error determining sentiment trend: {e}")
            return "unknown"
    
    async def _extract_sentiment_themes(
        self, table_name: str, where_sql: str
    ) -> Tuple[List[str], List[str]]:
        """Extract key positive and negative themes using LLM."""
        try:
            pos_query = text(f"""
                SELECT text FROM "{table_name}"
                {where_sql}
                {"AND" if where_sql else "WHERE"} rating >= 4
                ORDER BY RANDOM()
                LIMIT 10
            """)
            pos_result = await self.db.execute(pos_query)
            pos_reviews = [row.text[:150] for row in pos_result.fetchall()]
            
            neg_query = text(f"""
                SELECT text FROM "{table_name}"
                {where_sql}
                {"AND" if where_sql else "WHERE"} rating <= 2
                ORDER BY RANDOM()
                LIMIT 10
            """)
            neg_result = await self.db.execute(neg_query)
            neg_reviews = [row.text[:150] for row in neg_result.fetchall()]
            
            if not pos_reviews and not neg_reviews:
                return [], []
            
            llm = self._get_llm()
            
            positive_themes = []
            if pos_reviews:
                prompt = f"""Extract 3-5 key themes from these positive reviews:
{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(pos_reviews[:5]))}

Return only a JSON array of theme strings: ["theme1", "theme2", ...]"""
                
                try:
                    response = await llm.acomplete(prompt)
                    import json
                    positive_themes = json.loads(response.text.strip())
                except:
                    positive_themes = ["positive feedback"]
            
            negative_themes = []
            if neg_reviews:
                prompt = f"""Extract 3-5 key themes from these negative reviews:
{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(neg_reviews[:5]))}

Return only a JSON array of theme strings: ["theme1", "theme2", ...]"""
                
                try:
                    response = await llm.acomplete(prompt)
                    import json
                    negative_themes = json.loads(response.text.strip())
                except:
                    negative_themes = ["complaints"]
            
            return positive_themes[:5], negative_themes[:5]
            
        except Exception as e:
            logger.warning(f"Failed to extract sentiment themes: {e}")
            return [], []
    
    async def _count_by_rating(self, table_name: str, rating: int, where_sql: str) -> int:
        """Count reviews by rating."""
        query = text(f"""
            SELECT COUNT(*) as count
            FROM "{table_name}"
            {where_sql}
            {"AND" if where_sql else "WHERE"} rating = {rating}
        """)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def detect_trends(
        self,
        user_id: str,
        table_name: str,
        time_field: str = "date",
        metric: str = "rating",
        period: str = "month"
    ) -> Dict[str, Any]:
        """Detect temporal trends in reviews."""
        try:
            date_trunc_map = {"day": "day", "week": "week", "month": "month"}
            trunc = date_trunc_map.get(period, "month")
            
            query = text(f"""
                SELECT 
                    DATE_TRUNC('{trunc}', {time_field}) as period,
                    AVG(rating) as average_rating,
                    COUNT(*) as review_count,
                    AVG(CASE 
                        WHEN rating >= 4 THEN 1.0
                        WHEN rating = 3 THEN 0.0
                        ELSE -1.0
                    END) as sentiment_score
                FROM "{table_name}"
                WHERE {time_field} IS NOT NULL
                GROUP BY period
                ORDER BY period
            """)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return {
                    "user_id": user_id,
                    "time_field": time_field,
                    "metric": metric,
                    "trends": [],
                    "overall_trend": "insufficient_data",
                    "trend_strength": "none",
                    "insights": ["Not enough data to detect trends"],
                }
            
            trends = []
            for row in rows:
                trends.append({
                    "period": row.period.strftime("%Y-%m-%d") if row.period else "unknown",
                    "average_rating": round(float(row.average_rating), 2) if row.average_rating else 0,
                    "review_count": row.review_count,
                    "sentiment_score": round(float(row.sentiment_score), 2) if row.sentiment_score else 0,
                })
            
            if len(trends) >= 2:
                ratings = [t["average_rating"] for t in trends]
                x = np.arange(len(ratings))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, ratings)
                
                if slope > 0.1:
                    overall_trend = "improving"
                elif slope < -0.1:
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
            else:
                overall_trend = "insufficient_data"
                trend_strength = "none"
            
            insights = self._generate_trend_insights(trends, overall_trend)
            
            return {
                "user_id": user_id,
                "time_field": time_field,
                "metric": metric,
                "trends": trends,
                "overall_trend": overall_trend,
                "trend_strength": trend_strength,
                "insights": insights,
            }
            
        except Exception as e:
            logger.error(f"Error detecting trends: {e}")
            raise
    
    def _generate_trend_insights(self, trends: List[Dict], overall_trend: str) -> List[str]:
        """Generate human-readable insights from trend data."""
        insights = []
        
        if not trends:
            return ["No trend data available"]
        
        if len(trends) >= 2:
            first_rating = trends[0]["average_rating"]
            last_rating = trends[-1]["average_rating"]
            rating_change = last_rating - first_rating
            
            if rating_change > 0.3:
                insights.append(f"Average rating increased from {first_rating:.1f} to {last_rating:.1f}")
            elif rating_change < -0.3:
                insights.append(f"Average rating decreased from {first_rating:.1f} to {last_rating:.1f}")
            
            first_volume = trends[0]["review_count"]
            last_volume = trends[-1]["review_count"]
            volume_change_pct = ((last_volume - first_volume) / first_volume * 100) if first_volume > 0 else 0
            
            if volume_change_pct > 20:
                insights.append(f"Review volume increased by {volume_change_pct:.0f}%")
            elif volume_change_pct < -20:
                insights.append(f"Review volume decreased by {abs(volume_change_pct):.0f}%")
            
            first_sentiment = trends[0]["sentiment_score"]
            last_sentiment = trends[-1]["sentiment_score"]
            if last_sentiment < first_sentiment - 0.2:
                insights.append("Negative sentiment increased over time")
            elif last_sentiment > first_sentiment + 0.2:
                insights.append("Positive sentiment increased over time")
        
        if not insights:
            insights.append("Ratings remain relatively stable over time")
        
        return insights
    
    async def cluster_reviews(
        self,
        user_id: str,
        table_name: str,
        n_clusters: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Cluster similar reviews to identify themes."""
        filters = filters or {}
        
        try:
            where_clauses = []
            if filters.get("source"):
                where_clauses.append(f"source = '{filters['source']}'")
            if filters.get("min_length"):
                where_clauses.append(f"LENGTH(text) >= {filters['min_length']}")
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query = text(f"""
                SELECT id, text, rating, source
                FROM "{table_name}"
                {where_sql}
                ORDER BY date DESC
                LIMIT 500
            """)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            if len(rows) < n_clusters:
                logger.warning(f"Not enough reviews ({len(rows)}) for {n_clusters} clusters")
                n_clusters = max(2, len(rows) // 2)
            
            texts = [row.text for row in rows]
            reviews_data = [
                {"id": row.id, "text": row.text, "rating": row.rating, "source": row.source}
                for row in rows
            ]
            
            vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 2),
                stop_words='english',
                min_df=2
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
            except ValueError as e:
                logger.warning(f"TF-IDF failed for clustering: {e}")
                return {
                    "user_id": user_id,
                    "n_clusters": n_clusters,
                    "clusters": [],
                    "total_reviews_clustered": 0,
                }
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            clusters = []
            feature_names = vectorizer.get_feature_names_out()
            
            for i in range(n_clusters):
                cluster_indices = np.where(cluster_labels == i)[0]
                cluster_reviews = [reviews_data[idx] for idx in cluster_indices]
                
                if not cluster_reviews:
                    continue
                
                cluster_center = kmeans.cluster_centers_[i]
                top_keyword_indices = cluster_center.argsort()[-5:][::-1]
                keywords = [feature_names[idx] for idx in top_keyword_indices]
                
                avg_rating = np.mean([r["rating"] for r in cluster_reviews if r.get("rating")])
                
                cluster_vectors = tfidf_matrix[cluster_indices]
                distances = np.linalg.norm(cluster_vectors.toarray() - cluster_center, axis=1)
                representative_idx = cluster_indices[distances.argmin()]
                representative_review = reviews_data[representative_idx]["text"][:200]
                
                theme = await self._generate_cluster_theme(cluster_reviews, keywords)
                
                clusters.append({
                    "cluster_id": i,
                    "theme": theme,
                    "size": len(cluster_reviews),
                    "keywords": keywords,
                    "average_rating": round(float(avg_rating), 2),
                    "representative_review": representative_review,
                })
            
            clusters.sort(key=lambda x: x["size"], reverse=True)
            
            return {
                "user_id": user_id,
                "n_clusters": n_clusters,
                "clusters": clusters,
                "total_reviews_clustered": len(rows),
            }
            
        except Exception as e:
            logger.error(f"Error clustering reviews: {e}")
            raise
    
    async def _generate_cluster_theme(self, cluster_reviews: List[Dict], keywords: List[str]) -> str:
        """Generate theme name for a cluster using LLM."""
        try:
            llm = self._get_llm()
            sample_size = min(3, len(cluster_reviews))
            sample_texts = [r["text"][:150] for r in cluster_reviews[:sample_size]]
            
            prompt = f"""Generate a concise theme name (2-4 words) for this group of reviews.

Top keywords: {', '.join(keywords[:5])}

Sample reviews:
{chr(10).join(f'{i+1}. {text}' for i, text in enumerate(sample_texts))}

Return only the theme name, nothing else."""
            
            response = await llm.acomplete(prompt)
            theme = response.text.strip().strip('"\'')
            return theme if theme else " ".join(keywords[:2]).title()
            
        except Exception as e:
            logger.warning(f"LLM failed to generate theme name: {e}")
            return " ".join(keywords[:2]).title()
    
    async def extract_keywords(
        self,
        user_id: str,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        top_n: int = 20
    ) -> Dict[str, Any]:
        """Extract top keywords from reviews."""
        filters = filters or {}
        
        try:
            where_clauses = []
            if filters.get("source"):
                where_clauses.append(f"source = '{filters['source']}'")
            if filters.get("min_rating"):
                where_clauses.append(f"rating >= {filters['min_rating']}")
            if filters.get("max_rating"):
                where_clauses.append(f"rating <= {filters['max_rating']}")
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query = text(f"""
                SELECT text
                FROM "{table_name}"
                {where_sql}
                LIMIT 1000
            """)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return {
                    "user_id": user_id,
                    "top_keywords": [],
                    "total_keywords": 0,
                }
            
            texts = [row.text for row in rows]
            
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
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            raise

