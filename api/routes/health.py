from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/health")
def health(request: Request):
    startup_error = getattr(request.app.state, "startup_error", None)
    if startup_error:
        return {"status": "degraded", "startup_error": startup_error}
    return {"status": "ok"}
