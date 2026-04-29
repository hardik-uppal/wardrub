#!/usr/bin/env python3
"""
Test script for Google Cloud Vision API - Product Identification

This script tests whether Cloud Vision API can help us identify
clothing products more accurately for better descriptions.

Tests:
1. Label Detection - Generic labels for the image
2. Web Detection - Find similar products and entities online
3. Object Localization - Detect and locate objects
4. Product Search (if configured) - Find exact product matches
"""

import os
import sys
import json
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up credentials path
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS", 
    os.path.join(os.path.dirname(__file__), "service-account.json")
)

from google.cloud import vision
from google.cloud import storage
from google.oauth2 import service_account


def get_credentials():
    """Get GCP credentials."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(creds_path)
    return None


def get_storage_client():
    """Get GCS client."""
    credentials = get_credentials()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if credentials:
        return storage.Client(project=project, credentials=credentials)
    return storage.Client(project=project)


def get_vision_client():
    """Get Vision API client."""
    credentials = get_credentials()
    if credentials:
        return vision.ImageAnnotatorClient(credentials=credentials)
    return vision.ImageAnnotatorClient()


def list_user_garments(bucket_name: str, user_id: str = None):
    """List garments from GCS bucket."""
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    
    garments = []
    
    # Try legacy format first (garments/{category}/)
    print("   Checking legacy garments format...")
    blobs = list(client.list_blobs(bucket, prefix="garments/", max_results=30))
    for blob in blobs:
        if blob.name.endswith(".png") or blob.name.endswith(".jpg"):
            garments.append({
                "name": blob.name,
                "gs_uri": f"gs://{bucket_name}/{blob.name}"
            })
    
    if garments:
        print(f"   Found {len(garments)} garments in legacy format")
        return garments
    
    # Try user-scoped format
    print("   Checking user-scoped garments format...")
    if user_id:
        prefix = f"users/{user_id}/garments/"
    else:
        # List users directory to find any user
        blobs = list(client.list_blobs(bucket, prefix="users/", max_results=50))
        user_ids = set()
        for blob in blobs:
            parts = blob.name.split("/")
            if len(parts) >= 2 and parts[0] == "users":
                user_ids.add(parts[1])
        
        if user_ids:
            user_id = list(user_ids)[0]
            print(f"   Found user: {user_id[:8]}...")
            prefix = f"users/{user_id}/garments/"
        else:
            return []
    
    blobs = list(client.list_blobs(bucket, prefix=prefix, max_results=20))
    
    for blob in blobs:
        if blob.name.endswith(".png") or blob.name.endswith(".jpg"):
            garments.append({
                "name": blob.name,
                "gs_uri": f"gs://{bucket_name}/{blob.name}"
            })
    
    return garments


def analyze_with_labels(client: vision.ImageAnnotatorClient, image_uri: str):
    """Test Label Detection on clothing image."""
    print("\n" + "="*60)
    print("📏 LABEL DETECTION")
    print("="*60)
    
    image = vision.Image()
    image.source.image_uri = image_uri
    
    response = client.label_detection(image=image)
    
    if response.error.message:
        print(f"❌ Error: {response.error.message}")
        return None
    
    labels = response.label_annotations
    print(f"Found {len(labels)} labels:\n")
    
    results = []
    for label in labels:
        confidence = label.score * 100
        results.append({
            "description": label.description,
            "confidence": confidence,
            "topicality": label.topicality
        })
        print(f"  • {label.description:30} ({confidence:.1f}% confidence)")
    
    return results


def analyze_with_web_detection(client: vision.ImageAnnotatorClient, image_uri: str):
    """Test Web Detection - finds similar images and entities online."""
    print("\n" + "="*60)
    print("🌐 WEB DETECTION (Product Matching)")
    print("="*60)
    
    image = vision.Image()
    image.source.image_uri = image_uri
    
    response = client.web_detection(image=image)
    
    if response.error.message:
        print(f"❌ Error: {response.error.message}")
        return None
    
    annotations = response.web_detection
    results = {
        "web_entities": [],
        "best_guess_labels": [],
        "matching_pages": [],
        "visually_similar": []
    }
    
    # Web Entities (this is key for product identification)
    if annotations.web_entities:
        print("\n🏷️  Web Entities (Product/Brand Detection):")
        for entity in annotations.web_entities[:10]:
            results["web_entities"].append({
                "description": entity.description,
                "score": entity.score
            })
            score = entity.score * 100 if entity.score else 0
            print(f"  • {entity.description:35} (score: {score:.1f})")
    
    # Best guess labels
    if annotations.best_guess_labels:
        print("\n🎯 Best Guess Labels:")
        for label in annotations.best_guess_labels:
            results["best_guess_labels"].append(label.label)
            print(f"  ★ {label.label}")
    
    # Pages with matching images
    if annotations.pages_with_matching_images:
        print("\n📄 Pages with Matching Images:")
        for page in annotations.pages_with_matching_images[:5]:
            results["matching_pages"].append({
                "url": page.url,
                "title": page.page_title if page.page_title else "N/A"
            })
            title = page.page_title[:50] if page.page_title else "N/A"
            print(f"  • {title}")
            print(f"    URL: {page.url[:80]}...")
    
    # Visually similar images
    if annotations.visually_similar_images:
        print(f"\n👁️  Found {len(annotations.visually_similar_images)} visually similar images")
        for img in annotations.visually_similar_images[:3]:
            results["visually_similar"].append(img.url)
    
    return results


def analyze_with_object_localization(client: vision.ImageAnnotatorClient, image_uri: str):
    """Test Object Localization - detects and locates objects."""
    print("\n" + "="*60)
    print("📍 OBJECT LOCALIZATION")
    print("="*60)
    
    image = vision.Image()
    image.source.image_uri = image_uri
    
    response = client.object_localization(image=image)
    
    if response.error.message:
        print(f"❌ Error: {response.error.message}")
        return None
    
    objects = response.localized_object_annotations
    print(f"Found {len(objects)} objects:\n")
    
    results = []
    for obj in objects:
        confidence = obj.score * 100
        results.append({
            "name": obj.name,
            "confidence": confidence
        })
        print(f"  • {obj.name:30} ({confidence:.1f}% confidence)")
    
    return results


def analyze_image_properties(client: vision.ImageAnnotatorClient, image_uri: str):
    """Test Image Properties - dominant colors."""
    print("\n" + "="*60)
    print("🎨 IMAGE PROPERTIES (Color Analysis)")
    print("="*60)
    
    image = vision.Image()
    image.source.image_uri = image_uri
    
    response = client.image_properties(image=image)
    
    if response.error.message:
        print(f"❌ Error: {response.error.message}")
        return None
    
    props = response.image_properties_annotation
    
    if props.dominant_colors and props.dominant_colors.colors:
        print("Dominant Colors:")
        results = []
        for color in props.dominant_colors.colors[:5]:
            r, g, b = int(color.color.red), int(color.color.green), int(color.color.blue)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            pixel_frac = color.pixel_fraction * 100
            results.append({
                "hex": hex_color,
                "rgb": (r, g, b),
                "pixel_fraction": pixel_frac
            })
            print(f"  • {hex_color} (RGB: {r},{g},{b}) - {pixel_frac:.1f}% of image")
        return results
    
    return None


def test_garment(vision_client, garment_uri: str, garment_name: str):
    """Run all Vision API tests on a single garment."""
    print("\n" + "🔥"*30)
    print(f"\n🧥 TESTING GARMENT: {garment_name.split('/')[-1]}")
    print(f"   URI: {garment_uri}")
    print("\n" + "🔥"*30)
    
    results = {
        "uri": garment_uri,
        "name": garment_name
    }
    
    # Run all analysis types
    results["labels"] = analyze_with_labels(vision_client, garment_uri)
    results["web_detection"] = analyze_with_web_detection(vision_client, garment_uri)
    results["objects"] = analyze_with_object_localization(vision_client, garment_uri)
    results["colors"] = analyze_image_properties(vision_client, garment_uri)
    
    return results


def summarize_results(all_results: list):
    """Summarize all test results."""
    print("\n" + "="*70)
    print("📊 SUMMARY: Vision API Evaluation for Clothing Description")
    print("="*70)
    
    print("\n🎯 KEY FINDINGS:\n")
    
    # Check label quality
    clothing_labels = set()
    all_web_entities = []
    
    for result in all_results:
        if result.get("labels"):
            for label in result["labels"]:
                desc = label["description"].lower()
                if any(kw in desc for kw in ["shirt", "pants", "dress", "jacket", "top", "bottom", "clothing", "fashion", "textile", "sleeve", "denim", "cotton"]):
                    clothing_labels.add(label["description"])
        
        if result.get("web_detection") and result["web_detection"].get("web_entities"):
            all_web_entities.extend([e["description"] for e in result["web_detection"]["web_entities"] if e["description"]])
    
    print("✅ PROS:")
    if clothing_labels:
        print(f"   • Label Detection found relevant clothing terms: {', '.join(list(clothing_labels)[:5])}")
    if all_web_entities:
        print(f"   • Web Detection found product-related entities")
    print("   • Color analysis can complement existing ColorAnalysisService")
    print("   • Object Localization can identify garment types")
    
    print("\n⚠️  CONSIDERATIONS:")
    print("   • Web Detection works best with real product photos (not ghost mannequins)")
    print("   • May not find exact product matches for unique/rare items")
    print("   • Labels are generic - may need Gemini for detailed descriptions")
    
    print("\n💡 RECOMMENDATION:")
    print("   Consider HYBRID approach:")
    print("   1. Use Vision API for: labels, color analysis, basic categorization")
    print("   2. Use Gemini for: detailed descriptions, style analysis, outfit suggestions")
    print("   3. Use Web Detection for: brand identification on original photos (before processing)")


def main():
    """Main test runner."""
    print("="*70)
    print("🔬 Google Cloud Vision API - Clothing Product Identification Test")
    print("="*70)
    
    # Check credentials
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    bucket_name = os.environ.get("GCS_BUCKET")
    
    print(f"\n📋 Configuration:")
    print(f"   Credentials: {creds_path}")
    print(f"   Bucket: {bucket_name}")
    
    if not bucket_name:
        print("\n❌ Error: GCS_BUCKET environment variable not set")
        print("   Please set it in your .env file")
        return
    
    if not creds_path or not os.path.exists(creds_path):
        print("\n❌ Error: Credentials not found")
        print(f"   Path checked: {creds_path}")
        return
    
    # Initialize clients
    try:
        vision_client = get_vision_client()
        print("\n✅ Vision API client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize Vision API client: {e}")
        print("\n📝 Make sure Vision API is enabled in your GCP project:")
        print("   https://console.cloud.google.com/apis/library/vision.googleapis.com")
        return
    
    # List available garments
    print("\n🔍 Looking for garments in GCS...")
    garments = list_user_garments(bucket_name)
    
    if not garments:
        print("❌ No garments found in bucket")
        return
    
    print(f"\n📦 Found {len(garments)} garments")
    for g in garments[:5]:
        print(f"   • {g['name'].split('/')[-1]}")
    
    # Test first few garments
    num_to_test = min(3, len(garments))
    print(f"\n🧪 Testing {num_to_test} garment(s)...")
    
    all_results = []
    for garment in garments[:num_to_test]:
        try:
            result = test_garment(vision_client, garment["gs_uri"], garment["name"])
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {garment['name']}: {e}")
    
    # Summary
    if all_results:
        summarize_results(all_results)
        
        # Save detailed results
        output_path = os.path.join(os.path.dirname(__file__), "vision_api_results.json")
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {output_path}")
    
    print("\n" + "="*70)
    print("✅ Vision API test complete!")
    print("="*70)


if __name__ == "__main__":
    main()
