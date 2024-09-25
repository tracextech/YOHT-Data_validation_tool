#this program will run both streamlit and fastapi at the same time using threading
import subprocess
import streamlit as st
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from threading import Thread

# FastAPI setup
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check route
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Thread to run FastAPI
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=3000)

# Streamlit application ( validate.py)
def run_streamlit():
    subprocess.run(["streamlit", "run", "validate.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"])

# Run both FastAPI and Streamlit in parallel
if __name__ == "__main__":
    t1 = Thread(target=run_fastapi)
    t2 = Thread(target=run_streamlit)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
