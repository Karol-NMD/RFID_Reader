from fastapi import FastAPI, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from RFIDReader2 import (
    TAG_QUEUE,
    view_database_contents,
    start_inventory_with_ip,
    stop_inventory,
    connect_reader,
    disconnect_reader,
    get_reader_antennas,
)
from queue import Empty
import threading
import sqlite3
import asyncio
import socket
import os

app = FastAPI()

inventory_thread = None
stop_event = threading.Event()

# Allow frontend like Next.js to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"] for Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/ping")
async def ping_reader(request: Request):
    data = await request.json()
    ip = data.get("ip")
    if not ip:
        return {"status": "error", "message": "No IP provided"}

    try:
        socket.setdefaulttimeout(1)
        s = socket.socket()
        s.connect((ip, 5084))
        s.close()
        return {"status": "success", "message": f"Reader at {ip} is reachable"}
    except Exception:
        return {"status": "error", "message": f"Reader at {ip} is not reachable"}

@app.post("/api/connect")
async def connect_reader_endpoint(request: Request):
    data = await request.json()
    ip = data.get("ip")
    try:
        connect_reader(ip)
        return {"message": f"🔌 Connected to reader at {ip}"}
    except Exception as e:
        return {"error": f"❌ Connection failed: {str(e)}"}

@app.post("/api/disconnect")
async def disconnect_reader_endpoint():
    try:
        disconnect_reader()
        return {"message": "🔌 Reader disconnected successfully"}
    except Exception as e:
        return {"error": f"❌ Failed to disconnect: {str(e)}"}

@app.post("/api/start-inventory")
async def start_inventory(request: Request):
    global inventory_thread
    data = await request.json()
    ip = data.get("ip")

    if inventory_thread and inventory_thread.is_alive():
        return {"message": "Inventory already running."}

    try:
        inventory_thread = threading.Thread(target=start_inventory_with_ip, args=(ip,), daemon=True)
        inventory_thread.start()
        return {"status" : f"Started inventory on reader {ip}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/stop-inventory")
async def stop_inventory_endpoint():
    global inventory_thread
    try:
        stop_inventory()
        if inventory_thread and inventory_thread.is_alive():
            inventory_thread.join(timeout=5)
            inventory_thread = None
        return {"message": "🛑 Inventory stopped."}
    except Exception as e:
        return {"error": f"⚠️ Failed to stop inventory: {str(e)}"}

@app.post("/api/set-tx-power")
async def set_tx_power(request: Request):
    data = await request.json()
    power_map = data.get("power_map")

    if not isinstance(power_map, dict):
        return {"error": "Invalid power map"}

    try:
        from RFIDReader2 import set_tx_power_for_antennas
        set_tx_power_for_antennas(power_map)
        return {"message": "TX power updated."}
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/live-tags")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            tags = []
            try:
                while True:
                    tag = TAG_QUEUE.get_nowait()
                    tags.append(tag)
            except Empty:
                pass
            if tags:
                await websocket.send_json({"tags": tags})
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.get("/api/db-tags")
def get_filtered_tags(
    date: str = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    db: str = Query(None)
):
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()

        query = "SELECT * FROM tag_reads"
        conditions = []

        if date:
            if start_time and end_time:
                conditions.append(f"(last_seen BETWEEN '{date} {start_time}' AND '{date} {end_time}')")
            else:
                conditions.append(f"(DATE(last_seen) = '{date}')")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id ASC"
        c.execute(query)
        rows = c.fetchall()
        conn.close()

        keys = ["id", "epc_hex", "epc_ascii", "antenna", "channel", "seen_count", "last_seen"]
        structured = [dict(zip(keys, row)) for row in rows]
        return {"rows": structured}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/list-dbs")
def list_databases():
    try:
        db_files = [f for f in os.listdir('.') if f.endswith(".db")]
        return {"databases": db_files}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/antennas")
def fetch_antennas():
    try:
        antennas = get_reader_antennas()
        return {"antennas": antennas}
    except Exception as e:
        return {"error": str(e)}