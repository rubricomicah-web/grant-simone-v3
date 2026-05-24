import os
from pydantic_settings import BaseSettings
from pydantic import computed_field, field_validator

class Settings(BaseSettings):
    @field_validator("payment_required", "payments_enabled", "email_notifications_enabled", "browser_automation_enabled", "funding_monitor_enabled", "vector_memory_enabled", "advanced_security_enabled", "weekly_digest_enabled", "email_verification_required", "password_reset_enabled", "security_headers_enabled", mode="before")
    @classmethod
    def parse_bool_env(cls, value):
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            cleaned = value.strip().strip('\"').strip("'").strip().lower()
            if cleaned in {"true", "1", "yes", "y", "on"}:
                return True
            if cleaned in {"false", "0", "no", "n", "off", ""}:
                return False
        return value

    app_name: str = "Mogul Grant System"
    app_env: str = "development"
    database_url: str = "sqlite:///./mogul_grant_system.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 30
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    # Payment mode. Keep false while you do not have Stripe yet.
    # When ready, set PAYMENT_REQUIRED=true and add Stripe keys/price IDs.
    payment_required: bool = False
    # Backward-compatible alias for your current Railway env.
    # If PAYMENT_REQUIRED is not set, PAYMENTS_ENABLED=true will require checkout.
    payments_enabled: bool | None = None
    trial_days: int = 14
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_individual_starter: str | None = None
    stripe_price_individual_pro: str | None = None
    stripe_price_individual_elite: str | None = None
    stripe_price_business_owner: str | None = None
    stripe_price_business_growth: str | None = None
    stripe_price_business_scale: str | None = None
    stripe_price_business_enterprise: str | None = None
    stripe_price_white_label_agency: str | None = None
    stripe_price_white_label_studio: str | None = None
    stripe_price_white_label_platform: str | None = None
    # Backward-compatible old single white-label plan env var
    stripe_price_white_label: str | None = None
    default_success_url: str = "/?payment=success"
    default_cancel_url: str = "/?payment=cancelled"
    frontend_base_url: str = "http://localhost:8000"
    cors_origins: str = "*"

    # Email notifications via Resend
    resend_api_key: str | None = None
    resend_from_email: str = "Mogul Grant System <notifications@yourdomain.com>"
    email_notifications_enabled: bool = True

    # Enterprise modules are deploy-safe and off unless configured.
    browser_automation_enabled: bool = False
    storage_backend: str = "local"  # local or s3/r2
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str | None = None
    funding_monitor_enabled: bool = False
    vector_memory_enabled: bool = True
    advanced_security_enabled: bool = True
    weekly_digest_enabled: bool = False
    email_verification_required: bool = False
    password_reset_enabled: bool = True
    sentry_dsn: str | None = None
    security_headers_enabled: bool = True
    max_login_attempts: int = 8
    lockout_minutes: int = 15
    max_upload_mb: int = 15

    @computed_field
    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def model_post_init(self, __context):
        if "PAYMENT_REQUIRED" not in os.environ and self.payments_enabled is not None:
            self.payment_required = bool(self.payments_enabled)
        if os.getenv("FRONTEND_URL") and not os.getenv("FRONTEND_BASE_URL"):
            self.frontend_base_url = os.getenv("FRONTEND_URL", self.frontend_base_url).rstrip("/")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
