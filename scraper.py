"""
Scraper: pulls raw text context from a company website.
Uses Playwright for JS-rendered pages. Falls back gracefully on errors.
"""

import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def scrape_website(url: str, timeout_ms: int = 12000) -> dict:
    """
    Scrape a company homepage and return structured text context.
    Returns a dict with keys: title, description, hero_text, about_text, raw_snippet
    """
    result = {
        "url": url,
        "title": "",
        "description": "",
        "hero_text": "",
        "about_text": "",
        "raw_snippet": "",
        "error": None,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(2000)
            except PlaywrightTimeout:
                result["error"] = f"Timeout loading {url}"
                browser.close()
                return result

            # Page title
            result["title"] = page.title()

            # Meta description
            meta = page.query_selector('meta[name="description"]')
            if meta:
                result["description"] = meta.get_attribute("content") or ""

            # Hero / above-fold text (h1, h2, first large p)
            hero_parts = []
            for selector in ["h1", "h2", "header p", "[class*='hero'] p"]:
                els = page.query_selector_all(selector)
                for el in els[:3]:
                    text = (el.inner_text() or "").strip()
                    if text and len(text) > 10:
                        hero_parts.append(text)
            result["hero_text"] = " | ".join(hero_parts[:5])

            # About / mission section
            about_parts = []
            for selector in [
                "[class*='about'] p",
                "[class*='mission'] p",
                "[class*='vision'] p",
                "section p",
                "main p",
            ]:
                els = page.query_selector_all(selector)
                for el in els[:4]:
                    text = (el.inner_text() or "").strip()
                    if text and len(text) > 40:
                        about_parts.append(text)
                if about_parts:
                    break
            result["about_text"] = " ".join(about_parts[:3])

            # Raw text snippet (first 800 chars of body text as fallback)
            body = page.query_selector("body")
            if body:
                raw = (body.inner_text() or "")
                raw = re.sub(r"\s+", " ", raw).strip()
                result["raw_snippet"] = raw[:800]

            browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result


def format_context_for_llm(lead: dict, scraped: dict) -> str:
    """
    Combine lead info + scraped data into a clean context string for the LLM.
    """
    lines = [
        f"PROSPECT: {lead['name']}",
        f"ROLE: {lead['role']} at {lead['company']}",
        f"WEBSITE: {lead['website']}",
        "",
        "--- SCRAPED COMPANY CONTEXT ---",
    ]

    if scraped.get("title"):
        lines.append(f"Page title: {scraped['title']}")
    if scraped.get("description"):
        lines.append(f"Meta description: {scraped['description']}")
    if scraped.get("hero_text"):
        lines.append(f"Hero text: {scraped['hero_text']}")
    if scraped.get("about_text"):
        lines.append(f"About/mission: {scraped['about_text']}")
    if scraped.get("raw_snippet") and not scraped.get("hero_text"):
        lines.append(f"Page content: {scraped['raw_snippet'][:400]}")
    if scraped.get("error"):
        lines.append(f"[Scrape note: {scraped['error']} — using company name only]")

    return "\n".join(lines)
