import os
import grpc
import codecs
import hashlib
import json

from flask import Flask, request, jsonify, Response
from typing import Optional

# LND protobufs
from lnd_grpc import rpc_pb2 as ln
from lnd_grpc import rpc_pb2_grpc as lnrpc

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

LND_RPC_HOST = os.getenv("LND_RPC_HOST", "localhost:10009")

MACAROON_PATH = os.getenv(
    "LND_MACAROON",
    os.path.expanduser(
        "~/Library/Application Support/Lnd/data/chain/bitcoin/mainnet/admin.macaroon"
    ),
)

TLS_CERT_PATH = os.getenv(
    "LND_TLS_CERT",
    os.path.expanduser("~/Library/Application Support/Lnd/tls.cert"),
)

PRICE_SATS = 30
INVOICE_EXPIRY = 3600  # 1 hour

# ────────────────────────────────────────────────
# APP & GLOBALS
# ────────────────────────────────────────────────

app = Flask(__name__)

# Persistent LND stub (lazy initialized)
_lnd_stub: Optional[lnrpc.LightningStub] = None


# ────────────────────────────────────────────────
# LND CONNECTION
# ────────────────────────────────────────────────

def get_lnd_stub() -> lnrpc.LightningStub:
    global _lnd_stub

    if _lnd_stub is not None:
        return _lnd_stub

    # Read macaroon
    with open(MACAROON_PATH, "rb") as f:
        macaroon = codecs.encode(f.read(), "hex").decode()

    # Read TLS cert
    with open(TLS_CERT_PATH, "rb") as f:
        cert = f.read()

    def metadata_callback(context, callback):
        callback([("macaroon", macaroon)], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    ssl_creds = grpc.ssl_channel_credentials(cert)
    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

    channel = grpc.secure_channel(LND_RPC_HOST, composite_creds)
    _lnd_stub = lnrpc.LightningStub(channel)

    return _lnd_stub


# ────────────────────────────────────────────────
# L402 PAYMENT VALIDATION
# ────────────────────────────────────────────────

def verify_l402_payment(auth_header: str) -> bool:
    """
    Verifies payment using preimage sent in Authorization header.
    Supports:
        Authorization: L402 <preimage>
        Authorization: L402 macaroon:preimage
    """
    if not auth_header or not auth_header.startswith("L402 "):
        return False

    try:
        token = auth_header.replace("L402 ", "").strip()

        if ":" in token:
            # macaroon:preimage format → take the part after last :
            preimage_hex = token.split(":", 1)[-1]
        else:
            preimage_hex = token

        preimage = bytes.fromhex(preimage_hex)
        r_hash = hashlib.sha256(preimage).digest()

        stub = get_lnd_stub()
        payment_hash = ln.PaymentHash(r_hash=r_hash)
        invoice = stub.LookupInvoice(payment_hash)

        # state == 1 → SETTLED
        return invoice.state == 1

    except Exception as e:
        print("Payment verification error:", e)
        return False


# ────────────────────────────────────────────────
# CREATE INVOICE
# ────────────────────────────────────────────────

def create_invoice() -> str:
    stub = get_lnd_stub()

    invoice_req = ln.Invoice(
        value=PRICE_SATS,
        memo="Ωmega Pruner — UTXO pruning & privacy scoring",
        expiry=INVOICE_EXPIRY,
        private=True,
    )

    response = stub.AddInvoice(invoice_req)
    return response.payment_request


# ────────────────────────────────────────────────
# MAIN ENDPOINT
# ────────────────────────────────────────────────

@app.route("/omega-pruner", methods=["GET"])
def omega_pruner():
    address = request.args.get("address")
    if not address:
        return jsonify({
            "status": "error",
            "message": "Missing address parameter",
            "example": "/omega-pruner?address=bc1q..."
        }), 400

    auth_header = request.headers.get("Authorization", "")

    # ───────────────────────────────
    # 1) Valid payment → return analysis result
    # ───────────────────────────────
    if verify_l402_payment(auth_header):
        try:
            # Replace with your actual analysis function
            from engine.analyze import analyze_address

            data = analyze_address(address)

            return Response(
                json.dumps(data, indent=2),
                content_type="application/json"
            )

        except ImportError:
            return jsonify({
                "status": "error",
                "message": "Analysis module not found"
            }), 500
        except Exception as e:
            print("Analysis error:", e)
            return jsonify({
                "status": "error",
                "message": "Error analyzing address"
            }), 500

    # ───────────────────────────────
    # 2) No/invalid payment → return invoice
    # ───────────────────────────────
    try:
        payment_request = create_invoice()

        return jsonify({
            "status": "payment_required",
            "price_sats": PRICE_SATS,
            "invoice": payment_request
        }), 402

    except Exception as e:
        print("LND error:", e)
        return jsonify({
            "status": "error",
            "message": "Error communicating with LND"
        }), 500


# ────────────────────────────────────────────────
# START SERVER
# ────────────────────────────────────────────────

if __name__ == "__main__":
    print("Ωmega Pruner L402 service running")
    print("http://127.0.0.1:8081/omega-pruner?address=bc1qexample...")

    app.run(host="127.0.0.1", port=8081, debug=True)
