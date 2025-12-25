from flask import Flask, request, jsonify
import time
import requests
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
CACHE_TTL = 60  # secondes

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "market_status": "OFFLINE",
    "last_action": "ATTENTE",
    "reason": "STO initialisé",
    "start_time": time.time()
}

# ======================
# CACHE MARCHÉ
# ======================
market_cache = {
    "price": None,
    "timestamp": 0,
    "source": None
}

# ======================
# PAGE RACINE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# FONCTION CACHE PRIX
# ======================
def get_cached_price():
    now = time.time()

    # 1️⃣ Cache valide
    if market_cache["price"] and (now - market_cache["timestamp"] < CACHE_TTL):
        return market_cache["price"], market_cache["source"], "CACHE"

    # 2️⃣ Tentative CoinGecko
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        )
        data = r.json()
        price = data["bitcoin"]["usd"]

        market_cache["price"] = price
        market_cache["timestamp"] = now
        market_cache["source"] = "COINGECKO"

        return price, "COINGECKO", "LIVE"

    except:
        # 3️⃣ Fallback ultime
        if market_cache["price"]:
            return market_cache["price"], market_cache["source"], "STALE"

        return None, None, "ERROR"

# ======================
# MARCHÉ STATUS
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    price, source, mode = get_cached_price()

    if price is None:
        sto_state["market_status"] = "ERREUR"
        sto_state["reason"] = "Aucune donnée marché disponible"
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": sto_state["reason"]
        }), 500

    sto_state["market_status"] = "OK"
    sto_state["last_action"] = "OBSERVATION"
    sto_state["reason"] = "Prix disponible"

    return jsonify({
        "statut_marche": "OK",
        "prix_actuel": round(price, 2),
        "source": source,
        "mode_cache": mode,
        "action_STO": "OBSERVATION",
        "raison": sto_state["reason"]
    })

# ======================
# SIMULATION RSI / EMA
# ======================
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées (min 20)"
        }), 400

    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)

    signal = "NEUTRE"
    if rsi and rsi > 60 and ema_fast > ema_slow:
        signal = "HAUSSE"
    elif rsi and rsi < 40 and ema_fast < ema_slow:
        signal = "BAISSE"

    return jsonify({
        "RSI": rsi,
        "EMA_10": ema_fast,
        "EMA_20": ema_slow,
        "signal": signal,
        "statut": "SIMULATION OK"
    })

# ======================
# JOURNAL (VISUEL 1)
# ======================
decision_log = []

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(decision_log[-50:])

# ======================
# AUTH
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    if data.get("email") == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
