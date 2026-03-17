"""
API v1 endpoints.

Available endpoints:
- /api/v1/upload-excel - Upload and process Excel files
"""

from .upload import router

__all__ = ["router"]
