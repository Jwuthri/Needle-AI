from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd
from textblob import TextBlob
from langchain_openai import OpenAIEmbeddings
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np
import os

dm = DataManager()

@tool
def sentiment_analysis_tool(dataset_id: str, text_column: str) -> str:
    """
    Analyzes the sentiment of a text column in a dataset.
    Adds a new column 'sentiment_polarity' to the dataset.
    
    Args:
        dataset_id: The ID of the dataset.
        text_column: The name of the column containing text.
        
    Returns:
        A message confirming the operation and the new dataset ID (which is the same).
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    if text_column not in df.columns:
        return f"Error: Column {text_column} not found."
    
    try:
        # Apply sentiment analysis
        df['sentiment_polarity'] = df[text_column].astype(str).apply(lambda x: TextBlob(x).sentiment.polarity)
        return f"Successfully added 'sentiment_polarity' column to dataset {dataset_id}. Range is -1.0 (negative) to 1.0 (positive)."
    except Exception as e:
        return f"Error performing sentiment analysis: {str(e)}"

@tool
def embedding_tool(dataset_id: str, text_column: str) -> str:
    """
    Generates vector embeddings for a text column using OpenAI's embedding model.
    Adds a new column 'embedding' to the dataset.
    WARNING: This can be slow and cost money for large datasets.
    
    Args:
        dataset_id: The ID of the dataset.
        text_column: The name of the column containing text.
        
    Returns:
        A message confirming the operation.
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    if text_column not in df.columns:
        return f"Error: Column {text_column} not found."
        
    try:
        embeddings_model = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        texts = df[text_column].astype(str).tolist()
        
        # Batch processing could be better, but keeping it simple for now
        embeddings = embeddings_model.embed_documents(texts)
        
        df['embedding'] = embeddings
        return f"Successfully added 'embedding' column to dataset {dataset_id}."
    except Exception as e:
        return f"Error generating embeddings: {str(e)}"

@tool
def linear_regression_tool(dataset_id: str, target_column: str, feature_columns: list[str]) -> str:
    """
    Performs a simple linear regression to predict a target column based on feature columns.
    
    Args:
        dataset_id: The ID of the dataset.
        target_column: The column to predict (y).
        feature_columns: A list of columns to use as predictors (X).
        
    Returns:
        A summary of the regression results (R2 score, MSE, Coefficients).
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    missing_cols = [col for col in feature_columns + [target_column] if col not in df.columns]
    if missing_cols:
        return f"Error: Columns {missing_cols} not found in dataset."
        
    try:
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
                
    except Exception as e:
        return f"Error performing regression: {str(e)}"
