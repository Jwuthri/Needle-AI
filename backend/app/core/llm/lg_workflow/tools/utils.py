"""Utility tools for general information."""
from langchain_core.tools import tool
from datetime import datetime
import requests
from typing import Dict, Any


@tool
async def get_current_time() -> str:
    """Get current time and date in UTC.
    
    Returns formatted string with current UTC time information.
    Use this when the user asks about the current time, date, or datetime.
    """
    now = datetime.utcnow()
    
    # Build formatted response
    response = []
    response.append("# Current Time Information")
    response.append(f"\n**Date:** {now.strftime('%Y-%m-%d (%A, %B %d, %Y)')}")
    response.append(f"**Time:** {now.strftime('%H:%M:%S UTC')}")
    response.append(f"**ISO Format:** {now.isoformat()}Z")
    response.append(f"**Timezone:** UTC (Coordinated Universal Time)")
    
    return "\n".join(response)


@tool
async def get_user_location() -> str:
    """Get approximate user location using IP geolocation.
    
    Returns location information including city, region, and country.
    Use this when the user asks about their location or wants location-based information.
    """
    try:
        # Get public IP
        ip_response = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip = ip_response.json()["ip"]
        
        # Get location data
        location_response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        
        if location_response.status_code == 200:
            data = location_response.json()
            
            # Build formatted response
            response = []
            response.append("# User Location Information")
            response.append(f"\n**IP Address:** {ip}")
            response.append(f"**City:** {data.get('city', 'Unknown')}")
            response.append(f"**Region:** {data.get('regionName', 'Unknown')}")
            response.append(f"**Country:** {data.get('country', 'Unknown')}")
            response.append(f"**Timezone:** {data.get('timezone', 'Unknown')}")
            response.append(f"**Coordinates:** {data.get('lat', 'N/A')}°, {data.get('lon', 'N/A')}°")
            
            return "\n".join(response)
        else:
            return "Error: Unable to retrieve location information from IP geolocation service."
            
    except requests.exceptions.Timeout:
        return "Error: Location service timed out. Please try again later."
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to retrieve location information: {str(e)}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

