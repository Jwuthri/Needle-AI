import matplotlib
matplotlib.use('Agg') # Use non-interactive backend to avoid thread issues
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import base64
from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager

# Singleton access (or we could instantiate inside, but singleton is better for shared state if any)
dm = DataManager()

@tool
def generate_plot_tool(dataset_id: str, x_column: str, y_column: str, plot_type: str = "scatter") -> str:
    """
    Generate a plot for a given dataset.
    
    Args:
        dataset_id: The ID of the dataset to plot.
        x_column: The column name for the x-axis.
        y_column: The column name for the y-axis.
        plot_type: The type of plot ('scatter', 'line', 'bar', 'hist').
        
    Returns:
        A string message indicating success (plots are displayed in the UI if supported, 
        but for now we just confirm generation).ipyt
    """
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    if x_column not in df.columns:
        return f"Error: Column {x_column} not found in dataset."
    
    # y_column is optional for some plots like hist, but required for others
    if y_column and y_column not in df.columns:
        return f"Error: Column {y_column} not found in dataset."

    plt.figure(figsize=(10, 6))
    
    try:
        if plot_type == "scatter":
            sns.scatterplot(data=df, x=x_column, y=y_column)
        elif plot_type == "line":
            sns.lineplot(data=df, x=x_column, y=y_column)
        elif plot_type == "bar":
            sns.barplot(data=df, x=x_column, y=y_column)
        elif plot_type == "hist":
            sns.histplot(data=df, x=x_column)
        else:
            return f"Error: Unsupported plot type {plot_type}. Use 'scatter', 'line', 'bar', or 'hist'."
            
        plt.title(f"{plot_type.capitalize()} Plot of {y_column} vs {x_column}")
        
        # Save and open the plot
        filename = "plot.png"
        plt.savefig(filename)
        plt.close()
        
        # Open the file (macOS specific, but user is on Mac)
        import os
        os.system(f"open {filename}")
        
        return f"Successfully generated {plot_type} plot for {x_column} vs {y_column}. The plot has been opened in a new window and saved here: {filename}."
        
    except Exception as e:
        return f"Error generating plot: {str(e)}"
