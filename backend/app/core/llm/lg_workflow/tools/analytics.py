from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

dm = DataManager()

@tool
def clustering_tool(dataset_id: str, target_column: str, n_clusters: int = 3) -> str:
    """
    Performs K-Means clustering on a numeric column of a dataset.
    Returns the ID of the new dataset containing the cluster labels.
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    if target_column not in df.columns:
        return f"Error: Column {target_column} not found in dataset."
        
    # Simple numeric check
    if not pd.api.types.is_numeric_dtype(df[target_column]):
        return f"Error: Column {target_column} is not numeric."

    # Perform Clustering
    data = df[[target_column]].dropna()
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(data)
    
    # Create result dataframe
    result_df = df.copy()
    result_df['cluster'] = pd.Series(clusters, index=data.index)
    
    # Save artifact
    new_id = dm.save_artifact(result_df, f"Clustered {dataset_id} on {target_column} with k={n_clusters}")
    
    return f"Clustering complete. Result saved to dataset ID: {new_id}. You can now query this new dataset."

@tool
def tfidf_tool(dataset_id: str, text_column: str, max_features: int = 10) -> str:
    """
    Computes TF-IDF top features for a text column.
    Returns a summary of top keywords.
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
        
    if text_column not in df.columns:
        return f"Error: Column {text_column} not found."

    vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(df[text_column].dropna().astype(str))
        feature_names = vectorizer.get_feature_names_out()
        
        return f"Top {max_features} TF-IDF terms: {', '.join(feature_names)}"
    except Exception as e:
        return f"Error computing TF-IDF: {str(e)}"

@tool
def describe_tool(dataset_id: str) -> str:
    """
    Returns descriptive statistics for a dataset (count, mean, std, etc.).
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
        
    return df.describe().to_markdown()
