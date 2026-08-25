from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "SYSTEM_PROMPT.md"
HISTORY_PATH = ROOT / "output" / "history.json"
OUTPUT_DIR = ROOT / "output" / "generated"
DEFAULT_MODEL_ID = "zai.glm-4.7-flash"
MAX_HISTORY_TOPICS = 50
CONTEXT_TOPIC_COUNT = 10
MAX_ATTEMPTS = 3

REQUIRED_KEYS = {"hook", "full_script", "caption", "hashtags", "topic"}


def load_system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise RuntimeError("SYSTEM_PROMPT.md does not contain the expected fenced prompt block")
    return match.group(1).strip()


def load_history() -> dict[str, list[str]]:
    if not HISTORY_PATH.exists():
        return {"topics": []}
    data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    topics = data.get("topics", [])
    if not isinstance(topics, list):
        raise ValueError("output/history.json must contain a 'topics' list")
    return {"topics": [str(topic) for topic in topics]}


def build_user_prompt(history: dict[str, list[str]], correction: str | None = None) -> str:
    recent = history["topics"][-CONTEXT_TOPIC_COUNT:]
    parts = [
        "Aaj ka ek naya original short generate karo.",
        "Pichle topics repeat mat karna.",
        "Recent topics: " + (", ".join(recent) if recent else "none yet"),
        "Return only the strict JSON object required by the system prompt.",
    ]
    if correction:
        parts.append("Previous response failed validation. Fix these issues: " + correction)
    return "\n".join(parts)


def extract_text(response: dict[str, Any]) -> str:
    try:
        blocks = response["output"]["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unexpected Bedrock Converse response shape") from exc

    text_parts = [block["text"] for block in blocks if isinstance(block, dict) and "text" in block]
    if not text_parts:
        raise ValueError("Model response contained no text")
    return "\n".join(text_parts).strip()


def parse_json_object(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Model output must be one JSON object")
    return parsed


def validate_script(data: dict[str, Any], history: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_KEYS - set(data)
    extra = set(data) - REQUIRED_KEYS
    if missing:
        errors.append("missing keys: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unexpected keys: " + ", ".join(sorted(extra)))

    for key in ("hook", "full_script", "caption", "topic"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            errors.append(f"{key} must be a non-empty string")

    hashtags = data.get("hashtags")
    if not isinstance(hashtags, list) or len(hashtags) != 5:
        errors.append("hashtags must be a list of exactly 5 items")
    elif any(not isinstance(tag, str) or not tag.startswith("#") for tag in hashtags):
        errors.append("every hashtag must be a string starting with #")

    topic = str(data.get("topic", "")).strip().lower()
    recent = {item.strip().lower() for item in history["topics"][-CONTEXT_TOPIC_COUNT:]}
    if topic and topic in recent:
        errors.append("topic repeats one of the recent topics")

    return errors


def invoke_model(system_prompt: str, user_prompt: str) -> str:
    import boto3

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    model_id = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={
            "maxTokens": int(os.getenv("MAX_TOKENS", "900")),
            "temperature": float(os.getenv("TEMPERATURE", "0.9")),
        },
    )
    return extract_text(response)


def generate_valid_script() -> dict[str, Any]:
    system_prompt = load_system_prompt()
    history = load_history()
    correction: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = invoke_model(system_prompt, build_user_prompt(history, correction))
        try:
            data = parse_json_object(raw)
            errors = validate_script(data, history)
        except (json.JSONDecodeError, ValueError) as exc:
            data = {}
            errors = [str(exc)]

        if not errors:
            return data

        correction = "; ".join(errors)
        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(f"Model failed validation after {MAX_ATTEMPTS} attempts: {correction}")

    raise RuntimeError("unreachable")


def persist(script: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y-%m-%d_%H%M%S_UTC.json")
    output_path = OUTPUT_DIR / filename
    output_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history = load_history()
    history["topics"].append(script["topic"])
    history["topics"] = history["topics"][-MAX_HISTORY_TOPICS:]
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    script = generate_valid_script()
    path = persist(script)
    print(json.dumps(script, ensure_ascii=False, indent=2))
    print(f"Saved: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
