import requests
import time
import json
import os
import pandas as pd
from datetime import datetime

SEARCH_TERMS = [
    "sol", "ai", "dog", "cat", "pepe", "inu",
    "pump", "moon", "gem", "new", "launch",
    "bonk", "wif", "meme"
]
TOP = 10

MIN_LIQ = 8000
MAX_FDV = 50_000_000
MIN_VOLUME = 15000

MEMORY_FILE = "memory.json"
WEIGHTS_FILE = "weights.json"

AI_WEIGHTS = {
    "prepump": 1.0,
    "momentum": 1.0,
    "smart_money": 1.0
}

# ---------------- LOG ----------------
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ---------------- FETCH SOLANA ----------------
def fetch_solana_pairs():
    pairs = []

    for term in SEARCH_TERMS:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={term}"
            r = requests.get(url, timeout=8).json()

            for p in r.get("pairs", []):
                if (p.get("chainId") or "").lower() == "solana":
                    pairs.append(p)
        except:
            continue

    return pairs

# ---------------- DEDUPE ----------------
def dedupe(pairs):
    seen = set()
    result = []

    for p in pairs:
        addr = p.get("pairAddress")
        if not addr or addr in seen:
            continue
        seen.add(addr)
        result.append(p)

    return result

# ---------------- ANTI-SCAM ----------------
def is_not_scam(p):
    try:
        liquidity = float(p.get("liquidity", {}).get("usd") or 0)
        fdv = float(p.get("fdv") or 0)
        volume = float(p.get("volume", {}).get("h24") or 0)

        if liquidity < MIN_LIQ: return False
        if fdv > MAX_FDV: return False
        if volume < MIN_VOLUME: return False
        if volume > liquidity * 50: return False
        return True
    except:
        return False

# ---------------- IA PART ----------------
def pre_pump_signal(pair):
    liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
    volume_24h = float(pair.get("volume", {}).get("h24") or 0)
    change_5m = float(pair.get("priceChange", {}).get("m5") or 0)

    volume_5m = volume_24h / 288 if volume_24h else 0
    score = 0

    if 20000 < liquidity < 200000: score += 2
    if 1 < change_5m < 5: score += 3
    if liquidity and volume_5m > liquidity * 0.05: score += 2
    return score

def smart_money_boost(pair):
    buys = float(pair.get("txns", {}).get("m5", {}).get("buys") or 0)
    sells = float(pair.get("txns", {}).get("m5", {}).get("sells") or 0)

    if buys > 100 and buys > sells * 2: return 3
    if buys > 50: return 2
    return 0

def ai_score(pair):
    momentum = float(pair.get("priceChange", {}).get("m5") or 0)
    return (
        pre_pump_signal(pair) * AI_WEIGHTS["prepump"] +
        momentum * AI_WEIGHTS["momentum"] +
        smart_money_boost(pair) * AI_WEIGHTS["smart_money"]
    )

# ---------------- MEMORY ----------------
def save_memory(data):
    mem = []
    if os.path.exists(MEMORY_FILE):
        mem = json.load(open(MEMORY_FILE))
    mem.append(data)
    json.dump(mem[-200:], open(MEMORY_FILE, "w"))

def register_signal(pair, score):
    save_memory({
        "token": pair.get("baseToken", {}).get("symbol"),
        "price": float(pair.get("priceUsd") or 0),
        "time": time.time(),
        "score": score
    })

def get_current_price(symbol):
    try:
        r = requests.get(
            f"https://api.dexscreener.com/latest/dex/search?q={symbol}",
            timeout=10
        ).json()
        pairs = r.get("pairs", [])
        return float(pairs[0]["priceUsd"]) if pairs else None
    except:
        return None

def auto_learn():
    global AI_WEIGHTS
    if not os.path.exists(MEMORY_FILE): return

    mem = json.load(open(MEMORY_FILE))
    now = time.time()
    updated = False

    for entry in mem:
        if now - entry["time"] < 3600:
            continue

        new_price = get_current_price(entry["token"])
        if not new_price:
            continue

        change = (new_price - entry["price"]) / entry["price"] * 100

        if change >= 10:
            AI_WEIGHTS["prepump"] *= 1.03
            AI_WEIGHTS["smart_money"] *= 1.04
            AI_WEIGHTS["momentum"] *= 1.02
        else:
            AI_WEIGHTS["momentum"] *= 0.97

        updated = True

    if updated:
        json.dump(AI_WEIGHTS, open(WEIGHTS_FILE, "w"))
        print("🧠 IA evoluiu!")

# ---------------- RANK ----------------
def rank_with_ai(pairs):
    scored = []

    for p in pairs:
        if not is_not_scam(p):
            continue

        score = ai_score(p)
        scored.append((score, p))

    scored.sort(reverse=True, key=lambda x: x[0])

    # fallback se poucos resultados
    if len(scored) < 10:
        return scored

    return scored[:TOP]

# ---------------- PRINT ----------------
def print_top(results):
    print("\n🚀 TOP SOLANA PRE-PUMPS")
    print("=" * 50)
    for i, (s, p) in enumerate(results, 1):
        base = p.get("baseToken", {})
        print(f"\n#{i} {base.get('name')} ({base.get('symbol')})")
        print(f"Score IA: {s:.2f}")
        print(f"Preço: ${float(p.get('priceUsd') or 0):.8f}")
        print(f"5m: {float(p.get('priceChange', {}).get('m5') or 0):.2f}%")

def save_dashboard(results):
    rows = []

    for score, p in results:
        base = p.get("baseToken", {})
        rows.append({
            "Token": base.get("symbol"),
            "Nome": base.get("name"),
            "Score IA": round(score, 2),
            "Preço": float(p.get("priceUsd") or 0),
            "Pump 5m %": float(p.get("priceChange", {}).get("m5") or 0),
            "Liquidez $": float(p.get("liquidity", {}).get("usd") or 0),
        })

    df = pd.DataFrame(rows)
    df.to_csv("dashboard.csv", index=False)
# ---------------- LOOP ----------------
def run():
    log("Scanner Solana IA iniciado")

    while True:
        pairs = fetch_solana_pairs()
        pairs = dedupe(pairs)

        ranked = rank_with_ai(pairs)

        print_top(ranked)
        save_dashboard(ranked)

        for score, pair in ranked:
            register_signal(pair, score)

        auto_learn()

        time.sleep(30)

if __name__ == "__main__":
    run()
