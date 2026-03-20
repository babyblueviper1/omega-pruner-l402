import os
import grpc
import hashlib
import json
from flask import Flask, request, jsonify, Response
from typing import Optional
import base64

# LND protobufs
from lnd_grpc import rpc_pb2 as ln
from lnd_grpc import rpc_pb2_grpc as lnrpc

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

LND_RPC_HOST = os.getenv("LND_RPC_HOST", "localhost:10009")
PRICE_SATS = 30
INVOICE_EXPIRY = 3600  # 1 hour

# ────────────────────────────────────────────────
# APP & GLOBALS
# ────────────────────────────────────────────────

app = Flask(__name__)
_lnd_stub: Optional[lnrpc.LightningStub] = None

# ────────────────────────────────────────────────
# LND CONNECTION
# ────────────────────────────────────────────────

def get_lnd_stub() -> lnrpc.LightningStub:
    global _lnd_stub
    if _lnd_stub is not None:
        return _lnd_stub

    # Load macaroon from env (hex)
    macaroon_hex = os.getenv("LND_MACAROON_HEX")
    if not macaroon_hex:
        raise ValueError("LND_MACAROON_HEX environment variable is missing")

    # Load TLS cert from env (base64)
    tls_cert_b64 = os.getenv("LND_TLS_CERT_BASE64")
    if not tls_cert_b64:
        raise ValueError("LND_TLS_CERT_BASE64 environment variable is missing")
    cert_bytes = base64.b64decode(tls_cert_b64)

    # gRPC credentials
    def metadata_callback(context, callback):
        callback([("macaroon", macaroon_hex)], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    ssl_creds = grpc.ssl_channel_credentials(cert_bytes)
    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

    channel = grpc.secure_channel(LND_RPC_HOST, composite_creds)
    _lnd_stub = lnrpc.LightningStub(channel)
    return _lnd_stub

# ────────────────────────────────────────────────
# L402 PAYMENT VALIDATION
# ────────────────────────────────────────────────

def verify_l402_payment(auth_header: str) -> bool:
    if not auth_header or not auth_header.startswith("L402 "):
        return False

    try:
        token = auth_header.replace("L402 ", "").strip()
        preimage_hex = token.split(":", 1)[-1] if ":" in token else token
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

    if verify_l402_payment(auth_header):
        try:
            # Replace with your actual analysis function
            from engine.analyze import analyze_address
            data = analyze_address(address)
            return Response(json.dumps(data, indent=2), content_type="application/json")

        except ImportError:
            return jsonify({"status": "error", "message": "Analysis module not found"}), 500
        except Exception as e:
            print("Analysis error:", e)
            return jsonify({"status": "error", "message": "Error analyzing address"}), 500

    # No/invalid payment → return invoice
    try:
        payment_request = create_invoice()
        return jsonify({
            "status": "payment_required",
            "price_sats": PRICE_SATS,
            "invoice": payment_request
        }), 402

    except Exception as e:
        print("LND error:", e)
        return jsonify({"status": "error", "message": "Error communicating with LND"}), 500

# ────────────────────────────────────────────────
# START SERVER
# ────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Ωmega Pruner L402 service running on http://0.0.0.0:{port}/omega-pruner?address=bc1qexample...")
    app.run(host="0.0.0.0", port=port, debug=True)
