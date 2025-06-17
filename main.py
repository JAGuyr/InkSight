from fastapi import FastAPI, File, UploadFile
import requests
import base64
from io import BytesIO
from fastapi.responses import StreamingResponse

app = FastAPI(title="InkSight – AI Tattoo Placement")

HUGGINGFACE_API_TOKEN = "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"
MODEL_URL = "https://api-inference.huggingface.co/models/Fantasy-Studio/Paint-by-Example"

def to_base64(file: UploadFile):
    return base64.b64encode(file.file.read()).decode()

@app.post("/compose/")
async def apply_tattoo(body: UploadFile = File(...), tattoo: UploadFile = File(...)):
    body_b64 = to_base64(body)
    tattoo_b64 = to_base64(tattoo)

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "image": body_b64,
        "example_image": tattoo_b64
    }

    response = requests.post(MODEL_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return {"error": response.json()}

    return StreamingResponse(BytesIO(response.content), media_type="image/png")
