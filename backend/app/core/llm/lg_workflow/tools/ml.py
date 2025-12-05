from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd
from textblob import TextBlob
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import hdbscan
import numpy as np
import os
import asyncio
from pydantic import BaseModel, Field
from typing import List

@tool
async def sentiment_analysis_tool(table_name: str, text_column: str, user_id: str) -> str:
    """
    Analyzes the sentiment of a text column in a dataset.
    Returns a comprehensive sentiment analysis report with:
    - Overall sentiment distribution (positive/negative/neutral)
    - Statistical summary (mean, std, min, max polarity)
    - Subjectivity analysis
    - Most positive and negative examples
    Adds sentiment_polarity, sentiment_subjectivity, and sentiment_label columns to the dataset.
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if text_column not in df.columns:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Column '{text_column}' not found. Available columns: {available_cols}"
    
    def _analyze():
        result_df = df.copy()
        
        # Calculate sentiment scores for all rows
        sentiments = []
        for text in result_df[text_column]:
            try:
                text_str = str(text) if text is not None else ""
                blob = TextBlob(text_str)
                sentiments.append({
                    'polarity': blob.sentiment.polarity,
                    'subjectivity': blob.sentiment.subjectivity
                })
            except Exception:
                sentiments.append({'polarity': 0.0, 'subjectivity': 0.0})
        
        # Add sentiment columns
        result_df['sentiment_polarity'] = [s['polarity'] for s in sentiments]
        result_df['sentiment_subjectivity'] = [s['subjectivity'] for s in sentiments]
        
        # Classify sentiment
        def classify_sentiment(polarity):
            if polarity > 0.1:
                return 'Positive'
            elif polarity < -0.1:
                return 'Negative'
            else:
                return 'Neutral'
        
        result_df['sentiment_label'] = result_df['sentiment_polarity'].apply(classify_sentiment)
        
        # Build comprehensive report
        report = []
        report.append(f"# Sentiment Analysis Report: '{table_name}'")
        report.append(f"\n**Text Column:** {text_column}")
        report.append(f"**Total Records Analyzed:** {len(result_df)}\n")
        
        # Overall sentiment distribution
        report.append("## 1. Overall Sentiment Distribution")
        sentiment_counts = result_df['sentiment_label'].value_counts()
        total = len(result_df)
        
        report.append("\n**Sentiment Breakdown:**\n")
        for sentiment in ['Positive', 'Neutral', 'Negative']:
            count = sentiment_counts.get(sentiment, 0)
            pct = (count / total) * 100
            emoji = "😊" if sentiment == 'Positive' else "😐" if sentiment == 'Neutral' else "😞"
            report.append(f"- {emoji} **{sentiment}:** {count} ({pct:.1f}%)")
        
        # Sentiment statistics
        report.append("\n## 2. Sentiment Statistics")
        polarity_mean = result_df['sentiment_polarity'].mean()
        polarity_std = result_df['sentiment_polarity'].std()
        polarity_min = result_df['sentiment_polarity'].min()
        polarity_max = result_df['sentiment_polarity'].max()
        subjectivity_mean = result_df['sentiment_subjectivity'].mean()
        
        report.append(f"\n**Polarity Scores** (Range: -1.0 to +1.0):")
        report.append(f"- Mean: {polarity_mean:.3f}")
        report.append(f"- Std Dev: {polarity_std:.3f}")
        report.append(f"- Min: {polarity_min:.3f}")
        report.append(f"- Max: {polarity_max:.3f}")
        
        report.append(f"\n**Subjectivity Scores** (Range: 0.0 to 1.0):")
        report.append(f"- Mean: {subjectivity_mean:.3f}")
        report.append(f"- This indicates the text is {'mostly subjective' if subjectivity_mean > 0.5 else 'mostly objective'}")
        
        # Sentiment insights
        report.append("\n## 3. Sentiment Insights")
        if polarity_mean > 0.2:
            report.append("- 📈 **Overall Positive Sentiment**: The dataset shows predominantly positive sentiment")
        elif polarity_mean < -0.2:
            report.append("- 📉 **Overall Negative Sentiment**: The dataset shows predominantly negative sentiment")
        else:
            report.append("- ⚖️ **Balanced Sentiment**: The dataset shows balanced or neutral sentiment")
        
        if polarity_std > 0.4:
            report.append("- 🎭 **High Variation**: Sentiment varies significantly across records")
        else:
            report.append("- 📊 **Low Variation**: Sentiment is relatively consistent across records")
        
        # Most positive examples
        report.append("\n## 4. Most Positive Examples")
        most_positive = result_df.nlargest(min(3, len(result_df)), 'sentiment_polarity')
        report.append("\n**Top 3 Most Positive:**\n")
        
        for idx, (_, row) in enumerate(most_positive.iterrows(), 1):
            report.append(f"**{idx}. Polarity: {row['sentiment_polarity']:.3f}**")
            text_preview = str(row[text_column])[:200]
            if len(str(row[text_column])) > 200:
                text_preview += "..."
            report.append(f"   - {text_preview}")
            report.append("")
        
        # Most negative examples
        report.append("## 5. Most Negative Examples")
        most_negative = result_df.nsmallest(min(3, len(result_df)), 'sentiment_polarity')
        report.append("\n**Top 3 Most Negative:**\n")
        
        for idx, (_, row) in enumerate(most_negative.iterrows(), 1):
            report.append(f"**{idx}. Polarity: {row['sentiment_polarity']:.3f}**")
            text_preview = str(row[text_column])[:200]
            if len(str(row[text_column])) > 200:
                text_preview += "..."
            report.append(f"   - {text_preview}")
            report.append("")
        
        # Note about data update
        report.append("## 6. Data Updated")
        report.append(f"\n✅ Added 3 new columns to dataset '{table_name}':")
        report.append("- `sentiment_polarity`: Sentiment score from -1.0 (negative) to +1.0 (positive)")
        report.append("- `sentiment_subjectivity`: Subjectivity score from 0.0 (objective) to 1.0 (subjective)")
        report.append("- `sentiment_label`: Categorical label (Positive, Neutral, or Negative)")
        
        return result_df, "\n".join(report)

    loop = asyncio.get_running_loop()
    try:
        result_df, report = await loop.run_in_executor(None, _analyze)
        success = await dm.update_dataset(table_name, result_df, user_id)
        if not success:
            return f"Error: Failed to update dataset '{table_name}' with sentiment data."
        return report
    except Exception as e:
        return f"Error performing sentiment analysis: {str(e)}"

@tool
async def embedding_tool(table_name: str, text_column: str, user_id: str) -> str:
    """
    Generates vector embeddings for a text column using OpenAI's embedding model.
    Adds a new column 'embedding' to the dataset.
    WARNING: This can be slow and cost money for large datasets.
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if text_column not in df.columns:
        return f"Error: Column {text_column} not found."
        
    try:
        embeddings_model = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        texts = df[text_column].astype(str).tolist()
        
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, embeddings_model.embed_documents, texts)
        
        result_df = df.copy()
        result_df['__embedding__'] = embeddings
        
        success = await dm.update_dataset(table_name, result_df, user_id)
        if success:
            return f"Successfully added 'embedding' column to dataset '{table_name}'."
        return f"Error: Failed to update dataset '{table_name}'."
    except Exception as e:
        return f"Error generating embeddings: {str(e)}"

