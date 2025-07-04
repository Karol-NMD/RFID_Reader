from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from RFIDReader2 import TAG_QUEUE, view_database_contents  # import from your existing script
from queue import Empty
import threading

app = FastAPI()

# Allow frontend like Next.js to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"] for Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
