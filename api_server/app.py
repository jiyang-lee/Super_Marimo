from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import DATABASE_URL
from extensions.db import cleanup_old_realtime_rows, get_db_connection, init_db, start_cleanup_timer
from routers.events import router as events_router
from routers.health import router as health_router
from routers.interaction import router as interaction_router
from routers.sensor import router as sensor_router
from routers.sessions import router as sessions_router
from services.sensor_analytics import rebuild_sensor_reading_states


def create_app() -> FastAPI:
    app = FastAPI(title="Marimo API Server", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(sensor_router)
    app.include_router(sessions_router)
    app.include_router(interaction_router)

    @app.on_event("startup")
    def startup() -> None:
        init_db()
        if DATABASE_URL:
            with get_db_connection() as conn:
                rebuild_sensor_reading_states(conn)
        cleanup_old_realtime_rows(force=True)
        start_cleanup_timer()

    return app


app = create_app()
