# app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    print("Endpoint '/' was called")  # Debug log for endpoint access
    return {"message": "Hello, World!"}
