from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def ping():
    return {"ok": True, "service": "ping"}
