from pathlib import Path


from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse


from conf.system import SYS_CONFIG
from src.logger import logger

router = APIRouter()

@router.get("/get-image/{filename}")
async def get_image(filename: str):
    """Retrieve an image by its filename."""
    image_path = Path(SYS_CONFIG.base_dir) / "server" / "assets" / filename
    logger.info(f"Fetching image from path: {image_path}")
    if not image_path.exists():
        return JSONResponse(status_code=404, content={"error": "Image not found."})
    return StreamingResponse(image_path.open("rb"), media_type="image/jpeg")