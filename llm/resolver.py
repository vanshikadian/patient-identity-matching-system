import asyncio
import json

from common.config import get_settings

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    AsyncAnthropic = None


PROMPT_TEMPLATE = """You are a healthcare data analyst specializing in patient identity resolution.

Given two patient records with potentially missing or inconsistent data, determine if they refer to the same person.

Record A:
- Name: {name_a}
- DOB: {dob_a}
- Gender: {gender_a}
- Address: {address_a}
- SSN last 4: {ssn_a}

Record B:
- Name: {name_b}
- DOB: {dob_b}
- Gender: {gender_b}
- Address: {address_b}
- SSN last 4: {ssn_b}

ML confidence score: {ml_score} (uncertain — needs your judgment)

Respond in JSON with match, confidence, and reasoning.
"""


def resolve_ambiguous_pairs(df):
    if df.empty:
        return []
    settings = get_settings()
    if settings.anthropic_api_key and AsyncAnthropic is not None:
        return asyncio.run(_resolve_with_claude(df, settings.anthropic_api_key))
    return [_heuristic_resolution(row) for row in df.to_dict(orient="records")]


async def _resolve_with_claude(df, api_key: str):
    client = AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(50)

    async def worker(row):
        async with semaphore:
            prompt = PROMPT_TEMPLATE.format(
                name_a=f"{row.get('first_name_a', '')} {row.get('last_name_a', '')}".strip(),
                dob_a=row.get("dob_a"),
                gender_a=row.get("gender_a"),
                address_a=row.get("address_a"),
                ssn_a=row.get("ssn_last4_a"),
                name_b=f"{row.get('first_name_b', '')} {row.get('last_name_b', '')}".strip(),
                dob_b=row.get("dob_b"),
                gender_b=row.get("gender_b"),
                address_b=row.get("address_b"),
                ssn_b=row.get("ssn_last4_b"),
                ml_score=row["ml_score"],
            )
            response = await client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            payload = json.loads(text)
            payload["pair_key"] = f'{row["record_a_id"]}:{row["record_b_id"]}'
            return payload

    return await asyncio.gather(*(worker(row) for row in df.to_dict(orient="records")))


def _heuristic_resolution(row: dict) -> dict:
    supporting_signals = [
        row.get("last_name_similarity", 0) > 0.92,
        row.get("first_name_similarity", 0) > 0.86,
        row.get("dob_exact_match", 0) == 1 or row.get("dob_off_by_one", 0) == 1,
        row.get("address_token_overlap", 0) > 0.4,
        row.get("ssn_last4_match", 0) == 1,
    ]
    confidence = min(0.99, 0.45 + 0.1 * sum(int(flag) for flag in supporting_signals))
    match = sum(int(flag) for flag in supporting_signals) >= 3
    return {
        "pair_key": f'{row["record_a_id"]}:{row["record_b_id"]}',
        "match": match,
        "confidence": confidence,
        "reasoning": "Multiple demographic fields align despite inconsistent formatting.",
    }
