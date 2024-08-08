from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.middleware.cors import CORSMiddleware

from mm.api.routes import avatea
from trading_api import algorithm_routes_v1, algorithm_routes_v2
from trading_api.core.container import Container, di_container
from trading_api.core.health import handle_health_request

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.mount("/api/v1", algorithm_routes_v1.app, name="api_v1")
app.mount("/api/v2", algorithm_routes_v2.app, name="api_v2")

app.mount("/api/avatea", avatea, name="api_avatea")


@app.get(
    path="/",
)
async def check_health(
    container: Container = Depends(di_container),
):
    handle_health_request(container)
    return {"message": "To the moon! 🚀", "status": "OK"}


@app.get(
    path="/docs",
)
async def get_swagger_ui():
    return RedirectResponse("/api/v2/docs", status_code=status.HTTP_303_SEE_OTHER)


@app.get(
    path="/redoc",
)
async def get_redoc():
    return RedirectResponse("/api/v2/redoc", status_code=status.HTTP_303_SEE_OTHER)
