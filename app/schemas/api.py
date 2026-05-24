from pydantic import BaseModel, EmailStr, Field
from typing import Any

class RegisterRequest(BaseModel):
    tenant_name: str = "Mogul Grant System"
    tenant_slug: str = "default"
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    account_type: str = "individual"  # individual, business, nonprofit, agency
    plan: str = "individual_elite"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str = "default"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RegisterCheckoutResponse(BaseModel):
    access_token: str
    refresh_token: str
    checkout_url: str | None = None
    payment_required: bool = False
    plan: str
    token_type: str = "bearer"

class CheckoutRequest(BaseModel):
    plan: str = "individual_elite"

class OrganizationCreate(BaseModel):
    name: str
    profile_type: str = "individual"
    org_type: str = "individual"
    state: str | None = None
    city: str | None = None
    county: str | None = None
    zip_code: str | None = None
    years_in_operation: int | None = None
    age_range: str | None = None
    education_level: str | None = None
    employment_status: str | None = None
    household_size: int | None = None
    annual_income: float | None = None
    veteran_status: bool = False
    disability_status: bool = False
    mission: str | None = None
    funding_goals: str | None = None
    annual_budget: float | None = None
    eligibility_tags: list[str] = []
    metadata_json: dict[str, Any] = {}

class GrantSearchRequest(BaseModel):
    query: str
    state: str | None = None
    organization_id: int | None = None
    audience: str = "all"  # all, individual, organization
    category: str | None = None
    limit: int = 10

class ProposalRequest(BaseModel):
    organization_id: int
    grant_id: int | None = None
    grant_name: str | None = None
    requested_amount: float | None = None
    funding_purpose: str | None = None

class WorkflowStartRequest(BaseModel):
    workflow: str = "full_grant_pipeline"
    organization_id: int | None = None
    grant_id: int | None = None
    context: dict[str, Any] = {}

class TenantUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    background_color: str | None = None
    audience_mode: str | None = None

class MemoryCreate(BaseModel):
    organization_id: int
    memory_type: str
    content: str
    importance: float = 0.5

class ApplicationCreate(BaseModel):
    organization_id: int
    grant_id: int
    proposal_id: int | None = None
    notes: str | None = None


class NotificationSettingsUpdate(BaseModel):
    email_grant_matches: bool = True
    platform_grant_matches: bool = True
    email_deadline_reminders: bool = True
    minimum_match_score: float = 75
    categories_json: list[str] = []
    states_json: list[str] = []


class ProposalUpdate(BaseModel):
    title: str | None = None
    body: str

class IngestRequest(BaseModel):
    query: str = "small business nonprofit education housing benefits"
    state: str | None = None
    limit: int = 25


class ResendVerificationRequest(BaseModel):
    email: EmailStr
    tenant_slug: str = "default"

class PasswordResetRequest(BaseModel):
    email: EmailStr
    tenant_slug: str = "default"

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None
    plan: str | None = None

class UsageRecordRequest(BaseModel):
    event_type: str
    quantity: int = 1
    metadata_json: dict[str, Any] = {}
