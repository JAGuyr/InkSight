from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests, base64, os, uuid
from io import BytesIO
from supabase import create_client, Client

# Initialize FastAPI
app = FastAPI(title="InkSight – AI Tattoo Placement")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your FlutterFlow domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hugging Face API Info
HUGGINGFACE_API_TOKEN = os.getenv("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")
MODEL_URL = "https://api-inference.huggingface.co/models/Fantasy-Studio/Paint-by-Example"

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def to_base64(file: UploadFile):
    return base64.b64encode(file.file.read()).decode()

@app.post("/compose/")
async def apply_tattoo(body: UploadFile = File(...), tattoo: UploadFile = File(...)):
    # Convert to base64
    body_b64 = to_base64(body)
    tattoo_b64 = to_base64(tattoo)

    # Hugging Face API call
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
        return JSONResponse(content={"error": response.text}, status_code=500)

    # Upload to Supabase
    image_bytes = response.content
    image_id = str(uuid.uuid4()) + ".png"
    path = f"results/{image_id}"

    upload = supabase.storage.from_(SUPABASE_BUCKET).upload(path, image_bytes, {"content-type": "image/png"})

    if upload.get("error"):
        return JSONResponse(content={"error": upload["error"]["message"]}, status_code=500)

    # Get public URL
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)

    return {"url": public_url}
