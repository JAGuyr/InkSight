from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import requests
import base64
import os
import uuid
from io import BytesIO
from supabase import create_client, Client

# === CONFIG ===
HUGGINGFACE_API_TOKEN = os.getenv("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")
HUGGINGFACE_MODEL_URL = "https://api-inference.huggingface.co/models/Fantasy-Studio/Paint-by-Example"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "tattoos")

# === INIT ===
app = FastAPI(title="InkSight – Tattoo Placement API")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Replace with FlutterFlow domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CORS-Friendly Error Handlers ===
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers={"Access-Control-Allow-Origin": "*"},
    )

# === Health Check ===
@app.get("/")
def health():
    return {"message": "InkSight API is live"}

# === Image Encoding ===
def to_base64(file: UploadFile) -> str:
    return base64.b64encode(file.file.read()).decode()

# === Main Endpoint ===
@app.post("/compose/")
async def compose_tattoo(body: UploadFile = File(...), tattoo: UploadFile = File(...)):
    try:
        # Encode images to base64
        body_b64 = to_base64(body)
        tattoo_b64 = to_base64(tattoo)

        # Call Hugging Face model
        payload = {
            "image": body_b64,
            "example_image": tattoo_b64,
        }
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(HUGGINGFACE_MODEL_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return JSONResponse(
                content={"error": "HuggingFace API failed", "details": response.text},
                status_code=500
            )

        # Upload result to Supabase
        result_image = response.content
        file_name = f"results/{uuid.uuid4().hex}.png"
        upload_response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            file_name,
            result_image,
            {"content-type": "image/png"}
        )

        if upload_response.get("error"):
            return JSONResponse(content={"error": "Supabase upload failed"}, status_code=500)

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)

        return {"url": public_url}

    except Exception as e:
        return JSONResponse(content={"error": "Unexpected error", "details": str(e)}, status_code=500)