@tool
async def linear_regression_tool(table_name: str, target_column: str, feature_columns: list[str], user_id: str) -> str:
    """
    Performs a simple linear regression to predict a target column based on feature columns.
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    missing_cols = [col for col in feature_columns + [target_column] if col not in df.columns]
    if missing_cols:
        return f"Error: Columns {missing_cols} not found in dataset."
        
    def _regress():
        # Drop NaNs for simplicity
        data = df[feature_columns + [target_column]].dropna()
        
        X = data[feature_columns]
        y = data[target_column]
        
        model = LinearRegression()
        model.fit(X, y)
        
        predictions = model.predict(X)
        r2 = r2_score(y, predictions)
        mse = mean_squared_error(y, predictions)
        
        coef_info = "\n".join([f"{feat}: {coef:.4f}" for feat, coef in zip(feature_columns, model.coef_)])
        
        return (f"Linear Regression Results:\n"
                f"Target: {target_column}\n"
                f"Features: {feature_columns}\n"
                f"R2 Score: {r2:.4f}\n"
                f"MSE: {mse:.4f}\n"
                f"Coefficients:\n{coef_info}")

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _regress)
    except Exception as e:
        return f"Error performing regression: {str(e)}"

@tool
async def trend_analysis_tool(table_name: str, date_column: str, value_column: str, user_id: str, period: str = 'M') -> str:
    """
    Analyzes trends in a value column over time.
    Returns a comprehensive trend analysis report with:
    - Trend direction (increasing/decreasing/stable)
    - Statistical summary (first, last, mean, std, min, max)
    - Percentage change over time
    - Volatility detection
    - Recent time series data
    
    Aggregates data by the specified period:
    - D: Daily
    - W: Weekly  
    - M: Monthly (default)
    - Q: Quarterly
    - Y: Yearly
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if date_column not in df.columns or value_column not in df.columns:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Columns '{date_column}' or '{value_column}' not found. Available columns: {available_cols}"

    def _analyze_trend():
        data = df.copy()
        
        # Convert date column to datetime
        try:
            data[date_column] = pd.to_datetime(data[date_column])
        except Exception as e:
            return None, None, f"Error: Could not convert '{date_column}' to datetime: {str(e)}"
        
        # Remove rows with invalid dates or values
        data = data.dropna(subset=[date_column, value_column])
        
        if data.empty:
            return None, None, "Error: No valid data after cleaning."
        
        # Sort by date
        data = data.set_index(date_column).sort_index()
        
        # Determine time range for context
        time_range_days = (data.index.max() - data.index.min()).days
        
        # Resample by period
        period_names = {
            'D': 'Daily', 'W': 'Weekly', 'M': 'Monthly', 
            'Q': 'Quarterly', 'Y': 'Yearly'
        }
        period_name = period_names.get(period, period)
        
        resampled = data[value_column].resample(period).mean().dropna()
        
        if len(resampled) < 2:
            return None, None, "Error: Not enough data points for trend analysis (need at least 2)."
        
        # Calculate statistics
        values = resampled.values
        first_value = values[0]
        last_value = values[-1]
        mean_value = np.mean(values)
        std_value = np.std(values)
        min_value = np.min(values)
        max_value = np.max(values)
        
        # Calculate trend (linear regression)
        x = np.arange(len(resampled)).reshape(-1, 1)
        y = resampled.values
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(x, y)
        slope = model.coef_[0]
        
        # Calculate percentage change
        if first_value != 0:
            pct_change = ((last_value - first_value) / abs(first_value)) * 100
        else:
            pct_change = 0 if last_value == 0 else float('inf')
        
        # Determine trend direction
        if abs(pct_change) < 5:
            trend_direction = "📊 Stable"
            trend_desc = "stable"
        elif pct_change > 0:
            trend_direction = "📈 Increasing"
            trend_desc = "increasing"
        else:
            trend_direction = "📉 Decreasing"
            trend_desc = "decreasing"
        
        # Build comprehensive report
        report = []
        report.append(f"# Trend Analysis Report: '{table_name}'")
        report.append(f"\n**Date Column:** {date_column}")
        report.append(f"**Value Column:** {value_column}")
        report.append(f"**Time Range:** {data.index.min().strftime('%Y-%m-%d')} to {data.index.max().strftime('%Y-%m-%d')} ({time_range_days} days)")
        report.append(f"**Time Grouping:** {period_name} ({period})")
        report.append(f"**Data Points:** {len(resampled)}\n")
        
        # Trend direction
        report.append("## 1. Trend Direction")
        report.append(f"\n**Overall Trend:** {trend_direction}")
        report.append(f"**Trend Description:** The {value_column} shows a {trend_desc} trend over time")
        report.append(f"**Overall Change:** {pct_change:+.1f}%")
        report.append(f"**Slope:** {slope:.4f} per {period_name.lower()}")
        
        # Summary statistics
        report.append("\n## 2. Summary Statistics")
        report.append(f"\n**Time Series Statistics:**")
        report.append(f"- First Value: {first_value:.2f}")
        report.append(f"- Last Value: {last_value:.2f}")
        report.append(f"- Mean: {mean_value:.2f}")
        report.append(f"- Std Dev: {std_value:.2f}")
        report.append(f"- Min: {min_value:.2f}")
        report.append(f"- Max: {max_value:.2f}")
        report.append(f"- Range: {max_value - min_value:.2f}")
        
        # Volatility analysis
        report.append("\n## 3. Volatility Analysis")
        cv = (std_value / mean_value) * 100 if mean_value != 0 else 0
        
        if cv > 30:
            volatility_level = "🔴 High"
            volatility_desc = "Values fluctuate significantly over time"
        elif cv > 15:
            volatility_level = "🟡 Moderate"
            volatility_desc = "Values show some variation over time"
        else:
            volatility_level = "🟢 Low"
            volatility_desc = "Values are relatively stable over time"
        
        report.append(f"\n**Volatility Level:** {volatility_level}")
        report.append(f"**Coefficient of Variation:** {cv:.1f}%")
        report.append(f"- {volatility_desc}")
        
        # Recent time series data
        report.append(f"\n## 4. Recent {period_name} Values")
        report.append(f"\n**Last 10 {period_name} Periods:**\n")
        
        recent_data = resampled.tail(10).reset_index()
        recent_data.columns = ['Time Period', value_column]
        recent_data['Time Period'] = recent_data['Time Period'].dt.strftime('%Y-%m-%d')
        recent_data[value_column] = recent_data[value_column].round(2)
        report.append(recent_data.to_markdown(index=False))
        
        # Key insights
        report.append("\n## 5. Key Insights")
        report.append("\n**Trend Summary:**\n")
        
        if pct_change > 20:
            report.append(f"- 🚀 **Strong Growth**: {value_column} has increased significantly by {pct_change:.1f}%")
        elif pct_change < -20:
            report.append(f"- 📉 **Strong Decline**: {value_column} has decreased significantly by {pct_change:.1f}%")
        elif abs(pct_change) < 5:
            report.append(f"- 📊 **Stable Performance**: {value_column} remains relatively stable with only {abs(pct_change):.1f}% change")
        else:
            report.append(f"- 📈 **Moderate Change**: {value_column} has changed by {pct_change:+.1f}%")
        
        if cv > 30:
            report.append(f"- ⚠️ **High Variability**: Consider investigating causes of fluctuation")
        
        # Peak and trough analysis
        peak_idx = np.argmax(values)
        trough_idx = np.argmin(values)
        peak_date = resampled.index[peak_idx].strftime('%Y-%m-%d')
        trough_date = resampled.index[trough_idx].strftime('%Y-%m-%d')
        
        report.append(f"\n**Peak & Trough:**")
        report.append(f"- Peak: {max_value:.2f} on {peak_date}")
        report.append(f"- Trough: {min_value:.2f} on {trough_date}")
        
        # Save aggregated data as artifact
        agg_df = resampled.reset_index()
        agg_df.columns = [date_column, f"avg_{value_column}"]
        
        report.append(f"\n## 6. Data Saved")
        report.append(f"\n✅ Aggregated time series data saved for further analysis")
        report.append(f"- Period: {period_name} ({period})")
        report.append(f"- Data Points: {len(agg_df)}")
        
        return agg_df, resampled, "\n".join(report)

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _analyze_trend)
        
        if result[0] is None:
            return result[2]  # Error message
        
        agg_df, resampled, report = result
        
        # Save artifact with a descriptive name
        artifact_name = f"trend_{table_name}_{value_column}_{period}"
        artifact_id = await dm.save_artifact(
            agg_df, 
            artifact_name, 
            f"Trend analysis of {value_column} over {date_column} ({period})", 
            user_id
        )
        
        return f"{report}\n\n**Artifact ID:** `{artifact_id}`"
    except Exception as e:
        return f"Error analyzing trend: {str(e)}"

