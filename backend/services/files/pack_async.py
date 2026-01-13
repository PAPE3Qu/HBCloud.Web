import os
import json
import uuid
import threading
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import HTTPException

from ...services.files import pack as pack_svc


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TMP_PACKS_DIR = PROJECT_ROOT / "data" / "tmp_packs" / "pack_jobs"
TMP_PACKS_DIR.mkdir(parents=True, exist_ok=True)


def _job_file(job_id: str) -> Path:
    return TMP_PACKS_DIR / f"{job_id}.json"


def _write_job(job_id: str, data: Dict[str, Any]):
    f = _job_file(job_id)
    try:
        with f.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False)
    except Exception:
        pass


def _read_job(job_id: str) -> Dict[str, Any]:
    f = _job_file(job_id)
    if not f.exists():
        return {}
    try:
        with f.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def create_job(body: Dict[str, Any], current_user: Dict[str, Any]) -> str:
    job_id = uuid.uuid4().hex
    now = time.time()
    job = {
        "id": job_id,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "owner": current_user.get("phone") or current_user.get("name"),
        "body": body,
        "result": None,
        "error": None,
    }
    _write_job(job_id, job)

    # start background thread
    t = threading.Thread(target=_run_job, args=(job_id, current_user), daemon=True)
    t.start()
    return job_id


def get_job(job_id: str) -> Dict[str, Any]:
    return _read_job(job_id)


def _run_job(job_id: str, current_user: Dict[str, Any]):
    job = _read_job(job_id)
    if not job:
        return
    job["status"] = "working"
    job["updated_at"] = time.time()
    _write_job(job_id, job)

    try:
        # call existing pack_to_temp asynchronously
        body = job.get("body") or {}
        # pack_to_temp is async; run it in new event loop
        result = asyncio.run(pack_svc.pack_to_temp(body, current_user))

        job = _read_job(job_id) or {}
        job["status"] = "ready"
        job["result"] = result
        job["updated_at"] = time.time()
        _write_job(job_id, job)
    except Exception as e:
        job = _read_job(job_id) or {}
        job["status"] = "failed"
        msg = str(e)
        try:
            # try to extract detail from HTTPException
            if isinstance(e, HTTPException):
                msg = e.detail if hasattr(e, "detail") else msg
        except Exception:
            pass
        job["error"] = msg
        job["updated_at"] = time.time()
        _write_job(job_id, job)
