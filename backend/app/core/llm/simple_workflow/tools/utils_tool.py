from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.logging import get_logger
from llama_index.core.workflow import Context
import requests

logger = get_logger(__name__)


async def get_current_time(ctx: Context) -> Dict[str, Any]:
    """Get current time and date in UTC.
    
    Returns:
        Dict with current UTC time information
    """
    now = datetime.utcnow()
    current_time = {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_datetime": now.isoformat(),
        "timezone": "UTC",
    }

    async with ctx.store.edit_state() as ctx_state:
        if "state" not in ctx_state:
            ctx_state["state"] = {}
        ctx_state["state"]["current_time"] = current_time

    return current_time


async def get_user_location(ctx: Context) -> Dict[str, Any]:
    """Get approximate location using IP geolocation.

    Returns:
        Dict with user location information
    """
    user_location = {}
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip = response.json()["ip"]
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            user_location = {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
            }
    except Exception as e:
        logger.error(f"Failed to get location: {e}")

    async with ctx.store.edit_state() as ctx_state:
        if "state" not in ctx_state:
            ctx_state["state"] = {}
        ctx_state["state"]["user_location"] = user_location

    return user_location
