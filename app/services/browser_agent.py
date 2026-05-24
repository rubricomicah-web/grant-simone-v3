"""Approval-gated browser automation foundation.

This never submits applications automatically. It prepares drafts/checklists and returns
a human approval step. Real portal credentials and Playwright can be enabled later.
"""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class BrowserAgentResult:
    status: str
    message: str
    steps: list[str]
    requires_human_approval: bool = True
    portal_session_url: str | None = None


def browser_automation_enabled() -> bool:
    return os.getenv("BROWSER_AUTOMATION_ENABLED", "false").strip().strip('"').lower() in {"true", "1", "yes", "on"}


async def prepare_portal_draft(application_url: str, profile: dict, grant: dict, documents: list[dict]) -> BrowserAgentResult:
    if not browser_automation_enabled():
        return BrowserAgentResult(
            status="prepared_without_browser",
            message="Browser automation is disabled. Mogul Grant System prepared the application packet and checklist for human review.",
            steps=[
                "Open official application link",
                "Review eligibility requirements",
                "Copy prepared proposal sections",
                "Upload required documents",
                "Review all certifications",
                "Submit only after applicant approval",
            ],
        )
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception:
        return BrowserAgentResult(
            status="playwright_not_installed",
            message="BROWSER_AUTOMATION_ENABLED is true but Playwright is not installed. Run: pip install playwright && playwright install chromium",
            steps=[],
        )

    # Safe foundation: open page, verify reachable, stop before form submission.
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(application_url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        await browser.close()
    return BrowserAgentResult(
        status="portal_checked",
        message=f"Portal reached successfully: {title}. Draft packet is ready; submission still requires human approval.",
        steps=["Portal reached", "Application packet prepared", "Human approval required before submission"],
    )
