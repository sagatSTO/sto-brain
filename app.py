from flask import Flask, request, jsonify
import time
import math
from statistics import mean

app = Flask(__name__)

# =====================================================
# CONFIGURATION GLOBALE
# =====================================================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# Capital simulé (offline)
CAPITAL_INITIAL = 10000.0
RISK_PER_TRADE = 0.01  # 1%

# =====================================================
# ÉTAT GLOBAL STO
# =====================================================
sto_state = {
    "mode_decision": "C",  # A = conservateur, B = semi-actif, C = agressif
    "market_status": "OFFLINE",
    "last_action": "ATTENTE",
    "reason": "STO initialisé",
    "start_time": time.time(),
    "capital": CAPITAL_INITIAL
}

# Journal des décisions
decision_log = []

# Cache marché simulé
market_cache = {
    "prices": [],
    "last_update": None
}

# =====================================================
# OUTILS INDICATEURS
# =====================================================
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
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# =====================================================
# GESTION DU RISQUE
# =====================================================
def position_size(capital, entry_price):
    risk_amount = capital * RISK_PER_TRADE
    stop_loss_distance = entry_price * 0.01  # 1%
    size = risk_amount / stop_loss_distance
    return round(size, 4)

# =====================================================
# LOG DECISION
# =====================================================
def log_decision(data):
    decision_log.append({
        "timestamp": time.time(),
        **data
    })

# =====================================================
# ROUTES API
# =====================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode_decision": sto_state["mode_decision"],
        "capital": sto_state["capital"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# -----------------------------------------------------
# SIMULATION PRIX (ALIMENTATION CACHE)
# -----------------------------------------------------
@app.route("/simulate/feed", methods=["POST"])
def feed_prices():
    data = request.json or {}
    prices = data.get("prices", [])
    if not prices or not isinstance(prices, list):
        return jsonify({"error": "Liste de prix invalide"}), 400

    market_cache["prices"] = prices
    market_cache["last_update"] = time.time()

    return jsonify({
        "status": "OK",
        "message": "Prix simulés injectés",
        "nb_prices": len(prices)
    })

# -----------------------------------------------------
# ANALYSE OFFLINE (RSI / EMA / TENDANCE)
# -----------------------------------------------------
@app.route("/market/status", methods=["GET"])
def market_status():
    prices = market_cache["prices"]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        }), 400

    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)
    last_price = prices[-1]

    # Décision selon mode
    mode = sto_state["mode_decision"]
    action = "ATTENTE"
    raison = "Marché neutre"
    tendance = "STABLE"

    if rsi and ema_fast and ema_slow:
        if rsi > 60 and ema_fast > ema_slow:
            tendance = "HAUSSE"
            action = "ENTRER" if mode in ["B", "C"] else "ATTENTE"
            raison = "Signal haussier confirmé"
        elif rsi < 40 and ema_fast < ema_slow:
            tendance = "BAISSE"
            action = "SORTIR" if mode == "C" else "ATTENTE"
            raison = "Signal baissier confirmé"

    # Gestion du risque
    size = position_size(sto_state["capital"], last_price) if action == "ENTRER" else 0

    log_decision({
        "prix": last_price,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "action": action,
        "tendance": tendance,
        "mode": mode
    })

    sto_state["last_action"] = action
    sto_state["reason"] = raison

    return jsonify({
        "statut_marche": "OK",
        "mode_decision": mode,
        "prix_actuel": last_price,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "tendance": tendance,
        "action_STO": action,
        "position_size": size,
        "raison": raison
    })

# -----------------------------------------------------
# JOURNAL DES DÉCISIONS
# -----------------------------------------------------
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify({
        "nb_decisions": len(decision_log),
        "decisions": decision_log[-50:]  # dernières 50
    })

# -----------------------------------------------------
# BACKTEST AUTOMATIQUE
# -----------------------------------------------------
@app.route("/backtest", methods=["GET"])
def backtest():
    prices = market_cache["prices"]
    if len(prices) < 30:
        return jsonify({"error": "Pas assez de données"}), 400

    gains = 0
    trades = 0
    for i in range(20, len(prices)):
        sub_prices = prices[:i]
        rsi = calculate_rsi(sub_prices)
        ema_fast = calculate_ema(sub_prices, 10)
        ema_slow = calculate_ema(sub_prices, 20)
        if rsi and ema_fast and ema_slow and rsi > 60 and ema_fast > ema_slow:
            trades += 1
            gains += sub_prices[-1] * 0.002  # gain simulé

    return jsonify({
        "trades_simules": trades,
        "gain_simule": round(gains, 2)
    })

# -----------------------------------------------------
# AUTH
# -----------------------------------------------------
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    if data.get("email") == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
