from app.core.llm.simple_workflow.utils.extract_data_from_ctx_by_key import extract_data_from_ctx_by_key
from app.database.session import get_async_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

import pandas as pd
import numpy as np
from llama_index.core.workflow import Context
from typing import Optional, List
from textblob import TextBlob

logger = get_logger(__name__)


async def analyze_sentiment(
    ctx: Context,
    dataset_name: str,
    text_column: str,
    categories: Optional[List[str]] = None
) -> str:
    """Analyze sentiment in text data using TextBlob.
    
    This tool performs sentiment analysis to identify:
    1. Overall sentiment distribution (positive, negative, neutral)
    2. Sentiment polarity (-1 to +1 scale)
    3. Subjectivity scores (0 to 1 scale)
    4. Sentiment trends by categories (if provided)
    5. Most positive and negative samples
    
    Args:
        ctx: Context
        dataset_name: Name of the dataset to analyze
        text_column: Name of the column containing text data
        categories: Optional list of category columns for segmented analysis
    
    Returns:
        str: Markdown formatted sentiment analysis report
    """
    async with get_async_session() as db:
        try:
            # Get dataset from context
            data = await extract_data_from_ctx_by_key(ctx, "dataset_data", dataset_name)
            
            if data is None or data.empty:
                return f"Error: Dataset '{dataset_name}' not found in context. Please load the dataset first."
            
            # Check if text column exists
            if text_column not in data.columns:
                available_cols = ", ".join(data.columns[:10])
                return f"Error: Text column '{text_column}' not found. Available columns: {available_cols}"
            
            # Create a working copy
            analysis_data = data.copy()
            
            # Calculate sentiment scores
            logger.info(f"Analyzing sentiment for {len(analysis_data)} records...")
            
            sentiments = []
            for text in analysis_data[text_column]:
                try:
                    text_str = str(text) if text is not None else ""
                    blob = TextBlob(text_str)
                    sentiments.append({
                        'polarity': blob.sentiment.polarity,
                        'subjectivity': blob.sentiment.subjectivity
                    })
                except Exception as e:
                    logger.warning(f"Failed to analyze text: {e}")
                    sentiments.append({'polarity': 0.0, 'subjectivity': 0.0})
            
            # Add sentiment columns
            analysis_data['__sentiment_polarity__'] = [s['polarity'] for s in sentiments]
            analysis_data['__sentiment_subjectivity__'] = [s['subjectivity'] for s in sentiments]
            
            # Classify sentiment
            def classify_sentiment(polarity):
                if polarity > 0.1:
                    return 'Positive'
                elif polarity < -0.1:
                    return 'Negative'
                else:
                    return 'Neutral'
            
            analysis_data['__sentiment_label__'] = analysis_data['__sentiment_polarity__'].apply(classify_sentiment)
            
            # Build report
            report = []
            report.append(f"# Sentiment Analysis Report for '{dataset_name}'")
            report.append(f"\n**Text Column:** {text_column}")
            report.append(f"**Total Records Analyzed:** {len(analysis_data)}\n")
            
            # Overall sentiment distribution
            report.append("## 1. Overall Sentiment Distribution")
            sentiment_counts = analysis_data['__sentiment_label__'].value_counts()
            total = len(analysis_data)
            
            report.append("\n**Sentiment Breakdown:**\n")
            for sentiment in ['Positive', 'Neutral', 'Negative']:
                count = sentiment_counts.get(sentiment, 0)
                pct = (count / total) * 100
                emoji = "😊" if sentiment == 'Positive' else "😐" if sentiment == 'Neutral' else "😞"
                report.append(f"- {emoji} **{sentiment}:** {count} ({pct:.1f}%)")
            
            # Sentiment statistics
            report.append("\n## 2. Sentiment Statistics")
            polarity_mean = analysis_data['__sentiment_polarity__'].mean()
            polarity_std = analysis_data['__sentiment_polarity__'].std()
            subjectivity_mean = analysis_data['__sentiment_subjectivity__'].mean()
            
            report.append(f"\n**Polarity Scores** (Range: -1 to +1):")
            report.append(f"- Mean: {polarity_mean:.3f}")
            report.append(f"- Std Dev: {polarity_std:.3f}")
            report.append(f"- Min: {analysis_data['__sentiment_polarity__'].min():.3f}")
            report.append(f"- Max: {analysis_data['__sentiment_polarity__'].max():.3f}")
            
            report.append(f"\n**Subjectivity Scores** (Range: 0 to 1):")
            report.append(f"- Mean: {subjectivity_mean:.3f}")
            report.append(f"- This indicates the text is {'mostly subjective' if subjectivity_mean > 0.5 else 'mostly objective'}")
            
            # Sentiment interpretation
            report.append("\n## 3. Sentiment Insights")
            if polarity_mean > 0.2:
                report.append("- 📈 **Overall Positive Sentiment**: The dataset shows predominantly positive sentiment")
            elif polarity_mean < -0.2:
                report.append("- 📉 **Overall Negative Sentiment**: The dataset shows predominantly negative sentiment")
            else:
                report.append("- ⚖️ **Balanced Sentiment**: The dataset shows balanced or neutral sentiment")
            
            if polarity_std > 0.4:
                report.append("- 🎭 **High Variation**: Sentiment varies significantly across records")
            
            # Most positive samples
            report.append("\n## 4. Most Positive Examples")
            most_positive = analysis_data.nlargest(3, '__sentiment_polarity__')
            report.append("\n**Top 3 Most Positive:**\n")
            
            sample_cols = [col for col in data.columns if col not in ['__sentiment_polarity__', '__sentiment_subjectivity__', '__sentiment_label__', '__embedding__']][:3]
            for idx, (_, row) in enumerate(most_positive.iterrows(), 1):
                report.append(f"**{idx}. Polarity: {row['__sentiment_polarity__']:.3f}**")
                report.append(f"   - {text_column}: {str(row[text_column])[:200]}...")
                report.append("")
            
            # Most negative samples
            report.append("## 5. Most Negative Examples")
            most_negative = analysis_data.nsmallest(3, '__sentiment_polarity__')
            report.append("\n**Top 3 Most Negative:**\n")
            
            for idx, (_, row) in enumerate(most_negative.iterrows(), 1):
                report.append(f"**{idx}. Polarity: {row['__sentiment_polarity__']:.3f}**")
                report.append(f"   - {text_column}: {str(row[text_column])[:200]}...")
                report.append("")
            
            # Category-based analysis (if categories provided)
            if categories:
                report.append("## 6. Sentiment by Category")
                
                for category in categories:
                    if category not in data.columns:
                        report.append(f"\n⚠️ Category column '{category}' not found, skipping...")
                        continue
                    
                    report.append(f"\n### By {category}")
                    
                    # Group by category and calculate mean sentiment
                    category_sentiment = analysis_data.groupby(category).agg({
                        '__sentiment_polarity__': ['mean', 'count'],
                        '__sentiment_label__': lambda x: x.value_counts().to_dict()
                    }).reset_index()
                    
                    category_sentiment.columns = [category, 'Mean Polarity', 'Count', 'Distribution']
                    category_sentiment = category_sentiment.sort_values('Mean Polarity', ascending=False)
                    
                    # Create summary table
                    summary_data = []
                    for _, row in category_sentiment.head(10).iterrows():
                        dist = row['Distribution']
                        sentiment_icon = "😊" if row['Mean Polarity'] > 0.1 else "😞" if row['Mean Polarity'] < -0.1 else "😐"
                        summary_data.append({
                            category: row[category],
                            'Sentiment': sentiment_icon,
                            'Polarity': f"{row['Mean Polarity']:.3f}",
                            'Count': int(row['Count'])
                        })
                    
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        report.append("\n" + summary_df.to_markdown(index=False))
                        report.append("")
            
            # Store sentiment analysis results in context
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "sentiment_analysis" not in ctx_state["state"]:
                    ctx_state["state"]["sentiment_analysis"] = {}
                
                # Store the analyzed data with sentiment scores
                if "dataset_data" not in ctx_state["state"]:
                    ctx_state["state"]["dataset_data"] = {}
                if "sentiment" not in ctx_state["state"]["dataset_data"]:
                    ctx_state["state"]["dataset_data"]["sentiment"] = {}
                
                ctx_state["state"]["dataset_data"]["sentiment"][dataset_name] = analysis_data
                
                # Store summary statistics
                ctx_state["state"]["sentiment_analysis"][dataset_name] = {
                    "text_column": text_column,
                    "total_records": len(analysis_data),
                    "sentiment_distribution": sentiment_counts.to_dict(),
                    "mean_polarity": float(polarity_mean),
                    "mean_subjectivity": float(subjectivity_mean),
                    "std_polarity": float(polarity_std)
                }
            
            result = "\n".join(report)
            logger.info(f"Sentiment analysis completed for '{dataset_name}': {len(analysis_data)} records analyzed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing sentiment analysis: {e}", exc_info=True)
            return f"Error: {str(e)}"
