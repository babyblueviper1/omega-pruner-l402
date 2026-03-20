# Ωmega Pruner – L402 Micro-Paid Bitcoin Endpoint

A Bitcoin-native API that lets users (or agents) **verify and prune Bitcoin addresses** using Lightning micro-payments.

Instead of a subscription or API key, this endpoint uses **L402**:  
you pay a few sats → the request unlocks instantly.

---

## What this does

**Ωmega Pruner** analyzes a Bitcoin address and returns:

- Address cleanliness  
- Dust / spam UTXO detection  
- Risk signals (low / medium / high)  
- Prune recommendations  
- Useful metadata for agents or automation tools  

Designed for:

- Bitcoin power users  
- Lightning / agent developers  
- Wallet hygiene tools  
- Automated treasury systems  
- AI agents that manage Bitcoin  

---

## Why this exists

Most APIs rely on API keys and subscriptions.

This one uses **native Bitcoin payments** instead.

**Advantages:**

- No accounts  
- No API keys  
- No subscriptions  
- Pay only when you actually use it  

Just send a request → pay 10–30 sats → receive the result.

---

## How it works (simple version)

1. You call the endpoint  
2. If unpaid → you receive a Lightning invoice  
3. You pay the invoice  
4. Call the endpoint again → now it returns the result  

This is called an **L402 paywall** (built on Lightning).

---

## Example request

```bash
curl "http://127.0.0.1:8081/omega-pruner?address=bc1qexample..."
```

**Example response (unpaid)**

```json
{
  "status": "payment_required",
  "price_sats": 30,
  "invoice": "lnbc1..."
}
```

**Example response (after payment)**

```json
{
  "status": "success",
  "address": "bc1qexample...",
  "risk_level": "low",
  "dust_detected": false,
  "prune_recommendation": "no pruning needed",
  "score": 92
}
```

---

## Run locally

1. Clone the repo

   ```bash
   git clone https://github.com/YOUR-USERNAME/omega-pruner-l402.git
   cd omega-pruner-l402
   ```

2. Create a virtual environment

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Make sure **LND** is running

   You need a local Lightning node running with gRPC enabled.

   ```bash
   # Start LND
   lnd

   # Unlock the wallet
   lncli unlock
   ```

5. Start the server

   ```bash
   python l402_omega_pruner.py
   ```

   You should see:

   ```
   Ωmega Pruner L402 service running
   http://127.0.0.1:8081/omega-pruner?address=bc1qexample...
   ```

### Test it in the browser

Open:

```
http://127.0.0.1:8081/omega-pruner?address=bc1qexample...
```

You should see a Lightning invoice.  
Pay it → refresh → the result appears.

---

## Why this matters

This is not just an API.  
It’s an example of **machines paying machines** using Bitcoin.

Instead of:

- API keys  
- subscriptions  
- centralized billing  

We get:

- instant payments  
- permissionless access  
- micro-priced endpoints  
- native Bitcoin infrastructure  

---

## Future plans

Planned features:

- Multi-address batch pruning  
- UTXO optimization scoring  
- Agent-friendly JSON output  
- Policy-based pruning (DVrl integration)  
- Public hosted endpoint  

---

## Who this is for

This project is useful if you are:

- building a Bitcoin agent  
- building a Lightning tool  
- building a wallet hygiene tool  
- experimenting with L402  
- interested in machine-to-machine payments  

---

## License

**MIT**

## Author

Built as part of the **Viper Bitcoin Agent Tools** ecosystem.
```
