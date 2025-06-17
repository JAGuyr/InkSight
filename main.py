from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os, uuid, requests, base64
from supabase import create_client, Client
from fastapi import FastAPI
import os
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello Railway!"}

if __name__ == "__main__":
    # Use PORT environment variable set by Railway or default to 8000 locally
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)



app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
HUGGINGFACE_API_TOKEN = os.getenv("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")
HUGGINGFACE_MODEL_URL = "https://api-inference.huggingface.co/models/Fantasy-Studio/Paint-by-Example"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "tattoos")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@app.get("/")
def health_check():
    return {"message": "InkSight API is live"}

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

def to_base64(file: UploadFile) -> str:
    return base64.b64encode(file.file.read()).decode()

@app.post("/compose/")
async def compose_tattoo(body: UploadFile = File(...), tattoo: UploadFile = File(...)):
    try:
        body_b64 = to_base64(body)
        tattoo_b64 = to_base64(tattoo)

        payload = {"image": body_b64, "example_image": tattoo_b64}
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}", "Content-Type": "application/json"}
        response = requests.post(HUGGINGFACE_MODEL_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return JSONResponse(content={"error": "HuggingFace API failed", "details": response.text}, status_code=500)

        result_image = response.content
        file_name = f"results/{uuid.uuid4().hex}.png"
        upload_response = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, result_image, {"content-type": "image/png"})

        if upload_response.get("error"):
            return JSONResponse(content={"error": "Supabase upload failed"}, status_code=500)

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        return {"url": public_url}
    except Exception as e:
        return JSONResponse(content={"error": "Unexpected error", "details": str(e)}, status_code=500)