@tool
async def product_gap_detection_tool(
    table_name: str, 
    user_id: str, 
    min_cluster_size: int = 5,
    eps: float = 0.3
) -> str:
    """
    Detects gaps in a product catalog by clustering on embeddings.
    Uses DBSCAN clustering on the __embedding__ column to identify:
    1. Underrepresented product clusters (gaps)
    2. Outlier products (niche or edge cases)
    3. Missing product themes
    
    Args:
        table_name: The table name of the product dataset (must have __embedding__ column)
        user_id: User ID
        min_cluster_size: Minimum cluster size for DBSCAN (default: 5)
        eps: DBSCAN epsilon parameter for clustering (default: 0.3)
    
    Returns:
        Detailed gap analysis report with product recommendations
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if "__embedding__" not in df.columns:
        return f"Error: Dataset must have '__embedding__' column. Use embedding_tool first to generate embeddings."

    def _detect_product_gaps():
        from sklearn.cluster import DBSCAN
        
        # Extract embeddings
        embeddings = np.array(df["__embedding__"].tolist())
        
        # Perform DBSCAN clustering
        dbscan = DBSCAN(eps=eps, min_samples=min_cluster_size, metric='cosine')
        cluster_labels = dbscan.fit_predict(embeddings)
        
        # Add cluster labels to dataframe
        result_df = df.copy()
        result_df["__cluster_id__"] = cluster_labels
        
        # Analyze clusters
        unique_clusters = sorted([c for c in set(cluster_labels) if c != -1])
        noise_count = (cluster_labels == -1).sum()
        total_points = len(result_df)
        
        # Calculate cluster statistics
        cluster_stats = []
        for cluster_id in unique_clusters:
            cluster_data = result_df[result_df["__cluster_id__"] == cluster_id]
            cluster_size = len(cluster_data)
            percentage = (cluster_size / total_points) * 100
            cluster_stats.append({
                "cluster_id": cluster_id,
                "size": cluster_size,
                "percentage": percentage,
                "data": cluster_data
            })
        
        # Sort by size
        cluster_stats.sort(key=lambda x: x["size"], reverse=True)
        
        # Build gap analysis report
        report = []
        report.append(f"# Product Gap Analysis Report")
        report.append(f"\n**Total Products:** {total_points}")
        report.append(f"**Clustered Products:** {total_points - noise_count} ({((total_points - noise_count) / total_points * 100):.1f}%)")
        report.append(f"**Outlier Products:** {noise_count} ({(noise_count / total_points * 100):.1f}%)")
        report.append(f"**Number of Product Clusters:** {len(unique_clusters)}\n")
        
        # 1. Identify underrepresented clusters (potential gaps)
        report.append("## 1. Underrepresented Product Clusters (Gaps)")
        if cluster_stats:
            avg_cluster_size = np.mean([cs["size"] for cs in cluster_stats])
            underrepresented = [cs for cs in cluster_stats if cs["size"] < avg_cluster_size * 0.5]
            
            if underrepresented:
                report.append(f"\n**Found {len(underrepresented)} underrepresented clusters** (less than 50% of average size):\n")
                for cs in underrepresented[:5]:  # Top 5 smallest
                    report.append(f"### Cluster {cs['cluster_id']}")
                    report.append(f"- **Size:** {cs['size']} products ({cs['percentage']:.1f}% of total)")
                    report.append(f"- **Gap Indicator:** This cluster is {(avg_cluster_size / cs['size']):.1f}x smaller than average")
                    
                    # Show sample products
                    sample_cols = [col for col in result_df.columns if col not in ["__embedding__", "__cluster_id__"]]
                    report.append("\n**Sample Products:**")
                    report.append(cs["data"][sample_cols].head(5).to_markdown(index=False))
                    report.append("")
            else:
                report.append("\n*No significantly underrepresented clusters found.*\n")
        else:
            report.append("\n*No clusters formed. All products are outliers.*\n")
        
        # 2. Outlier analysis
        report.append("## 2. Outlier Products (Niche Opportunities)")
        outlier_percentage = (noise_count / total_points) * 100 if total_points > 0 else 0
        if noise_count > 0:
            report.append(f"\n**{noise_count} outlier products detected** ({outlier_percentage:.1f}% of total)")
            
            if outlier_percentage > 10:
                report.append("\n⚠️ **High outlier rate** suggests:")
                report.append("- Diverse product needs not covered by main categories")
                report.append("- Potential for new product lines or features")
                report.append("- Consider creating new product segments")
            
            # Show sample outliers
            outlier_data = result_df[result_df["__cluster_id__"] == -1]
            sample_cols = [col for col in result_df.columns if col not in ["__embedding__", "__cluster_id__"]]
            report.append("\n**Sample Outlier Products:**")
            report.append(outlier_data[sample_cols].head(5).to_markdown(index=False))
            report.append("")
        else:
            report.append("\n*No significant outliers detected. Good product coverage!*\n")
        
        # 3. All clusters with sample data
        report.append("## 3. All Product Clusters")
        report.append("\n**Complete Cluster Analysis:**\n")
        
        if cluster_stats:
            avg_cluster_size = np.mean([cs["size"] for cs in cluster_stats])
            for cs in cluster_stats:
                report.append(f"### Cluster {cs['cluster_id']}")
                report.append(f"- **Size:** {cs['size']} products ({cs['percentage']:.1f}% of total)")
                status = "✓ Well-represented" if cs['size'] >= avg_cluster_size else "⚠️ Underrepresented"
                report.append(f"- **Status:** {status}")
                
                # Show sample products
                sample_cols = [col for col in result_df.columns if col not in ["__embedding__", "__cluster_id__"]]
                report.append("\n**Sample Products:**")
                report.append(cs["data"][sample_cols].head(5).to_markdown(index=False))
                report.append("")
        
        # 4. Gap recommendations
        report.append("## 4. Product Gap Recommendations")
        report.append("\n**Key Insights:**\n")
        
        if cluster_stats:
            # Calculate concentration
            top3_percentage = sum([cs["percentage"] for cs in cluster_stats[:3]])
            if top3_percentage > 70:
                report.append(f"- 🎯 **High Concentration:** Top 3 clusters contain {top3_percentage:.1f}% of products")
                report.append("  - Consider: Are we over-focusing on a few product categories?")
                report.append("  - Opportunity: Explore underrepresented clusters for innovation")
            
            if len(underrepresented) > len(unique_clusters) * 0.3:
                report.append(f"- 📊 **Many Small Clusters:** {len(underrepresented)} clusters are underrepresented")
                report.append("  - Suggests: Diverse product needs not being adequately addressed")
                report.append("  - Action: Investigate these clusters for product gaps")
        
        if outlier_percentage > 15:
            report.append(f"- 🔍 **High Outlier Rate:** {outlier_percentage:.1f}% of products are outliers")
            report.append("  - Indicates: Significant niche opportunities or product gaps")
            report.append("  - Recommendation: Deep dive into outlier patterns for new product ideas")
        
        return "\n".join(report)

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _detect_product_gaps)
    except Exception as e:
        return f"Error detecting product gaps: {str(e)}"


@tool
async def semantic_search_tool(
    table_name: str,
    user_id: str,
    query: str,
    text_column: str = "text",
    top_k: int = 1000
) -> str:
    """
    Performs semantic search on a dataset to find reviews matching a query.
    
    Uses cosine similarity on the __embedding__ column to find the most relevant reviews.
    Only returns results with similarity score > 0.4 (relevant matches).
    
    IMPORTANT: The query is for EMBEDDING SEARCH, not a human! Keep it SHORT and DIRECT.
    
    Args:
        table_name: The dataset table name (must have __embedding__ column)
        user_id: User ID
        query: SHORT phrase (2-5 words). Examples:
               ✓ "slow search" 
               ✓ "bad customer support"
               ✓ "pricing too expensive"
               ✗ "reviews mentioning that the search is slow" (TOO VERBOSE)
               ✗ "find all reviews about customer support issues" (TOO VERBOSE)
        text_column: Column containing the text to display (default: "text")
        top_k: Maximum number of results to return (default: 1000, max: 1000)
    
    Returns:
        Markdown formatted results with matching reviews and download link
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if "__embedding__" not in df.columns:
        return f"Error: Dataset must have '__embedding__' column. Use generate_embeddings first."
    
    if text_column not in df.columns:
        return f"Error: Column '{text_column}' not found in dataset."
    
    # Cap top_k at 1000
    top_k = min(top_k, 1000)
    
    def _search():
        # Generate embedding for the query
        embeddings_model = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        query_embedding = embeddings_model.embed_query(query)
        query_vec = np.array(query_embedding)
        
        # Get all embeddings from dataset
        embeddings = np.array(df["__embedding__"].tolist())
        
        # Compute cosine similarity
        # Normalize vectors
        query_norm = query_vec / np.linalg.norm(query_vec)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Cosine similarity
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Get top_k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]
        # Filter to only include results with similarity > 0.4 (relevant matches)
        valid_mask = top_scores > 0.033
        top_indices = top_indices[valid_mask]
        top_scores = top_scores[valid_mask]
        
        return top_indices, top_scores
    
    loop = asyncio.get_running_loop()
    try:
        top_indices, top_scores = await loop.run_in_executor(None, _search)
        
        if len(top_indices) == 0:
            return f"No relevant results found for query: '{query}'"
        
        # Get the matching rows
        result_df = df.iloc[top_indices].copy()
        result_df["__similarity_score__"] = top_scores
        
        # Save as artifact for further analysis
        artifact_name = f"search_{table_name}_{len(result_df)}_similarity_to_{query}"
        await dm.save_artifact(
            result_df.drop(columns=["__embedding__", "__similarity_score__"], errors="ignore"),
            artifact_name,
            f"Semantic search results for: {query}",
            user_id
        )
        
        # Build report
        report = []
        report.append(f"# 🔍 Semantic Search Results")
        report.append(f"\n**Query:** \"{query}\"")
        report.append(f"**Dataset:** {table_name}")
        report.append(f"**Results Found:** {len(result_df)}")
        report.append(f"**Saved as:** `{artifact_name}`\n")
        
        # Show top 10 results with similarity scores
        report.append("## Top Results\n")
        report.append("| # | Score | Review |")
        report.append("|---|-------|--------|")
        
        for i, (idx, row) in enumerate(result_df.head(10).iterrows(), 1):
            score = row["__similarity_score__"]
            text_preview = str(row[text_column])[:100].replace("|", "\\|").replace("\n", " ")
            if len(str(row[text_column])) > 100:
                text_preview += "..."
            report.append(f"| {i} | {score:.3f} | {text_preview} |")
        
        if len(result_df) > 10:
            report.append(f"\n*...and {len(result_df) - 10} more results saved in `{artifact_name}`*")
        
        # Add summary stats
        report.append("\n## Similarity Score Distribution")
        report.append(f"- **Highest:** {top_scores[0]:.3f}")
        report.append(f"- **Lowest:** {top_scores[-1]:.3f}")
        report.append(f"- **Mean:** {np.mean(top_scores):.3f}")
        
        # Add download link
        report.append("\n---")
        report.append(f"\n📥 **[Download all {len(result_df)} results as CSV](download:{artifact_name})**")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error performing semantic search: {str(e)}"


