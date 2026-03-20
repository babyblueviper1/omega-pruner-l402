from typing import Dict, Any, List

from .fetch import get_utxos
from .classify import _classify_utxo
from .enrich import _enrich_utxos
from .fees import estimate_tx_economics
from .privacy import calculate_privacy_score, estimate_coinjoin_mixes_needed


def analyze_address(address: str, fee_rate: int = 15) -> Dict[str, Any]:
    """
    Main production entry point for Ωmega Pruner.

    Pipeline:
        1. Fetch UTXOs
        2. Classify them
        3. Enrich with metadata
        4. Calculate privacy score
        5. Estimate transaction economics
        6. Return machine-readable output (agent-friendly)
    """

    # ─────────────────────────────────────
    # 1) Fetch UTXOs
    # ─────────────────────────────────────
    utxos = get_utxos(address)

    if not utxos:
        return {
            "address": address,
            "utxo_count": 0,
            "error": "No UTXOs found",
        }

    # ─────────────────────────────────────
    # 2) Classify
    # ─────────────────────────────────────
    classified = [_classify_utxo(u) for u in utxos]

    # ─────────────────────────────────────
    # 3) Enrich
    # ─────────────────────────────────────
    enriched = _enrich_utxos(classified)

    # ─────────────────────────────────────
    # 4) Privacy score
    # ─────────────────────────────────────
    privacy_score = calculate_privacy_score(enriched)
    mixes_needed = estimate_coinjoin_mixes_needed(privacy_score)

    # ─────────────────────────────────────
    # 5) Fee economics
    # ─────────────────────────────────────
    fee_data = estimate_tx_economics(enriched, fee_rate)

    # ─────────────────────────────────────
    # 6) Health breakdown
    # ─────────────────────────────────────
    optimal = sum(1 for u in enriched if u["health"] == "optimal")
    medium = sum(1 for u in enriched if u["health"] == "medium")
    legacy = sum(1 for u in enriched if u["health"] == "legacy")

    # ─────────────────────────────────────
    # 7) Final response (designed for AI agents)
    # ─────────────────────────────────────
    return {
        "address": address,
        "utxo_count": len(enriched),
        "privacy_score": privacy_score,
        "coinjoin_needed": mixes_needed,
        "fee_estimate_sats": fee_data["fee_sats"],
        "future_fee_savings_sats": fee_data["future_savings_sats"],
        "health_breakdown": {
            "optimal": optimal,
            "medium": medium,
            "legacy": legacy,
        },
        "utxos": enriched,  # agents can reason over this
    }
