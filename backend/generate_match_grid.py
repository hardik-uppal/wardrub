#!/usr/bin/env python3
"""
Generate an HTML grid showing garments with their similar product matches.
"""

import asyncio
import os
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    os.path.join(os.path.dirname(__file__), "service-account.json")
)

from google.cloud import storage
from google.oauth2 import service_account


async def generate_match_grid():
    """Generate HTML grid of garments and their matches."""
    from app.services.product_matcher import ProductMatcherService
    
    print("="*60)
    print("🎨 Generating Product Match Grid")
    print("="*60)
    
    # Initialize
    matcher = ProductMatcherService()
    creds = service_account.Credentials.from_service_account_file('./service-account.json')
    client = storage.Client(project=os.environ.get('GOOGLE_CLOUD_PROJECT'), credentials=creds)
    bucket = client.bucket(os.environ.get('GCS_BUCKET'))
    
    # Get all garments
    print("\n📦 Loading garments from GCS...")
    all_garments = []
    
    for category in ["top", "bottom", "dress", "outerwear"]:
        blobs = list(client.list_blobs(bucket, prefix=f"garments/{category}/", max_results=10))
        for blob in blobs:
            if blob.name.endswith(".png") or blob.name.endswith(".jpg"):
                all_garments.append({
                    "name": blob.name,
                    "category": category,
                    "blob": blob
                })
    
    print(f"   Found {len(all_garments)} garments")
    
    # Process each garment
    results = []
    
    for i, garment in enumerate(all_garments):
        print(f"\n🔍 [{i+1}/{len(all_garments)}] Processing: {garment['name'].split('/')[-1][:30]}...")
        
        try:
            # Download image
            image_bytes = garment["blob"].download_as_bytes()
            
            # Convert to base64 for HTML display
            garment_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Find similar products
            similar = await matcher.find_similar_products(image_bytes, max_results=5)
            
            results.append({
                "name": garment["name"].split("/")[-1],
                "category": garment["category"],
                "image_b64": garment_b64,
                "similar_products": similar["similar_products"][:5],
                "web_entities": similar["web_entities"][:3],
                "best_guess": similar["best_guess_labels"],
                "pages": similar.get("pages_with_matches", [])[:2]
            })
            
            print(f"   ✅ Found {len(similar['similar_products'])} matches")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "name": garment["name"].split("/")[-1],
                "category": garment["category"],
                "image_b64": None,
                "similar_products": [],
                "web_entities": [],
                "best_guess": [],
                "error": str(e)
            })
    
    # Generate HTML
    print("\n📝 Generating HTML grid...")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wardrub - Product Match Grid</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #e94560, #f39c12);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            text-align: center;
            color: #8892b0;
            margin-bottom: 30px;
        }}
        .garment-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .category-badge {{
            background: linear-gradient(135deg, #e94560, #f39c12);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .garment-name {{
            font-size: 0.9em;
            color: #8892b0;
            font-family: monospace;
        }}
        .tags {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        .tag {{
            background: rgba(233, 69, 96, 0.2);
            color: #e94560;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75em;
        }}
        .tag.guess {{
            background: rgba(46, 213, 115, 0.2);
            color: #2ed573;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 20px;
            align-items: start;
        }}
        .original {{
            text-align: center;
        }}
        .original img {{
            width: 180px;
            height: 220px;
            object-fit: contain;
            background: #fff;
            border-radius: 12px;
            padding: 10px;
        }}
        .original-label {{
            margin-top: 8px;
            font-size: 0.8em;
            color: #8892b0;
        }}
        .matches {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .match-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            overflow: hidden;
            width: 150px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, border-color 0.2s;
        }}
        .match-card:hover {{
            transform: translateY(-5px);
            border-color: #e94560;
        }}
        .match-card img {{
            width: 150px;
            height: 180px;
            object-fit: cover;
            background: #fff;
        }}
        .match-info {{
            padding: 10px;
            font-size: 0.75em;
            color: #8892b0;
        }}
        .no-matches {{
            color: #666;
            font-style: italic;
            padding: 20px;
        }}
        .arrow {{
            font-size: 2em;
            color: #e94560;
            align-self: center;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #e94560, #f39c12);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{
            color: #8892b0;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
            .matches {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <h1>🔍 Wardrub Product Match Grid</h1>
    <p class="subtitle">Vision API finds similar products • Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{len(results)}</div>
            <div class="stat-label">Garments</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sum(len(r['similar_products']) for r in results)}</div>
            <div class="stat-label">Matches Found</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len([r for r in results if r['similar_products']])}</div>
            <div class="stat-label">With Matches</div>
        </div>
    </div>
"""
    
    for result in results:
        entities_html = "".join([f'<span class="tag">{e["description"]}</span>' for e in result["web_entities"]])
        guess_html = "".join([f'<span class="tag guess">{g}</span>' for g in result["best_guess"]])
        
        if result.get("image_b64"):
            original_img = f'<img src="data:image/png;base64,{result["image_b64"]}" alt="Original">'
        else:
            original_img = '<div style="width:180px;height:220px;background:#333;display:flex;align-items:center;justify-content:center;">Error</div>'
        
        matches_html = ""
        if result["similar_products"]:
            for j, match in enumerate(result["similar_products"]):
                # Get domain from URL for display
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(match["image_url"]).netloc.replace("www.", "")[:20]
                except:
                    domain = "Unknown"
                
                matches_html += f'''
                <div class="match-card">
                    <img src="{match["image_url"]}" alt="Match {j+1}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22180%22><rect fill=%22%23333%22 width=%22150%22 height=%22180%22/><text x=%2275%22 y=%2290%22 fill=%22%23666%22 text-anchor=%22middle%22>No Image</text></svg>'">
                    <div class="match-info">{domain}</div>
                </div>
                '''
        else:
            matches_html = '<div class="no-matches">No similar products found</div>'
        
        html += f'''
    <div class="garment-section">
        <div class="section-header">
            <span class="category-badge">{result["category"]}</span>
            <span class="garment-name">{result["name"][:40]}</span>
            <div class="tags">
                {entities_html}
                {guess_html}
            </div>
        </div>
        <div class="grid">
            <div class="original">
                {original_img}
                <div class="original-label">Your Garment</div>
            </div>
            <div class="matches">
                {matches_html}
            </div>
        </div>
    </div>
'''
    
    html += """
</body>
</html>
"""
    
    # Save HTML
    output_path = os.path.join(os.path.dirname(__file__), "product_match_grid.html")
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"\n✅ Grid saved to: {output_path}")
    print(f"   Open in browser to view!")
    
    return output_path


if __name__ == "__main__":
    asyncio.run(generate_match_grid())
