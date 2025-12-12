
from pydantic import BaseModel
from typing import Optional
import json

class Result(BaseModel):
    score: float
    l2_score: Optional[float] = None

try:
    r = Result(score=float("nan"), l2_score=1.5)
    print(f"Model: {r}")
    print(f"JSON: {r.model_dump_json()}")
except Exception as e:
    print(f"Error: {e}")
