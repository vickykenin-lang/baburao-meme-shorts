# Baburao Meme Shorts

Automated GitHub-based generator for **original, family-friendly 20–30 second Hindi/Hinglish comedy shorts** inspired by Baburao-style comic timing, without copying movie dialogue or scenes.

## What the system does

1. Loads the canonical writing rules from `SYSTEM_PROMPT.md`.
2. Reads the most recent topics from `output/history.json`.
3. Sends the prompt + recent-topic context to an Amazon Bedrock model through the Bedrock Runtime `Converse` API.
4. Requires exactly one JSON object with `hook`, `full_script`, `caption`, five `hashtags`, and `topic`.
5. Validates the result and retries up to 3 times when JSON/schema/topic-repeat validation fails.
6. Saves each accepted script under `output/generated/` and updates topic history.
7. GitHub Actions runs the generator every day at **09:00 IST** and can also be started manually.

## Repository structure

```text
.
├── .github/workflows/generate-short.yml
├── output/
│   ├── generated/               # generated scripts appear here
│   └── history.json             # rolling topic memory
├── src/generate_script.py       # generator + validator + persistence
├── tests/test_validation.py     # validation tests
├── SYSTEM_PROMPT.md             # canonical master prompt
├── requirements.txt
└── README.md
```

## Required GitHub configuration

Do **not** commit credentials.

### Repository Secrets

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` — only if your AWS credentials require it

### Repository Variables

- `AWS_REGION` — defaults to `us-east-1`
- `BEDROCK_MODEL_ID` — defaults to `zai.glm-4.7-flash`

The configured AWS identity must have permission to invoke the selected Bedrock model.

> Important: the source prompt names `zai.glm-4.7-flash` / “Bedrock Mantle”. The exact Bedrock model identifier and regional availability must match the AWS account being used. Keep `BEDROCK_MODEL_ID` configurable rather than hard-coding credentials or account-specific values.

## Manual run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
python src/generate_script.py
```

For a local live generation, export AWS credentials/region and optionally `BEDROCK_MODEL_ID` first.

## Output example

Each generated file is strict JSON:

```json
{
  "hook": "...",
  "full_script": "...",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "topic": "unique_topic_label"
}
```

## Safety and originality rules

The canonical system prompt requires original content, no copied/paraphrased movie dialogue, family-friendly language, no jokes targeting named public figures, and no politics/religion/caste/sensitive communal topics. `SYSTEM_PROMPT.md` remains the source of truth for those creative rules.
