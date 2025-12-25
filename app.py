from flask import Flask, jsonify, request
import time
import random

app = Flask(__name__)

# ======================
# CONFIG
# ======================
START_TIME = time.time()
MODE_DECISION = "C"  # A / B / C
CAPITAL_SIMULE = 1000

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OFFLINE",
    "decision": "ATTENTE",
    "raison": "STO stable – mode offline",
    "capital": CAPITAL_SIMULE,
    "last_update": time.time()
}

decision_log = []

# ======================
# VISUEL 1 — DASHBOARD STO
# ======================
@app.route("/")
def dashboard():
    uptime = int(time.time() - START_TIME)
    return f"""
    <html>
    <head>
        <title>STO Dashboard</title>
        <style>
            body {{ font-family: Arial; background:#0f172a; color:#e5e7eb; padding:30px; }}
            .box {{ background:#020617; padding:20px; border-radius:12px; width:400px; }}
            h1 {{ color:#22c55e; }}
            .label {{ color:#94a3b8; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>STO — EN LIGNE</h1>
            <p><span class="label">Mode :</span> {sto_state["mode"]}</p>
            <p><span class="label">Décision :</span> {sto_state["decision"]}</p>
            <p><span class="label">Raison :</span> {sto_state["raison"]}</p>
            <p><span class="label">Capital simulé :</span> {sto_state["capital"]} $</p>
            <p><span class="label">Uptime :</span> {uptime} sec</p>
            <hr>
            <p>📊 <a href="/simulate">Simulation</a></p>
            <p>📜 <a href="/journal">Journal décisions</a></p>
        </div>
    </body>
    </html>
    """

# ======================
# VISUEL 2 — SIMULATION OFFLINE
# ======================
@app.route("/simulate")
def simulate():
    prix = random.randint(85000, 90000)
    variation = random.choice([-1, 1]) * random.uniform(0.2, 1.5)

    if variation > 0.7:
        decision = "ACHAT"
        raison = "Signal haussier simulé"
    elif variation < -0.7:
        decision = "VENTE"
        raison = "Signal baissier simulé"
    else:
        decision = "ATTENTE"
        raison = "Marché simulé neutre"

    sto_state["decision"] = decision
    sto_state["raison"] = raison
    sto_state["last_update"] = time.time()

    decision_log.append({
        "prix": prix,
        "decision": decision,
        "raison": raison,
        "timestamp": int(time.time())
    })

    return f"""
    <html>
    <head>
        <title>STO Simulation</title>
        <style>
            body {{ font-family: Arial; background:#020617; color:#e5e7eb; padding:30px; }}
            .box {{ background:#020617; padding:20px; border-radius:12px; width:450px; }}
            h1 {{ color:#38bdf8; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>Simulation STO</h1>
            <p>Prix simulé BTC : {prix} $</p>
            <p>Décision : <b>{decision}</b></p>
            <p>Raison : {raison}</p>
            <br>
            <a href="/simulate">🔁 Relancer simulation</a><br>
            <a href="/">⬅ Retour dashboard</a>
        </div>
    </body>
    </html>
    """

# ======================
# VISUEL 3 — JOURNAL
# ======================
@app.route("/journal")
def journal():
    rows = ""
    for d in decision_log[-10:][::-1]:
        rows += f"<tr><td>{d['timestamp']}</td><td>{d['prix']}</td><td>{d['decision']}</td><td>{d['raison']}</td></tr>"

    return f"""
    <html>
    <head>
        <title>Journal STO</title>
        <style>
            body {{ font-family: Arial; background:#020617; color:#e5e7eb; padding:30px; }}
            table {{ border-collapse: collapse; width:600px; }}
            td, th {{ border:1px solid #334155; padding:8px; }}
            th {{ background:#020617; }}
        </style>
    </head>
    <body>
        <h1>Journal des décisions</h1>
        <table>
            <tr><th>Time</th><th>Prix</th><th>Décision</th><th>Raison</th></tr>
            {rows}
        </table>
        <br>
        <a href="/">⬅ Retour dashboard</a>
    </body>
    </html>
    """

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
