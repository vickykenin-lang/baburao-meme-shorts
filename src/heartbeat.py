import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = ROOT / "runtime"
STATUS_FILE = STATUS_DIR / "heartbeat.json"
REQUIRED_GOVERNANCE = ["SOUL.md", "OBJECTIVE.md", "GOVERNANCE.md", "SYSTEM_PROMPT.md"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def latest_generated():
    generated = ROOT / "output" / "generated"
    if not generated.exists():
        return None
    files = sorted(generated.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    path = files[0]
    return {
        "path": str(path.relative_to(ROOT)),
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }


def credential_presence():
    # Presence only. Never emit credential values.
    return {
        "aws_access_key_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "aws_secret_key_configured": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
        "aws_session_token_configured": bool(os.getenv("AWS_SESSION_TOKEN")),
    }


def build_status():
    missing = [name for name in REQUIRED_GOVERNANCE if not (ROOT / name).exists()]
    creds = credential_presence()
    provider_ready = creds["aws_access_key_configured"] and creds["aws_secret_key_configured"]
    latest = latest_generated()

    blockers = []
    if missing:
        blockers.append("MISSING_GOVERNANCE_FILES")
    if not provider_ready:
        blockers.append("AWS_BEDROCK_CREDENTIALS_UNAVAILABLE")

    runtime_health = "HEALTHY" if not blockers else "DEGRADED"
    department_state = "READY_FOR_DIAGNOSIS" if not missing else "BLOCKED"

    return {
        "schema_version": 1,
        "department": "BABU_RAO",
        "timestamp_utc": utc_now(),
        "governance_state": "FOUNDATION_GOVERNED" if not missing else "INVALID",
        "objective_alignment": "CHECKED" if not missing else "NOT_VERIFIED",
        "department_state": department_state,
        "runtime_health": runtime_health,
        "production_provider_ready": provider_ready,
        "credential_presence": creds,
        "last_successful_production": latest,
        "blockers": blockers,
        "next_autonomous_action": (
            "RUN_PRODUCTION_AND_RECORD_EVIDENCE" if provider_ready and not missing
            else "WAIT_FOR_REQUIRED_EXTERNAL_DEPENDENCY_WHILE_CONTINUING_HEALTH_REPORTING"
        ),
        "victor_communication_status": "NOT_IMPLEMENTED_STEP_3",
        "evidence": {"git_head": git_head(), "heartbeat_file": "runtime/heartbeat.json"},
    }


def main():
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    status = build_status()
    STATUS_FILE.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
