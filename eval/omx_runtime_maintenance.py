from __future__ import annotations

import argparse
import json
import shutil
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
HOME = Path.home()
CODEX_DIR = HOME / ".codex"
OMX_DIR = CODEX_DIR / ".omx"
STATE_DIR = OMX_DIR / "state"
NOTEPAD_PATH = OMX_DIR / "notepad.json"
SNAPSHOT_ROOT = SCRIPT_DIR / "snapshots"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat()


@dataclass
class JsonHealth:
    path: str
    valid: bool
    bytes: int
    active: bool | None = None
    age_hours: float | None = None
    error: str | None = None


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"{exc.msg} at line {exc.lineno} column {exc.colno}"


def audit_config(config_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(config_path),
        "exists": config_path.exists(),
        "omx_configured": False,
        "omx_server_path": None,
        "omx_server_exists": False,
    }
    if not config_path.exists():
        return result

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    omx_cfg = data.get("mcp_servers", {}).get("omx")
    if not omx_cfg:
        return result

    result["omx_configured"] = True
    args = omx_cfg.get("args", [])
    server_path = None
    for arg in args:
        if isinstance(arg, str) and arg.lower().endswith(("server.mjs", "server.js", "server.ts")):
            server_path = arg
            break
    result["omx_server_path"] = server_path
    result["omx_server_exists"] = bool(server_path and Path(server_path).exists())
    return result


def audit_state(state_dir: Path) -> dict[str, Any]:
    health: list[JsonHealth] = []
    if not state_dir.exists():
        return {"path": str(state_dir), "exists": False, "files": []}

    now = utc_now()
    for path in sorted(state_dir.glob("*.json")):
        data, error = read_json(path)
        stat = path.stat()
        age_hours = (now - datetime.fromtimestamp(stat.st_mtime, timezone.utc)).total_seconds() / 3600.0
        active = bool(isinstance(data, dict) and data.get("active")) if data is not None else None
        health.append(
            JsonHealth(
                path=str(path),
                valid=error is None,
                bytes=stat.st_size,
                active=active,
                age_hours=round(age_hours, 2),
                error=error,
            )
        )

    return {
        "path": str(state_dir),
        "exists": True,
        "files": [asdict(item) for item in health],
        "invalid_files": [asdict(item) for item in health if not item.valid],
        "stale_active_files": [
            asdict(item)
            for item in health
            if item.valid and item.active and item.age_hours is not None and item.age_hours > 24
        ],
    }


def audit_notepad(notepad_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(notepad_path),
        "exists": notepad_path.exists(),
        "valid": False,
        "schema_version": None,
        "workspace_scoped": False,
        "working_count": 0,
        "manual_count": 0,
        "error": None,
    }
    if not notepad_path.exists():
        return result

    data, error = read_json(notepad_path)
    if error is not None:
        result["error"] = error
        return result

    result["valid"] = True
    if isinstance(data, dict):
        result["schema_version"] = data.get("version")
        result["workspace_scoped"] = "workspaces" in data
        working = data.get("working", [])
        manual = data.get("manual", [])
        result["working_count"] = len(working) if isinstance(working, list) else 0
        result["manual_count"] = len(manual) if isinstance(manual, list) else 0
    return result


def build_audit_report() -> dict[str, Any]:
    config = audit_config(CODEX_DIR / "config.toml")
    state = audit_state(STATE_DIR)
    notepad = audit_notepad(NOTEPAD_PATH)
    return {
        "generated_at": iso_now(),
        "config": config,
        "state": state,
        "notepad": notepad,
        "summary": {
            "omx_runtime_ready": bool(config["omx_configured"] and config["omx_server_exists"]),
            "invalid_state_files": len(state.get("invalid_files", [])),
            "stale_active_files": len(state.get("stale_active_files", [])),
            "workspace_scoped_notepad": bool(notepad["workspace_scoped"]),
        },
    }


def snapshot(target_root: Path) -> Path:
    snap_dir = target_root / f"{timestamp()}_runtime_snapshot"
    snap_dir.mkdir(parents=True, exist_ok=False)

    shutil.copytree(CODEX_DIR / "skills", snap_dir / "skills")
    if OMX_DIR.exists():
        shutil.copytree(OMX_DIR, snap_dir / ".omx")
    shutil.copy2(CODEX_DIR / "config.toml", snap_dir / "config.toml")

    manifest = {
        "created_at": iso_now(),
        "snapshot_root": str(snap_dir),
        "contents": ["skills", ".omx", "config.toml"],
    }
    (snap_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snap_dir


def sanitize_runtime() -> dict[str, Any]:
    OMX_DIR.mkdir(parents=True, exist_ok=True)
    archive_dir = OMX_DIR / "archive" / f"{timestamp()}_sanitize"
    archive_dir.mkdir(parents=True, exist_ok=False)

    old_notepad_data = None
    if NOTEPAD_PATH.exists():
        old_notepad_data, _ = read_json(NOTEPAD_PATH)
        shutil.copy2(NOTEPAD_PATH, archive_dir / "notepad.legacy.json")
        NOTEPAD_PATH.unlink()

    if STATE_DIR.exists():
        shutil.copytree(STATE_DIR, archive_dir / "state")
        shutil.rmtree(STATE_DIR)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    working_count = 0
    manual_count = 0
    if isinstance(old_notepad_data, dict):
        old_working = old_notepad_data.get("working", [])
        old_manual = old_notepad_data.get("manual", [])
        if isinstance(old_working, list):
            working_count = len(old_working)
        if isinstance(old_manual, list):
            manual_count = len(old_manual)

    clean_notepad = {
        "version": 2,
        "active_workspace": "__global__",
        "working": [],
        "manual": [],
        "workspaces": {
            "__global__": {
                "working": [],
                "manual": [],
            }
        },
        "legacy_archive": {
            "archived_at": iso_now(),
            "path": str(archive_dir / "notepad.legacy.json"),
            "working_count": working_count,
            "manual_count": manual_count,
        },
    }
    NOTEPAD_PATH.write_text(
        json.dumps(clean_notepad, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = build_audit_report()
    report["sanitize_archive"] = str(archive_dir)
    (OMX_DIR / "runtime-health.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and sanitize local omx runtime files")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser("audit", help="Print a runtime health report")
    audit_parser.add_argument("--output", default="", help="Optional JSON output path")

    snapshot_parser = sub.add_parser("snapshot", help="Create a snapshot of current omx files")
    snapshot_parser.add_argument("--root", default=str(SNAPSHOT_ROOT), help="Snapshot root directory")

    sanitize_parser = sub.add_parser("sanitize", help="Archive stale runtime files and rebuild a clean local state")
    sanitize_parser.add_argument("--output", default="", help="Optional JSON output path")

    args = parser.parse_args()

    if args.command == "audit":
        report = build_audit_report()
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        print(payload)
        return

    if args.command == "snapshot":
        snap_dir = snapshot(Path(args.root))
        print(str(snap_dir))
        return

    report = sanitize_runtime()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
