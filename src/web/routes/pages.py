"""Page routes — serves full HTML pages."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page with roster checklist and query form."""
    return templates.TemplateResponse(request=request, name="index.html", context={})
