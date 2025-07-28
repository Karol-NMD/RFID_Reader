from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from RFIDReader2 import TAG_QUEUE, view_database_contents, start_inventory_with_ip, stop_inventory  # import from your existing script
from queue import Empty
import threading

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

@app.post("/api/start-inventory")
async def start_inventory(request: Request):
    global inventory_thread, stop_event
    data = await request.json()
    ip = data.get("ip")
    if not ip:
        return {"error": "No IP provided"}

    if inventory_thread and inventory_thread.is_alive():
        return {"message": "Inventory already running."}

    try:
        stop_event.clear()
        inventory_thread = threading.Thread(target=start_inventory_with_ip, args=(ip,), daemon=True)
        inventory_thread.start()
        return {"status" : f"Started inventory on reader {ip}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/stop-inventory")
async def stop_inventory():
    global inventory_thread
    try:
        stop_inventory()
        stop_event.set()
        if inventory_thread and inventory_thread.is_alive():
            stop_event.set()
            inventory_thread.join(timeout=5)
            inventory_thread = None
        return {"message": "🛑 Inventory stopped."}
    except Exception as e:
        return {"error": f"⚠️ Failed to stop inventory: {str(e)}"}

@app.get("/api/live-tags")
def get_tags():
    tags = []
    try:
        while True:
            tag = TAG_QUEUE.get_nowait()
            tags.append(tag)
    except Empty:
        pass
    return {"tags": tags}

@app.get("/api/db-tags")
def get_all_tags():
    try:
        # Capture printed output from view_database_contents
        import io
        import sys
        buffer = io.StringIO()
        sys.stdout = buffer
        view_database_contents()
        sys.stdout = sys.__stdout__
        output = buffer.getvalue()
        return {"output": output}
    except Exception as e:
        return {"error": str(e)}
