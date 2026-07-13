from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="Context Packer - Local Companion Server")

# Extension origin is a fixed chrome-extension:// id once loaded unpacked;
# update this once the extension has a stable id (Spike 2 uses a wildcard
# regex during dev since MV3 unpacked ids can change between reloads).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
