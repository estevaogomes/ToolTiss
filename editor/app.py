"""FastAPI application factory for the TISS Editor."""
import os
import sys

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


def create_app() -> FastAPI:
    app = FastAPI(title="ToolTiss Editor", docs_url=None, redoc_url=None)

    # Resolve paths relative to this file (works inside PyInstaller bundle)
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app.state.templates = Jinja2Templates(directory=templates_dir)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Import and register routes
    from editor.routes import dialogs, lote_ops, xml_ops

    app.include_router(xml_ops.router, prefix="/api")
    app.include_router(lote_ops.router, prefix="/api")
    app.include_router(dialogs.router, prefix="/api")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return app.state.templates.TemplateResponse("base.html", {"request": request})

    return app