class ProductGap(BaseModel):
    """A single product gap extracted from reviews."""
    title: str = Field(description="Short title for the gap (3-7 words)")
    description: str = Field(description="Detailed description of the gap")
    severity: str = Field(description="Severity level: critical, high, medium, low")
    frequency_hint: str = Field(description="How often this issue seems to appear")
    suggested_action: str = Field(description="Recommended action to address the gap")


class ProductGapsExtraction(BaseModel):
    """Structured extraction of product gaps from reviews."""
    gaps: List[ProductGap] = Field(description="List of identified product gaps")
    overall_summary: str = Field(description="Brief summary of the main pain points")


@tool
async def negative_review_gap_detector(
    table_name: str,
    user_id: str,
    text_column: str = "text",
    rating_column: str | None = None,
    max_clusters: int = 100,
    min_rating: int = 1,
    max_rating: int = 3
) -> str:
    """
    Detects product gaps from reviews using HDBSCAN clustering + LLM analysis.
    
    Process:
    1. If rating_column provided: filters reviews with ratings between min_rating and max_rating
    2. Clusters reviews using HDBSCAN (targets min(n_reviews/2, 100) clusters)
    3. Finds the centroid review (most representative) of each cluster
    4. Sends centroid reviews to LLM to extract product gaps
    
    Args:
        table_name: The dataset table name (must have __embedding__ column)
        user_id: User ID
        text_column: Column containing review text (default: "text")
        rating_column: Column containing ratings (optional - if not provided, analyzes all reviews)
        max_clusters: Maximum number of clusters to target (default: 100)
        min_rating: Minimum rating to include when filtering (default: 1)
        max_rating: Maximum rating to include when filtering (default: 3)
    
    Returns:
        Detailed product gap analysis report with actionable insights
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if "__embedding__" not in df.columns:
        return f"Error: Dataset must have '__embedding__' column. Use embedding_tool first."
    
    if text_column not in df.columns:
        return f"Error: Column '{text_column}' not found in dataset."
    
    # Check rating column only if provided
    use_rating_filter = rating_column is not None and rating_column in df.columns

    def _cluster_and_find_centroids():
        # Filter by rating if rating_column is provided and exists
        if use_rating_filter:
            filtered_df = df[
                (df[rating_column] >= min_rating) & 
                (df[rating_column] <= max_rating)
            ].copy()
        else:
            filtered_df = df.copy()
        
        if filtered_df.empty:
            if use_rating_filter:
                return None, None, "No reviews found with ratings between {} and {}".format(min_rating, max_rating)
            return None, None, "No reviews found in dataset"
        
        n_reviews = len(filtered_df)
        
        # Target cluster count: min(n_reviews / 2, max_clusters)
        target_clusters = min(n_reviews // 2, max_clusters)
        
        if n_reviews < 2:
            return None, None, "Not enough reviews for clustering (minimum 2 required)"
        
        # Extract embeddings
        embeddings = np.array(filtered_df["__embedding__"].tolist())
        
        # Calculate min_cluster_size to get approximately target_clusters
        # HDBSCAN finds clusters automatically, but min_cluster_size controls granularity
        # Rough heuristic: min_cluster_size = n_reviews / target_clusters
        min_cluster_size = max(2, n_reviews // max(target_clusters, 1))
        
        # Perform HDBSCAN clustering
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            metric='euclidean',
            cluster_selection_method='eom'
        )
        cluster_labels = clusterer.fit_predict(embeddings)
        
        filtered_df["__cluster_id__"] = cluster_labels
        
        # Get unique clusters (excluding noise labeled as -1)
        unique_clusters = [c for c in set(cluster_labels) if c != -1]
        
        # Find centroid review for each cluster
        centroid_reviews = []
        for cluster_id in unique_clusters:
            cluster_mask = cluster_labels == cluster_id
            cluster_embeddings = embeddings[cluster_mask]
            cluster_indices = np.where(cluster_mask)[0]
            
            if len(cluster_indices) == 0:
                continue
            
            # Find the review closest to the cluster centroid (mean of cluster)
            cluster_center = cluster_embeddings.mean(axis=0)
            distances = np.linalg.norm(cluster_embeddings - cluster_center, axis=1)
            closest_idx = cluster_indices[np.argmin(distances)]
            
            centroid_row = filtered_df.iloc[closest_idx]
            
            # Get rating if available
            review_rating = None
            if use_rating_filter and rating_column in filtered_df.columns:
                review_rating = int(centroid_row[rating_column]) if pd.notna(centroid_row[rating_column]) else None
            
            centroid_reviews.append({
                "cluster_id": cluster_id,
                "cluster_size": int(cluster_mask.sum()),
                "text": str(centroid_row[text_column])[:500],  # Limit text length
                "rating": review_rating
            })
        
        # Count noise points
        noise_count = (cluster_labels == -1).sum()
        
        # Sort by cluster size (most common issues first)
        centroid_reviews.sort(key=lambda x: x["cluster_size"], reverse=True)
        
        return filtered_df, centroid_reviews, None, noise_count, len(unique_clusters), use_rating_filter
    
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _cluster_and_find_centroids)
        
        # Handle error case (3 elements) vs success case (6 elements)
        if len(result) == 3:
            _, _, error = result
            return f"Error: {error}"
        
        filtered_df, centroid_reviews, _, noise_count, n_clusters, used_rating_filter = result
        n_reviews = len(filtered_df)
        
        # Build prompt for LLM with centroid reviews
        def format_review(i, r):
            rating_info = f", Rating: {r['rating']}" if r['rating'] is not None else ""
            return f"**Cluster {i+1}** ({r['cluster_size']} similar reviews{rating_info}):\n\"{r['text']}\""
        
        reviews_text = "\n\n".join([
            format_review(i, r)
            for i, r in enumerate(centroid_reviews[:50])  # Limit to top 50 clusters
        ])
        
        filter_desc = f"filtered to {min_rating}-{max_rating} star ratings" if used_rating_filter else "all reviews (no rating filter)"
        
        prompt = f"""You are a product analyst. Analyze these representative customer reviews (each represents a cluster of similar reviews).

