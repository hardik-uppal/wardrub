#!/usr/bin/env python3
"""
Generate an image grid showing garments with their similar product matches.
"""

import asyncio
import os
import httpx
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    os.path.join(os.path.dirname(__file__), "service-account.json")
)

from PIL import Image, ImageDraw, ImageFont
from google.cloud import storage
from google.oauth2 import service_account


async def download_image(url: str) -> Image.Image:
    """Download image from URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"      Failed to download: {e}")
        return None


async def generate_match_image():
    """Generate image grid of garments and their matches."""
    from app.services.product_matcher import ProductMatcherService
    
    print("="*60)
    print("🎨 Generating Product Match Image Grid")
    print("="*60)
    
    # Initialize
    matcher = ProductMatcherService()
    creds = service_account.Credentials.from_service_account_file('./service-account.json')
    client = storage.Client(project=os.environ.get('GOOGLE_CLOUD_PROJECT'), credentials=creds)
    bucket = client.bucket(os.environ.get('GCS_BUCKET'))
    
    # Get all garments
    print("\n📦 Loading garments from GCS...")
    all_garments = []
    
    for category in ["top", "bottom", "outerwear"]:
        blobs = list(client.list_blobs(bucket, prefix=f"garments/{category}/", max_results=6))
        for blob in blobs:
            if blob.name.endswith(".png") or blob.name.endswith(".jpg"):
                all_garments.append({
                    "name": blob.name,
                    "category": category,
                    "blob": blob
                })
    
    print(f"   Found {len(all_garments)} garments")
    
    # Settings
    thumb_size = (150, 180)
    original_size = (160, 200)
    matches_per_row = 4
    padding = 15
    header_height = 40
    row_spacing = 20
    
    # Colors
    bg_color = (26, 26, 46)
    card_bg = (40, 40, 70)
    text_color = (255, 255, 255)
    accent_color = (233, 69, 96)
    
    # Process garments and collect results
    results = []
    
    for i, garment in enumerate(all_garments[:12]):  # Limit to 12 for image size
        print(f"\n🔍 [{i+1}/{min(len(all_garments), 12)}] Processing: {garment['category']}/{garment['name'].split('/')[-1][:20]}...")
        
        try:
            # Download original image
            image_bytes = garment["blob"].download_as_bytes()
            original_img = Image.open(BytesIO(image_bytes))
            
            # Find similar products
            similar = await matcher.find_similar_products(image_bytes, max_results=matches_per_row)
            
            # Download match images
            match_images = []
            for match in similar["similar_products"][:matches_per_row]:
                match_img = await download_image(match["image_url"])
                if match_img:
                    match_images.append(match_img)
            
            results.append({
                "category": garment["category"],
                "name": garment["name"].split("/")[-1][:25],
                "original": original_img,
                "matches": match_images,
                "entities": [e["description"] for e in similar["web_entities"][:3]],
                "guess": similar["best_guess_labels"][:1]
            })
            
            print(f"   ✅ Found {len(match_images)} downloadable matches")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    
    if not results:
        print("❌ No results to display")
        return
    
    # Calculate image dimensions
    row_height = original_size[1] + header_height + padding * 2
    total_width = padding + original_size[0] + padding + (thumb_size[0] + padding) * matches_per_row + padding
    total_height = padding + len(results) * (row_height + row_spacing)
    
    # Create image
    print(f"\n📝 Creating {total_width}x{total_height} image...")
    img = Image.new('RGB', (total_width, total_height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    y_offset = padding
    
    for result in results:
        # Draw row background
        row_bg = Image.new('RGB', (total_width - padding * 2, row_height), card_bg)
        img.paste(row_bg, (padding, y_offset))
        
        # Draw category badge
        badge_text = result["category"].upper()
        draw.rectangle([padding + 10, y_offset + 8, padding + 10 + len(badge_text) * 8 + 16, y_offset + 28], fill=accent_color)
        draw.text((padding + 18, y_offset + 10), badge_text, fill=text_color, font=small_font)
        
        # Draw entities/tags
        tag_x = padding + 100
        for entity in result["entities"]:
            tag_text = entity[:15]
            draw.text((tag_x, y_offset + 12), tag_text, fill=(150, 150, 200), font=small_font)
            tag_x += len(tag_text) * 7 + 15
        
        # Draw guess
        if result["guess"]:
            guess_text = f"→ {result['guess'][0]}"
            draw.text((tag_x, y_offset + 12), guess_text, fill=(46, 213, 115), font=small_font)
        
        content_y = y_offset + header_height
        
        # Draw original image
        original = result["original"].copy()
        original.thumbnail(original_size, Image.Resampling.LANCZOS)
        
        # Center the original in its box
        orig_x = padding + padding + (original_size[0] - original.width) // 2
        orig_y = content_y + (original_size[1] - original.height) // 2
        
        # Add white background for transparent images
        if original.mode == 'RGBA':
            bg = Image.new('RGB', original.size, (255, 255, 255))
            bg.paste(original, mask=original.split()[3])
            original = bg
        elif original.mode != 'RGB':
            original = original.convert('RGB')
        
        img.paste(original, (orig_x, orig_y))
        
        # Draw arrow
        arrow_x = padding + padding + original_size[0] + 5
        draw.text((arrow_x, content_y + original_size[1] // 2 - 10), "→", fill=accent_color, font=font)
        
        # Draw matches
        match_x = padding + padding + original_size[0] + padding + 20
        
        for match_img in result["matches"]:
            match_copy = match_img.copy()
            match_copy.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if match_copy.mode == 'RGBA':
                bg = Image.new('RGB', match_copy.size, (255, 255, 255))
                bg.paste(match_copy, mask=match_copy.split()[3])
                match_copy = bg
            elif match_copy.mode != 'RGB':
                match_copy = match_copy.convert('RGB')
            
            # Center in thumbnail box
            m_x = match_x + (thumb_size[0] - match_copy.width) // 2
            m_y = content_y + (thumb_size[1] - match_copy.height) // 2
            
            img.paste(match_copy, (m_x, m_y))
            match_x += thumb_size[0] + padding
        
        # Draw "Your Garment" label
        draw.text((padding + padding + 40, content_y + original_size[1] + 5), "Your Garment", fill=(136, 146, 176), font=small_font)
        
        y_offset += row_height + row_spacing
    
    # Save image
    output_path = os.path.join(os.path.dirname(__file__), "product_match_grid.png")
    img.save(output_path, "PNG", optimize=True)
    
    print(f"\n✅ Image saved to: {output_path}")
    
    return output_path


if __name__ == "__main__":
    asyncio.run(generate_match_image())
