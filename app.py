import io
import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()
    process_pool.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INFO_API_URL = "https://jaat-info-api.onrender.com/player-info"
FONT_FILE = "arial_unicode_bold.otf"
FONT_CHEROKEE = "NotoSansCherokee.ttf"

ICON_CDN_URL = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/{}.png"

client = httpx.AsyncClient(
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=10.0,
    follow_redirects=True
)

process_pool = ThreadPoolExecutor(max_workers=4)

def load_unicode_font(size, font_file=FONT_FILE):
    try:
        font_path = os.path.join(os.path.dirname(__file__), font_file)
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

async def fetch_image_bytes(item_id):
    if not item_id or str(item_id) == "0" or item_id is None:
        return None

    item_id = str(item_id)
    url = ICON_CDN_URL.format(item_id)
    
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.content
    except:
        pass
    return None

def bytes_to_image(img_bytes):
    if img_bytes:
        return Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    return Image.new('RGBA', (100, 100), (0, 0, 0, 0))

def process_banner_image(data, avatar_bytes, banner_bytes, pin_bytes):
    avatar_img = bytes_to_image(avatar_bytes)
    banner_img = bytes_to_image(banner_bytes)
    pin_img = bytes_to_image(pin_bytes)

    # Get data with proper fallbacks
    level = str(data.get("level", "N/A"))
    name = data.get("nickname", "Unknown")
    guild = data.get("clanName", "")  # Empty string if no guild

    TARGET_HEIGHT = 405 
    avatar_img = avatar_img.resize((TARGET_HEIGHT, TARGET_HEIGHT), Image.LANCZOS)
    
    b_w, b_h = banner_img.size
    if b_w > 50 and b_h > 50:
        banner_img = banner_img.rotate(3, resample=Image.BICUBIC, expand=True)
        b_w, b_h = banner_img.size
        
        crop_top, crop_bottom, crop_sides = 0.23, 0.32, 0.17
        left, top = b_w * crop_sides, b_h * crop_top
        right, bottom = b_w * (1 - crop_sides), b_h * (1 - crop_bottom)
        banner_img = banner_img.crop((left, top, right, bottom))

    b_w, b_h = banner_img.size
    if b_h > 0:
        new_banner_w = int(TARGET_HEIGHT * (b_w / b_h) * 2.0)
        banner_img = banner_img.resize((new_banner_w, TARGET_HEIGHT), Image.LANCZOS)
    else:
        banner_img = Image.new("RGBA", (800, 400), (50, 50, 50, 0))

    final_w = TARGET_HEIGHT + new_banner_w
    final_h = TARGET_HEIGHT
    combined = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    combined.paste(avatar_img, (0, 0))
    combined.paste(banner_img, (TARGET_HEIGHT, 0))
    
    draw = ImageDraw.Draw(combined)
    
    font_large = load_unicode_font(125) 
    font_large_cherokee = load_unicode_font(125, FONT_CHEROKEE)
    font_small = load_unicode_font(95) 
    font_small_cherokee = load_unicode_font(95, FONT_CHEROKEE)
    font_level = load_unicode_font(50)

    text_x = TARGET_HEIGHT + 40 
    text_y = 40 
    
    def is_cherokee(char):
        code = ord(char)
        return (0x13A0 <= code <= 0x13FF) or (0xAB70 <= code <= 0xABBF)

    def draw_text_with_stroke(x, y, text, font_main, font_fallback, size=3):
        if not text:
            return
        current_x = x
        for char in text:
            font = font_fallback if is_cherokee(char) else font_main
            
            # Draw stroke (black outline)
            for dx in range(-size, size + 1):
                for dy in range(-size, size + 1):
                    if dx != 0 or dy != 0:
                        draw.text((current_x + dx, y + dy), char, font=font, fill="black")
            
            # Draw main text (white)
            draw.text((current_x, y), char, font=font, fill="white")
            
            char_width = font.getlength(char)
            current_x += char_width

    # Draw Name with stroke
    draw_text_with_stroke(text_x + 25, text_y, name, font_large, font_large_cherokee, 4)
    
    # Draw Guild only if exists (not empty)
    if guild and guild != "Not Found" and guild.strip():
        draw_text_with_stroke(text_x + 25, text_y + 200, guild, font_small, font_small_cherokee, 3)

    # Pin image (title)
    if pin_img and pin_img.size != (100, 100):
        pin_size = 130 
        pin_img = pin_img.resize((pin_size, pin_size), Image.LANCZOS)
        combined.paste(pin_img, (0, TARGET_HEIGHT - pin_size), pin_img)

    # Level text with stroke (no background box)
    level_txt = f"Lvl.{level}"
    
    # Draw Level with stroke
    font = font_level
    try:
        bbox = draw.textbbox((0, 0), level_txt, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except:
        text_w = len(level_txt) * 30
        text_h = 50
    
    # Position level at bottom right
    x_pos = final_w - text_w - 35
    y_pos = final_h - text_h - 25
    
    # Draw level with stroke
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx != 0 or dy != 0:
                draw.text((x_pos + dx, y_pos + dy), level_txt, font=font, fill="black")
    draw.text((x_pos, y_pos), level_txt, font=font, fill="white")

    img_io = io.BytesIO()
    combined.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@app.get("/")
async def home():
    return {
        "message": "Banner API Running",
        "OWNER": "JAAT",
        "Api Endpoint": "/banner-image?uid={uid}",
    }

@app.get("/banner-image")
async def get_banner(uid: str):
    if not uid:
        raise HTTPException(status_code=400, detail="UID required")

    try:
        resp = await client.get(f"{INFO_API_URL}?uid={uid}")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Info API Error")
            
        data = resp.json()
        
        basic_info = data.get("basicInfo", {})
        if not basic_info:
            raise HTTPException(status_code=404, detail="Player not found")
        
        clan_info = data.get("clanBasicInfo", {})
        
        avatar_id = basic_info.get("headPic")
        banner_id = basic_info.get("bannerId")
        pin_id = basic_info.get("title")

        avatar_task = fetch_image_bytes(avatar_id)
        banner_task = fetch_image_bytes(banner_id)
        pin_task = fetch_image_bytes(pin_id)

        results = await asyncio.gather(avatar_task, banner_task, pin_task)
        avatar_bytes, banner_bytes, pin_bytes = results[0], results[1], results[2]
        
        if pin_bytes is None:
            pin_bytes = b''

        loop = asyncio.get_event_loop()
        banner_data = {
            "level": basic_info.get("level", "N/A"),
            "nickname": basic_info.get("nickname", "Unknown"),
            "clanName": clan_info.get("clanName", "")
        }
        
        img_io = await loop.run_in_executor(
            process_pool, 
            process_banner_image, 
            banner_data, avatar_bytes, banner_bytes, pin_bytes
        )
        
        return Response(
            content=img_io.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"}
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
