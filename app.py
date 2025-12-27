from flask import Flask, request, jsonify
import time
import uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG GLOBALE
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

MODE_DECISION = "C"            # A / B / C
MODE_EXECUTION = "PAPER"       # OFFLINE / PAPER
CAPITAL_INITIAL = 1000.0
RISQUE_PAR_TRADE = 0.02        # 2%
SEUIL_JOURNALIER = 3           # max décisions / jour

# ======================
# TABLES (STOCKAGE)
# ======================
DECISION_JOURNAL = []   # TABLE 3
SIGNAL_TABLE = []       # TABLE 12
PAPER_TRADES = []       # TABLE 20 (nouvelle)

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "mode": MODE_DECISION,
    "execution": MODE_EXECUTION,
    "capital": CAPITAL_INITIAL,
    "daily_count": 0,
    "last_reset": time.strftime("%Y-%m-%d"),
    "start_time": time.time(),
    "signal_history": []
}

# ======================
# UTILS
# ======================
def reset_daily_counter():
    today = time.strftime("%Y-%m-%d")
    if sto_state["last_reset"] != today:
        sto_state["daily_count"] = 0
        sto_state["last_reset"] = today

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

def calculate_ema(prices, period=10):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = (p * k) + (ema * (1 - k))
    return round(ema, 2)

def position_size(capital, prix_entree):
    risque_montant = capital * RISQUE_PAR_TRADE
    if prix_entree <= 0:
        return 0
    return round(risque_montant / prix_entree, 6)

# ======================
# ROUTES
# ======================

@app.route("/")
def home():
    return jsonify({
        "statut": "STO STABLE",
        "mode_decision": sto_state["mode"],
        "mode_execution": sto_state["execution"],
        "capital": round(sto_state["capital"], 2),
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate", methods=["GET"])
def simulate():
    reset_daily_counter()

    if sto_state["daily_count"] >= SEUIL_JOURNALIER:
        return jsonify({
            "signal": "BLOQUÉ",
            "raison": "Seuil journalier atteint"
        })

    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        })

    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)

    signal = "ATTENTE"
    raison = "Marché neutre"
    prix_actuel = prices[-1]

    if rsi and ema_fast and ema_slow:
        if rsi > 60 and ema_fast > ema_slow:
            signal = "ACHAT"
            raison = "RSI + EMA haussiers"
        elif rsi < 40 and ema_fast < ema_slow:
            signal = "VENTE"
            raison = "RSI + EMA baissiers"

    sto_state["daily_count"] += 1

    decision = {
        "id": str(uuid.uuid4()),
        "signal": signal,
        "raison": raison,
        "timestamp": int(time.time())
    }
    DECISION_JOURNAL.append(decision)

    SIGNAL_TABLE.append({
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "signal": signal,
        "timestamp": decision["timestamp"]
    })

    # ======================
    # MODE PAPER (PRIORITÉ 2)
    # ======================
    trade = None
    if sto_state["execution"] == "PAPER" and signal in ["ACHAT", "VENTE"]:
        qty = position_size(sto_state["capital"], prix_actuel)
        if qty > 0:
            trade = {
                "id": decision["id"],
                "type": signal,
                "prix": prix_actuel,
                "quantite": qty,
                "valeur": round(qty * prix_actuel, 2),
                "timestamp": decision["timestamp"]
            }
            PAPER_TRADES.append(trade)

    return jsonify({
        "signal": signal,
        "raison": raison,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "trade_paper": trade,
        "capital": round(sto_state["capital"], 2),
        "decisions_jour": sto_state["daily_count"]
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(DECISION_JOURNAL[-20:])

@app.route("/signals", methods=["GET"])
def signals():
    return jsonify(SIGNAL_TABLE[-20:])

@app.route("/paper_trades", methods=["GET"])
def paper_trades():
    return jsonify(PAPER_TRADES[-20:])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
