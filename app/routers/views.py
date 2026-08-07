"""Views que servem HTML (a página do chat)."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app import config

router = APIRouter(tags=["views"])


@router.get("/", include_in_schema=False)
def index():
    return FileResponse(config.STATIC_DIR / "index.html")
