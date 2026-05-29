"""
LLM writer: two-step pipeline.
1. Extract the best hook from scraped context.
2. Write a personalized email using that hook.
Auto-retries if personalization_score < 7.
"""

import json
import re
from groq import Groq

from src.prompts.email_prompts import (
    HOOK_EXTRACTION_SYSTEM,
    HOOK_EXTRACTION_USER,
    EMAIL_WRITING_SYSTEM,
    EMAIL_WRITING_USER,
    SCORE_RETRY_USER,
)

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 800


def _call_llm(client: Groq, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content if response.choices else ""
    return (content or "").strip()


def _parse_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling minor formatting issues."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(raw)


def extract_hook(client: Groq, context: str) -> dict:
    """
    Step 1: Extract the single best hook from company context.
    Returns dict with hook, hook_type, confidence.
    Falls back to generic hook on parse failure.
    """
    raw = _call_llm(
        client,
        HOOK_EXTRACTION_SYSTEM,
        HOOK_EXTRACTION_USER.format(context=context),
    )
    try:
        return _parse_json(raw)
    except (json.JSONDecodeError, KeyError):
        return {
            "hook": "your company's focus on delivering real value to customers",
            "hook_type": "generic",
            "confidence": 3,
        }


def write_email(
    client: Groq,
    lead: dict,
    hook_data: dict,
    your_name: str = "Anshi",
    your_product: str = "Humanoid — AI-powered marketing automation for SaaS teams",
) -> dict:
    """
    Step 2: Write personalized cold email using the hook.
    Auto-retries once if score < 7.
    Returns dict with subject, body, personalization_score, retried.
    """
    user_prompt = EMAIL_WRITING_USER.format(
        name=lead["name"],
        role=lead["role"],
        company=lead["company"],
        hook=hook_data["hook"],
        hook_type=hook_data["hook_type"],
        your_product=your_product,
        your_name=your_name,
    )

    raw = _call_llm(client, EMAIL_WRITING_SYSTEM, user_prompt)

    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, KeyError):
        result = {
            "subject": f"quick question, {lead['name'].split()[0]}",
            "body": raw,
            "personalization_score": 5,
        }

    result["retried"] = False

    # Auto-retry if score is low
    score = result.get("personalization_score", 5)
    if isinstance(score, (int, float)) and score < 7:
        retry_prompt = SCORE_RETRY_USER.format(
            score=score,
            original_email=result.get("body", ""),
            hook=hook_data["hook"],
            name=lead["name"],
            role=lead["role"],
            company=lead["company"],
        )
        retry_raw = _call_llm(client, EMAIL_WRITING_SYSTEM, retry_prompt)
        try:
            retry_result = _parse_json(retry_raw)
            retry_result["retried"] = True
            return retry_result
        except (json.JSONDecodeError, KeyError):
            pass

    return result
