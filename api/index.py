import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from mangum import Mangum

app = FastAPI()

# CORS Middleware taaki kisi bhi origin se request block na ho
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

ORIGINAL_API = "https://frux-info-api.vercel.app/api/banner"

@app.get("/banner")
async def proxy_banner(uid: str = Query(...)):
    async with httpx.AsyncClient() as client:
        try:
            # Main API ko internal key "frux07" ke saath hit kar raha hai
            resp = await client.get(ORIGINAL_API, params={"uid": uid, "key": "frux07"}, timeout=30)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/png"))
        except Exception as e:
            raise HTTPException(502, f"Proxy error: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Banner Proxy Active", "endpoint": "/banner?uid=UID"}

# Vercel Serverless Function ke liye Mangum handler mandatory hai
handler = Mangum(app)
