import requests
from typing import List, Dict, Any


# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

TIMEOUT = 10  # seconds
USER_AGENT = "omega-pruner-endpoint/1.0"


# ────────────────────────────────────────────────
# PRIMARY: mempool.space
# ────────────────────────────────────────────────

def _fetch_from_mempool(address: str) -> List[Dict[str, Any]]:
    url = f"https://mempool.space/api/address/{address}/utxo"

    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )

    if response.status_code != 200:
        raise Exception("mempool.space returned non-200")

    data = response.json()

    utxos = []

    for u in data:
        utxos.append({
            "txid": u["txid"],
            "vout": u["vout"],
            "value": u["value"],   # sats
            "confirmed": u["status"]["confirmed"],
            "block_height": u["status"].get("block_height"),
        })

    return utxos


# ────────────────────────────────────────────────
# BACKUP: Blockstream API
# ────────────────────────────────────────────────

def _fetch_from_blockstream(address: str) -> List[Dict[str, Any]]:
    url = f"https://blockstream.info/api/address/{address}/utxo"

    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )

    if response.status_code != 200:
        raise Exception("blockstream API returned non-200")

    data = response.json()

    utxos = []

    for u in data:
        utxos.append({
            "txid": u["txid"],
            "vout": u["vout"],
            "value": u["value"],
            "confirmed": u["status"]["confirmed"],
            "block_height": u["status"].get("block_height"),
        })

    return utxos


# ────────────────────────────────────────────────
# PUBLIC FUNCTION USED BY ENGINE
# ────────────────────────────────────────────────

def get_utxos(address: str) -> List[Dict[str, Any]]:
    """
    Production-safe UTXO fetcher.

    Strategy:
        1) Try mempool.space
        2) If it fails → fallback to blockstream
        3) If both fail → return empty list (no crash)
    """

    # Try primary
    try:
        return _fetch_from_mempool(address)
    except Exception as e:
        print("Primary API failed:", e)

    # Try fallback
    try:
        return _fetch_from_blockstream(address)
    except Exception as e:
        print("Fallback API failed:", e)

    # Last resort
    return []
