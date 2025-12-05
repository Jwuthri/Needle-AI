"""
API endpoints for serving generated graph images.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security.clerk_auth import ClerkUser, get_current_user

router = APIRouter()

# Base directory for graphs
GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent / "data" / "graphs"


@router.get("/{filename}")
async def get_graph_image(
    filename: str,
    current_user: Optional[ClerkUser] = Depends(get_current_user)
):
    """
    Serve a generated graph image.
    
    The filename should be in format: TIMESTAMP_CHARTTYPE_TITLE.png
    The actual file is stored in user-specific subdirectories.
    
    Args:
        filename: The graph filename (e.g., "20251116_210029_pie_Overall_Sentiment_Distribution.png")
        current_user: Current authenticated user (optional for now)
        
    Returns:
        FileResponse with the PNG image
    """
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files are supported")
    
    # Search for the file in user directories
    # For now, we search all user directories since we don't have user_id in the filename
    # In production, you might want to encode user_id in the filename or use a different approach
    for user_dir in GRAPHS_BASE_DIR.iterdir():
        if user_dir.is_dir():
            file_path = user_dir / filename
            if file_path.exists() and file_path.is_file():
                return FileResponse(
                    path=str(file_path),
                    media_type="image/png",
                    headers={
                        "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    }
                )
    
    # File not found
    raise HTTPException(status_code=404, detail="Graph image not found")

