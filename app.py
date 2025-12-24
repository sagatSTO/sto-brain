from flask import Flask, request, jsonify
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# CONFIG STO
# ======================
CAPITAL_SIMULE = 1000.0
RISK_PERCENT = 0.02  # 2% par trade
MODE_DECISION = "C"  # A = observation, B = conservateur, C = hybride pro

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OFFLINE",
    "mode_decision": MODE_DECISION,
    "market_status": "OFFLINE",
    "last_action": "ATTENTE",
    "reason": "STO STABLE – MODE OFFLINE",
    "capital": CAPITAL_SIMULE,
    "start_time": time.time(),
    "journal": []
}

# ======================
# OUTILS INDICATEURS
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
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# LOGIQUE DÉCISIONNELLE
# ======================
def decide(prices):
    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)

    action = "ATTENTE"
    raison = "Marché neutre"

    if rsi is None or ema_fast is None or ema_slow is None:
        return action, "Données insuffisantes", rsi, ema_fast, ema_slow

    if sto_state["mode_decision"] == "A":
        return "OBSERVATION", "Mode A – observation seule", rsi, ema_fast, ema_slow

    if rsi > 60 and ema_fast > ema_slow:
        action = "ACHAT"
        raison = "RSI élevé + EMA haussière"
    elif rsi < 40 and ema_fast < ema_slow:
        action = "VENTE"
        raison = "RSI faible + EMA baissière"

    return action, raison, rsi, ema_fast, ema_slow

# ======================
# GESTION DU RISQUE
# ======================
def position_size(capital, price):
    risk_amount = capital * RISK_PERCENT
    if price <= 0:
        return 0
    size = risk_amount / price
    return round(size, 6)

# ======================
# ROUTES API
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"],
        "capital_simule": sto_state["capital"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate", methods=["GET"])
def simulate():
    """
    Exemple :
    /simulate?prices=87000,87100,87250,87300,87200,87400
    """
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({"erreur": "au moins 20 prix requis"}), 400

    last_price = prices[-1]
    action, raison, rsi, ema_fast, ema_slow = decide(prices)
    size = position_size(sto_state["capital"], last_price)

    entry = {
        "timestamp": int(time.time()),
        "prix": last_price,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "action": action,
        "raison": raison,
        "position_size": size
    }

    sto_state["last_action"] = action
    sto_state["reason"] = raison
    sto_state["journal"].append(entry)

    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode_decision": sto_state["mode_decision"],
        "action_STO": action,
        "prix_actuel": last_price,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "position_size": size,
        "raison": raison
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(sto_state["journal"][-20:])

# ======================
# AUTH
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
