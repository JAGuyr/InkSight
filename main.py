from fastapi import FastAPI, File, UploadFile
import requests
import base64
from io import BytesIO
from fastapi.responses import StreamingResponse

app = FastAPI()

HUGGINGFACE_API_TOKEN = "YOUR_HF_API_KEY"
MODEL_URL = "https://api-inference.huggingface.co/models/Fantasy-Studio/Paint-by-Example"

def image_to_base64(image: UploadFile):
    image_bytes = image.file.read()
    return base64.b64encode(image_bytes).decode("utf-8")

@app.post("/compose-tattoo/")
async def compose_tattoo(body: UploadFile = File(...), tattoo: UploadFile = File(...)):
    body_b64 = image_to_base64(body)
    tattoo_b64 = image_to_base64(tattoo)

    payload = {
        "image": body_b64,
        "example_image": tattoo_b64
    }

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(MODEL_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return {"error": response.text}

    # Return the raw image
    result_image_bytes = response.content
    return StreamingResponse(BytesIO(result_image_bytes), media_type="image/png")
