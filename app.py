from flask import Flask, request, jsonify
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OFFLINE",
    "decision_mode": "C",  # C = Hybride Pro
    "last_action": "ATTENTE",
    "reason": "STO initialisé",
    "start_time": time.time()
}

decision_journal = []
market_cache = {
    "prices": [],
    "last_update": None
}

# ======================
# INDICATEURS
# ======================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
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
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# HOME
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "decision_mode": sto_state["decision_mode"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# SIMULATION OFFLINE
# ======================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    market_cache["prices"] = prices
    market_cache["last_update"] = time.time()

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "STO STABLE – MODE OFFLINE",
            "raison": "Pas assez de données simulées (min 20)",
            "points_reçus": len(prices)
        })

    rsi = calculate_rsi(prices)
    ema_short = calculate_ema(prices, 10)
    ema_long = calculate_ema(prices, 20)

    if rsi > 60 and ema_short > ema_long:
        action = "ACHAT_SIMULE"
        tendance = "HAUSSE"
    elif rsi < 40 and ema_short < ema_long:
        action = "VENTE_SIMULE"
        tendance = "BAISSE"
    else:
        action = "ATTENTE"
        tendance = "STABLE"

    decision = {
        "timestamp": time.time(),
        "RSI": rsi,
        "EMA_10": ema_short,
        "EMA_20": ema_long,
        "tendance": tendance,
        "action": action
    }

    decision_journal.append(decision)
    sto_state["last_action"] = action
    sto_state["reason"] = "Décision offline calculée"
    sto_state["mode"] = "SEMI-ACTIF"

    return jsonify(decision)

# ======================
# VISUEL 1 – DASHBOARD
# ======================
@app.route("/dashboard", methods=["GET"])
def dashboard():
    return jsonify({
        "mode": sto_state["mode"],
        "decision_mode": sto_state["decision_mode"],
        "last_action": sto_state["last_action"],
        "reason": sto_state["reason"],
        "points_cache": len(market_cache["prices"]),
        "journal_size": len(decision_journal)
    })

# ======================
# VISUEL 2 – JOURNAL
# ======================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(decision_journal[-20:])

# ======================
# AUTH
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    return jsonify({
        "acces": "admin" if data.get("email") == ADMIN_EMAIL else "utilisateur"
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
