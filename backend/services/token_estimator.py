from backend.config import load_settings


def _count_tokens_rough(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    settings = load_settings()
    pricing = settings.get("token_pricing", {})
    model_pricing = pricing.get(model, {"input_per_1m": 3.0, "output_per_1m": 15.0})
    cost = (input_tokens / 1_000_000) * model_pricing["input_per_1m"]
    cost += (output_tokens / 1_000_000) * model_pricing["output_per_1m"]
    return round(cost, 6)


def estimate_and_record(operation_type: str, model: str, prompt_text: str, expected_output_tokens: int = 200):
    input_tokens = _count_tokens_rough(prompt_text)
    cost = estimate_cost(model, input_tokens, expected_output_tokens)

    try:
        from backend.db import SessionLocal
        from backend.models import TokenUsageEstimate
        db = SessionLocal()
        record = TokenUsageEstimate(
            operation_type=operation_type,
            model_name=model,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=expected_output_tokens,
            estimated_cost=cost,
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception:
        pass

    return {"input_tokens": input_tokens, "output_tokens": expected_output_tokens, "cost": cost}


def get_usage_summary() -> dict:
    try:
        from backend.db import SessionLocal
        from backend.models import TokenUsageEstimate
        from sqlalchemy import func
        db = SessionLocal()
        rows = db.query(
            TokenUsageEstimate.operation_type,
            func.sum(TokenUsageEstimate.estimated_input_tokens).label("total_input"),
            func.sum(TokenUsageEstimate.estimated_output_tokens).label("total_output"),
            func.sum(TokenUsageEstimate.estimated_cost).label("total_cost"),
            func.count().label("count"),
        ).group_by(TokenUsageEstimate.operation_type).all()
        db.close()

        return {
            "by_operation": [
                {
                    "operation": r.operation_type,
                    "total_input_tokens": r.total_input,
                    "total_output_tokens": r.total_output,
                    "estimated_cost_usd": round(r.total_cost, 6),
                    "count": r.count,
                }
                for r in rows
            ]
        }
    except Exception as e:
        return {"error": str(e), "by_operation": []}
