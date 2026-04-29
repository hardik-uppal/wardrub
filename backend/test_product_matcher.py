#!/usr/bin/env python3
"""
Test the Product Matcher Service.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    os.path.join(os.path.dirname(__file__), "service-account.json")
)

from google.cloud import storage
from google.oauth2 import service_account


async def test_product_matcher():
    """Test the product matching flow."""
    from app.services.product_matcher import ProductMatcherService
    
    print("="*60)
    print("🔬 Product Matcher Service Test")
    print("="*60)
    
    # Initialize service
    matcher = ProductMatcherService()
    
    # Get a test image from GCS
    creds = service_account.Credentials.from_service_account_file('./service-account.json')
    client = storage.Client(project=os.environ.get('GOOGLE_CLOUD_PROJECT'), credentials=creds)
    bucket = client.bucket(os.environ.get('GCS_BUCKET'))
    
    # Find a garment to test
    blobs = list(client.list_blobs(bucket, prefix="garments/top/", max_results=5))
    
    if not blobs:
        blobs = list(client.list_blobs(bucket, prefix="garments/", max_results=5))
    
    if not blobs:
        print("❌ No garments found to test")
        return
    
    # Get first garment
    test_blob = blobs[0]
    print(f"\n📷 Testing with: {test_blob.name}")
    
    # Download image
    image_bytes = test_blob.download_as_bytes()
    print(f"   Image size: {len(image_bytes)} bytes")
    
    # Step 1: Find similar products
    print("\n" + "-"*60)
    print("🔍 STEP 1: Finding similar products...")
    print("-"*60)
    
    try:
        similar = await matcher.find_similar_products(image_bytes)
        
        print(f"\n✅ Found {len(similar['similar_products'])} similar products:")
        for i, product in enumerate(similar['similar_products'][:5]):
            print(f"   {i+1}. {product['image_url'][:70]}...")
        
        print(f"\n🏷️  Web Entities: {[e['description'] for e in similar['web_entities'][:5]]}")
        print(f"🎯 Best Guess: {similar['best_guess_labels']}")
        
        if similar['pages_with_matches']:
            print(f"\n📄 Matching Pages:")
            for page in similar['pages_with_matches'][:3]:
                print(f"   • {page.get('title', 'N/A')}")
                print(f"     {page['url'][:60]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Extract details from best match
    if similar['similar_products']:
        print("\n" + "-"*60)
        print("📝 STEP 2: Extracting product details from best match...")
        print("-"*60)
        
        best_match_url = similar['similar_products'][0]['image_url']
        print(f"   URL: {best_match_url[:70]}...")
        
        # Determine category from blob path
        parts = test_blob.name.split("/")
        category = parts[1] if len(parts) >= 2 else "top"
        
        try:
            details = await matcher.extract_product_details(
                image_url=best_match_url,
                garment_category=category,
                original_image_bytes=image_bytes
            )
            
            print(f"\n✅ Extracted Product Details:")
            print(f"   Brand:       {details.brand or 'N/A'}")
            print(f"   Product:     {details.product_name or 'N/A'}")
            print(f"   Material:    {details.material or 'N/A'}")
            print(f"   Composition: {details.fabric_composition or 'N/A'}")
            print(f"   Style:       {details.style or 'N/A'}")
            print(f"   Fit:         {details.fit or 'N/A'}")
            print(f"   Occasions:   {details.occasion}")
            print(f"   Seasons:     {details.season}")
            print(f"   Features:    {details.features}")
            print(f"   Price Range: {details.price_range or 'N/A'}")
            print(f"\n   Description: {details.description[:200]}..." if len(details.description) > 200 else f"\n   Description: {details.description}")
            
        except Exception as e:
            print(f"❌ Error extracting details: {e}")
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_product_matcher())
