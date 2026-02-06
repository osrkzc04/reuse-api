"""
Aplicación FastAPI principal de Reuse.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.v1.router import api_router
from app.services.init_service import run_initialization
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ConflictException,
)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Reuse - Sistema de Intercambio Sostenible PUCE

    API RESTful para la sistema de intercambio de objetos entre estudiantes.

    ### Características principales:

    * 🔐 **Autenticación JWT** - Sistema seguro de login con refresh tokens
    * 📦 **Ofertas** - CRUD completo de objetos para intercambio
    * 💬 **Chat** - Mensajería en tiempo real entre usuarios
    * 🔄 **Intercambios** - Sistema de trueques con confirmación dual
    * 🏆 **Gamificación** - Puntos, niveles, badges y retos
    * 📊 **Rankings** - Rankings por facultad y general
    * 🔔 **Notificaciones** - Sistema de notificaciones en tiempo real

    ### Documentación:

    - **Swagger UI**: /docs
    - **ReDoc**: /redoc
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar archivos estáticos (uploads)
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")


# Exception Handlers
@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    """Handler para recursos no encontrados."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handler para errores de autenticación."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)}
    )


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    """Handler para errores de autorización."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)}
    )


@app.exception_handler(BadRequestException)
async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    """Handler para solicitudes inválidas."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(ConflictException)
async def conflict_exception_handler(request: Request, exc: ConflictException):
    """Handler para conflictos."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para errores de validación de Pydantic."""
    # Convertir errores a formato serializable
    errors = []
    for error in exc.errors():
        err = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
        }
        # Incluir input solo si es serializable
        if "input" in error:
            try:
                import json
                json.dumps(error["input"])
                err["input"] = error["input"]
            except (TypeError, ValueError):
                err["input"] = str(error["input"])
        errors.append(err)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors}
    )


# Incluir routers de la API
app.include_router(api_router, prefix="/api/v1")


# Endpoint raíz
@app.get("/", tags=["Health"])
async def root():
    """
    Endpoint raíz para verificar que la API está funcionando.
    """
    return {
        "message": "Reuse API - Sistema de Intercambio Sostenible PUCE",
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Endpoint de health check para monitoreo.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Evento ejecutado al iniciar la aplicación.
    """
    print(f"🚀 Reuse API v{settings.APP_VERSION} iniciada", flush=True)
    print(f"📚 Documentación disponible en: /docs", flush=True)
    print(f"🔧 Modo debug: {settings.DEBUG}", flush=True)

    # Inicializar datos (crear admin si no existe)
    try:
        run_initialization()
    except Exception as e:
        print(f"❌ Error en inicialización: {e}")
        import traceback
        traceback.print_exc()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento ejecutado al apagar la aplicación.
    """
    print("👋 Reuse API detenida")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
