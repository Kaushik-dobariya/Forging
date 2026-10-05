from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.templates import templates


router = APIRouter(tags=["Public Web"])


@router.get("/", response_class=HTMLResponse, summary="Public Homepage")
async def index_view(request: Request):
    """Renders the public corporate website homepage."""
    return templates.TemplateResponse(
        request=request,
        name="public/index.html",
        context={"request": request},
    )
