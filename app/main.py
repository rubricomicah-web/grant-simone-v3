from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, organizations, grants, proposals, workflows, applications, memory, tenants, billing, admin, analytics, notifications, agents, documents, automation, monitoring, search, outcomes, usage

try:
    import sentry_sdk
except Exception:
    sentry_sdk = None

if settings.sentry_dsn and sentry_sdk:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env, traces_sample_rate=0.05)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Mogul Grant System API",
    version="3.1.0",
    description="Enterprise-grade Autonomous AI Funding Intelligence Platform. Clean modules: Auth, Organizations, Grants, Proposals, Applications, Memory, Workflows, Billing, Notifications, Analytics, Admin.",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if settings.security_headers_enabled:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'")
    return response

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health", tags=["System"])
def health():
    return {"ok": True, "app": settings.app_name, "env": settings.app_env}

@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return RedirectResponse(url="/signup.html")

@app.get("/logout", include_in_schema=False)
def logout_page():
    return RedirectResponse(url="/signup.html?mode=login")

for router in [auth.router, organizations.router, grants.router, proposals.router, applications.router, workflows.router, agents.router, documents.router, automation.router, monitoring.router, search.router, outcomes.router, usage.router, memory.router, notifications.router, tenants.router, billing.router, analytics.router, admin.router]:
    app.include_router(router, prefix="/api")

app.mount("/", StaticFiles(directory="public", html=True), name="public")