Total reviews analyzed: {n_reviews} ({filter_desc})
Number of distinct clusters: {n_clusters}

REPRESENTATIVE REVIEWS (one per cluster, sorted by frequency):

{reviews_text}

Extract the key product gaps, issues, and improvement opportunities. Focus on:
1. Recurring problems that appear across multiple clusters
2. Critical issues that severely impact user experience
3. Feature gaps or missing functionality
4. UX/usability problems
5. Performance or reliability issues

Be specific and actionable in your analysis."""

        # Call LLM with structured output
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )
        structured_llm = llm.with_structured_output(ProductGapsExtraction)
        
        result = await structured_llm.ainvoke(prompt)
        
        # Build comprehensive report
        report = []
        report.append("# 🔍 Product Gap Analysis from Reviews")
        report.append(f"\n**Dataset:** {table_name}")
        if used_rating_filter:
            report.append(f"**Rating Filter:** {min_rating}-{max_rating} stars")
        else:
            report.append("**Rating Filter:** None (all reviews)")
        report.append(f"**Total Reviews Analyzed:** {n_reviews}")
        report.append(f"**Complaint Clusters:** {n_clusters}")
        report.append(f"**Unclustered (noise):** {noise_count}")
        report.append(f"**Analysis Method:** HDBSCAN Clustering + LLM Extraction\n")
        
        report.append("---\n")
        report.append(f"## 📋 Summary\n\n{result.overall_summary}\n")
        
        report.append("---\n")
        report.append("## 🚨 Identified Product Gaps\n")
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🟡",
            "low": "🟢"
        }
        
        for i, gap in enumerate(result.gaps, 1):
            emoji = severity_emoji.get(gap.severity.lower(), "⚪")
            report.append(f"### {i}. {gap.title} {emoji}")
            report.append(f"\n**Severity:** {gap.severity.upper()}")
            report.append(f"**Frequency:** {gap.frequency_hint}")
            report.append(f"\n**Description:**\n{gap.description}")
            report.append(f"\n**Recommended Action:**\n> {gap.suggested_action}\n")
        
        # Add cluster size distribution
        report.append("---\n")
        report.append("## 📊 Cluster Size Distribution\n")
        report.append("| Cluster | Size | Sample Review |")
        report.append("|---------|------|---------------|")
        
        for i, cr in enumerate(centroid_reviews[:15], 1):  # Top 15 clusters
            text_preview = cr["text"][:80].replace("|", "\\|").replace("\n", " ")
            if len(cr["text"]) > 80:
                text_preview += "..."
            report.append(f"| {i} | {cr['cluster_size']} | {text_preview} |")
        
        if len(centroid_reviews) > 15:
            report.append(f"\n*...and {len(centroid_reviews) - 15} more clusters*")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error detecting product gaps: {str(e)}"
