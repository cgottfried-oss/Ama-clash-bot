from __future__ import annotations

import uuid



def create_trade_offer(sender_id: str, target_id: str, item_id: str):
    return {
        "trade_id": str(uuid.uuid4()),
        "sender_id": sender_id,
        "target_id": target_id,
        "item_id": item_id,
        "accepted": False,
    }



def accept_trade_offer(trade: dict):
    trade["accepted"] = True
    return trade
