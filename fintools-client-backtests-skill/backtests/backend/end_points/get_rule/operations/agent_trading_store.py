from datetime import datetime

from db.models import AgentTrading


def upsert_agent_trading(
    db,
    *,
    rule_id: int,
    stock_code: str,
    trading_date,
    trading_type: str,
    trading_amount: float = 0,
    created_at=None,
    updated_at=None,
    commit: bool = True,
):
    normalized_stock_code = stock_code.split(".")[0] if "." in str(stock_code) else str(stock_code)
    created_value = created_at or datetime.now()
    updated_value = updated_at or created_value

    existing = (
        db.session.query(AgentTrading)
        .filter(AgentTrading.rule_id == rule_id)
        .filter(AgentTrading.stock == normalized_stock_code)
        .filter(AgentTrading.trading_date == trading_date)
        .first()
    )

    inserted = False
    updated = False
    if existing:
        if existing.trading_type != trading_type:
            existing.trading_type = trading_type
            updated = True
        if existing.trading_amount != trading_amount:
            existing.trading_amount = trading_amount
            updated = True
        if existing.updated_at != updated_value:
            existing.updated_at = updated_value
            updated = True
        if existing.created_at is None and created_value is not None:
            existing.created_at = created_value
            updated = True
        record = existing
    else:
        record = AgentTrading(
            rule_id=rule_id,
            stock=normalized_stock_code,
            trading_date=trading_date,
            trading_type=trading_type,
            trading_amount=trading_amount,
            created_at=created_value,
            updated_at=updated_value,
        )
        db.session.add(record)
        inserted = True

    if commit:
        db.session.commit()
    else:
        db.session.flush()

    return {
        "record": record,
        "inserted": inserted,
        "updated": updated,
        "skipped": (not inserted and not updated),
    }
