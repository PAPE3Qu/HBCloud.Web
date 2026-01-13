from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import time
from typing import List, Dict

from ..config import DATA_ROOT
from .files import write_log

router = APIRouter(prefix="/api/feedbacks", tags=["feedbacks"])

FEEDBACK_PATH = DATA_ROOT / 'feedbacks.json'
FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)


class FeedbackCreate(BaseModel):
  content: str


def _load_all() -> List[Dict]:
  if not FEEDBACK_PATH.exists():
    return []
  try:
    return json.loads(FEEDBACK_PATH.read_text(encoding='utf-8'))
  except Exception:
    return []


def _save_all(items: List[Dict]):
  FEEDBACK_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')


@router.post("", status_code=201)
async def create_feedback(payload: FeedbackCreate, request: Request):
  text = (payload.content or '').strip()
  if not text:
    raise HTTPException(status_code=400, detail='反馈内容不能为空')
  items = _load_all()
  now = time.time()
  fb = {
    'id': int(now * 1000),
    'content': text,
    'created_at': now,
  }
  items.insert(0, fb)
  _save_all(items)
  write_log(f"feedback_create id={fb['id']} from_ip={request.client.host if request.client else ''}")
  return {"success": True}


@router.get("/count")
async def count_feedbacks():
  items = _load_all()
  return {"count": len(items)}
