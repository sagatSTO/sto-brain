from flask import Flask, request, jsonify
import time
import uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
MODE_DECISION = "C"          # A / B / C
CAPITAL_INITIAL = 1000
POSITION_RATIO = 0.10        # 10 % du capital
SEUIL_JOURNALIER = 3         # max décisions / jour
SIGNAL_CONFIRMATION_REQUIRED = 3

# ======================
# TABLES (STOCKAGE)
# ======================
DECISION_JOURNAL = []   # TABLE 3
SIGNAL_TABLE = []       # TABLE 12
PAPER_TRADES = []       # TABLE 5

# ======================
# ÉTAT GLOBAL STO
# ======================
sto_state = {
    "mode": MODE_DECISION,
    "capital": CAPITAL_INITIAL,
    "position": None,        # None ou dict
    "daily_count": 0,
    "last_reset": time.strftime("%Y-%m-%d"),
    "signal_history": [],
    "start_time": time.time()
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

def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = (p * k) + (ema * (1 - k))
    return round(ema, 2)

def confirm_signal(signal):
    hist = sto_state["signal_history"]
    hist.append(signal)
    if len(hist) > 10:
        hist.pop(0)
    return hist.count(signal) >= SIGNAL_CONFIRMATION_REQUIRED

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO STABLE – MODE PAPER OFFLINE",
        "mode": sto_state["mode"],
        "capital": round(sto_state["capital"], 2),
        "position": sto_state["position"],
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
            "raison": "Pas assez de données"
        })

    last_price = prices[-1]
    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)

    signal = "ATTENTE"
    raison = "Marché neutre"

    if rsi and ema_fast and ema_slow:
        if rsi > 60 and ema_fast > ema_slow:
            signal = "ACHAT"
            raison = "RSI + EMA haussiers"
        elif rsi < 40 and ema_fast < ema_slow:
            signal = "VENTE"
            raison = "RSI + EMA baissiers"

    sto_state["daily_count"] += 1

    confirmed = confirm_signal(signal)

    trade_executed = None

    # ======================
    # PAPER EXECUTION (ÉTAPE 5)
    # ======================
    if confirmed:
        # ACHAT
        if signal == "ACHAT" and sto_state["position"] is None:
            invest = sto_state["capital"] * POSITION_RATIO
            qty = invest / last_price
            sto_state["capital"] -= invest
            sto_state["position"] = {
                "entry_price": last_price,
                "qty": qty,
                "invest": invest,
                "timestamp": int(time.time())
            }
            trade_executed = "ACHAT_PAPER"

        # VENTE
        elif signal == "VENTE" and sto_state["position"] is not None:
            pos = sto_state["position"]
            value = pos["qty"] * last_price
            pnl = value - pos["invest"]
            sto_state["capital"] += value
            sto_state["position"] = None
            trade_executed = "VENTE_PAPER"

            PAPER_TRADES.append({
                "id": str(uuid.uuid4()),
                "type": "VENTE",
                "entry_price": pos["entry_price"],
                "exit_price": last_price,
                "pnl": round(pnl, 2),
                "timestamp": int(time.time())
            })

    record = {
        "id": str(uuid.uuid4()),
        "mode": sto_state["mode"],
        "signal": signal,
        "confirmed": confirmed,
        "trade": trade_executed,
        "reason": raison,
        "timestamp": int(time.time())
    }

    DECISION_JOURNAL.append(record)
    SIGNAL_TABLE.append({
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "signal": signal,
        "timestamp": record["timestamp"]
    })

    return jsonify({
        "signal": signal,
        "confirmé": confirmed,
        "trade": trade_executed,
        "prix": last_price,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "capital": round(sto_state["capital"], 2),
        "position": sto_state["position"],
        "decisions_jour": sto_state["daily_count"]
    })

@app.route("/journal")
def journal():
    return jsonify(DECISION_JOURNAL[-20:])

@app.route("/signals")
def signals():
    return jsonify(SIGNAL_TABLE[-20:])

@app.route("/paper_trades")
def paper_trades():
    return jsonify(PAPER_TRADES[-20:])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
