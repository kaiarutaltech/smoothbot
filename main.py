from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import math

app = FastAPI(title="KaisaSmoothBot", version="v1.0")

# ---- Parameetrid ----
BETA = 0.3
BACKLOG_SPREAD = 4
MAX_CHANGE = 0.4

# ---- Andmete eraldamine ----
def extract_role_history(weeks, role):
    history = {
        "demand": [],
        "arrivals": [],
        "orders": [],
        "inventory": [],
        "backlog": []
    }
    for w in weeks:
        r = w["roles"][role]
        history["demand"].append(r["incoming_orders"])
        history["arrivals"].append(r["arriving_shipments"])
        history["inventory"].append(r["inventory"])
        history["backlog"].append(r["backlog"])
        history["orders"].append(w.get("orders", {}).get(role, 0))
    return history

# ---- Eksponentsiaalne silumine ----
def smooth_forecast(series, beta):
    estimate = float(series[0]) if series else 0.0
    for x in series[1:]:
        estimate = beta * x + (1 - beta) * estimate
    return estimate

# ---- Rollipõhine otsus ----
def decide_order(weeks, role):
    h = extract_role_history(weeks, role)

    supply_line = sum(h["orders"]) - sum(h["arrivals"])
    demand_est = smooth_forecast(h["demand"], BETA)

    backlog_now = h["backlog"][-1]
    backlog_component = backlog_now / max(1, BACKLOG_SPREAD)

    target = demand_est + backlog_component
    raw_order = target - supply_line

    last_order = h["orders"][-1]
    max_step = MAX_CHANGE * max(1, demand_est)

    adjusted = min(
        last_order + max_step,
        max(last_order - max_step, raw_order)
    )

    return max(0, int(round(adjusted)))

# ---- Iganädalane samm ----
def process_week(body):
    weeks = body["weeks"]
    return {
        "orders": {
            role: decide_order(weeks, role)
            for role in ["retailer", "wholesaler", "distributor", "factory"]
        }
    }

# ---- API endpoint ----
@app.post("/api/decision")
async def decision(req: Request):
    body = await req.json()

    if body.get("handshake"):
        return JSONResponse({
            "ok": True,
            "student_email": "kaiaru@taltech.ee",
            "algorithm_name": "KaisaSmoothBot",
            "version": "v1.0.0",
            "supports": {"blackbox": True, "glassbox": False},
            "message": "BeerBot ready"
        })

    return JSONResponse(process_week(body))
