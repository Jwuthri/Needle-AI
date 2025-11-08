"""
Configuration compatibility layer.
Imports from new location for backwards compatibility.
"""

from app.core.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
