# Wardrub Chrome Extension Plan

## 1. Vision

Build a Google Chrome extension that lets users virtually try on clothing items while browsing online stores. The extension should connect to the existing Wardrub backend, reuse the user's Wardrub avatar, capture product images from the browser, and generate AI try-on results.

The long-term experience should feel like this:

1. User browses a clothing website.
2. Wardrub detects product images on the page.
3. User clicks **Try with Wardrub** or drags the clothing item into the extension panel.
4. The extension sends the clothing image and product metadata to the Wardrub backend.
5. The backend processes the image as a garment.
6. Wardrub generates a virtual try-on using the user's avatar.
7. User can save the garment, save the generated look, or continue shopping.

---

## 2. Current Product Foundation

Wardrub already has most of the core infrastructure needed for this feature.

### Existing Backend Capabilities

The backend already supports:

- Firebase-authenticated users.
- Avatar creation and retrieval.
- Garment image processing.
- Background removal / ghost mannequin-style garment cleanup.
- Wardrobe storage in Firestore and Google Cloud Storage.
- Virtual try-on generation.
- Saved looks.
- Product matching and product metadata-related functionality.

Relevant existing endpoints include:

| Endpoint | Purpose |
|---|---|
| `GET /api/avatar` | Get current user's avatar |
| `POST /api/create-avatar` | Create user avatar |
| `POST /api/process-garment` | Upload and process garment |
| `POST /api/process-uploaded-clothes` | Detect/process clothes from uploaded image |
| `GET /api/wardrobe` | List user's wardrobe |
| `POST /api/try-on` | Try on a single garment |
| `POST /api/try-on-multiple` | Try on multiple garments |
| `GET /api/try-on/history` | Get try-on history |

### Existing Frontend Capabilities

The React frontend already supports:

- Firebase auth.
- Wardrobe browsing.
- Avatar creation.
- Dressing room.
- Try-on flow.
- Saved looks.
- Global API state through `WardrobeContext`.

The Chrome extension should not duplicate the entire frontend. Instead, it should provide a small shopping-focused interface that talks to the same backend.

---

## 3. MVP Definition

The first version should prove the main loop:

> A user can click a clothing item on a shopping website and see it tried on their Wardrub avatar.

### MVP User Flow

1. User installs the Wardrub Chrome extension.
2. User opens the extension side panel.
3. User signs in with their Wardrub/Firebase account.
4. The side panel loads the user's avatar.
5. User visits a shopping/product page.
6. Wardrub injects a **Try with Wardrub** button on likely product images.
7. User clicks the button.
8. Extension sends product image URL and metadata to backend.
9. Backend downloads and processes the product image.
10. Backend runs virtual try-on using user's avatar.
11. Side panel displays the result.
12. User can save the garment or the generated look.

### MVP Should Include

- Chrome Manifest V3 extension.
- Side panel UI.
- Firebase authentication or web-app linked auth.
- Content script that detects product images.
- Injected **Try with Wardrub** button.
- Backend endpoint for try-on from image URL.
- Basic product metadata capture:
  - image URL
  - page URL
  - page title
  - merchant domain
  - optional product title
  - optional price
- Result display.
- Save garment / save look actions if practical.

### MVP Should Not Initially Include

These are valuable but should come later:

- Perfect drag/drop behavior across every website.
- Merchant-specific integrations for every store.
- Screenshot cropping fallback.
- Affiliate links.
- Multi-item outfit building from browser pages.
- Complex product variant handling.
- Checkout/cart integrations.

---

## 4. Recommended UX

### Primary UX: Chrome Side Panel

Use Chrome's Side Panel API instead of a small popup. A side panel is better because try-on is visual and benefits from persistent space while the user shops.

```text
Shopping Website                         Wardrub Side Panel
┌──────────────────────────────┐         ┌─────────────────────────┐
│ Product Page                  │         │ Wardrub                 │
│                               │         │                         │
│   Product Image               │         │ Your Avatar             │
│   ┌──────────────┐            │         │ [ avatar image ]        │
│   │    jacket    │            │         │                         │
│   │              │            │ click   │ Selected Item           │
│   │ Try Wardrub  │────────────┼───────► │ [ product image ]       │
│   └──────────────┘            │         │                         │
│                               │         │ [ Try On ]              │
└──────────────────────────────┘         └─────────────────────────┘
```

### Side Panel States

#### State 1: Signed Out

```text
Wardrub

Try on clothes while you shop.

[ Sign in with Google ]
```

#### State 2: Signed In, No Avatar

```text
Wardrub

You need a Wardrub avatar first.

[ Create Avatar in Wardrub ]
```

#### State 3: Ready

```text
Wardrub

Your Avatar
[ avatar preview ]

Select clothing from the current page.

[ Waiting for item... ]
```

#### State 4: Product Selected

```text
Wardrub

Your Avatar
[ avatar preview ]

Selected Item
[ product image ]
Product title
Merchant

[ Try On ]
[ Save to Wardrobe ]
```

#### State 5: Generating

```text
Wardrub

Generating your try-on...
This may take a moment.

[ loading animation ]
```

#### State 6: Result

```text
Wardrub

Generated Look
[ try-on result image ]

[ Save Look ]
[ Save Garment ]
[ Try Another ]
[ Open in Wardrub ]
```

---

## 5. High-Level Architecture

```text
Chrome Extension
├── content script
│   ├── runs on shopping/product pages
│   ├── detects product-like images
│   ├── injects Try with Wardrub buttons
│   ├── extracts product metadata
│   └── sends selected product to extension background
│
├── background service worker
│   ├── manages extension lifecycle
│   ├── receives messages from content scripts
│   ├── stores selected product state
│   ├── opens/focuses side panel
│   └── proxies/authenticates backend calls if needed
│
├── side panel React UI
│   ├── handles sign-in
│   ├── displays avatar
│   ├── displays selected product
│   ├── calls try-on API
│   ├── shows generated result
│   └── exposes save actions
│
└── Wardrub Backend
    ├── authenticates Firebase user
    ├── downloads product image
    ├── validates image safely
    ├── processes garment
    ├── loads user's avatar
    ├── runs virtual try-on
    ├── stores temporary garment/look
    └── returns result URLs
```

---

## 6. Proposed Extension Folder Structure

Add a new top-level folder:

```text
extension/
├── manifest.json
├── package.json
├── package-lock.json
├── vite.config.js
├── index.html
├── src/
│   ├── background/
│   │   └── background.js
│   │
│   ├── content/
│   │   ├── contentScript.js
│   │   ├── imageDetection.js
│   │   ├── productMetadata.js
│   │   └── injectedButton.css
│   │
│   ├── sidepanel/
│   │   ├── index.html
│   │   ├── main.jsx
│   │   ├── SidePanel.jsx
│   │   ├── components/
│   │   │   ├── AuthGate.jsx
│   │   │   ├── AvatarCard.jsx
│   │   │   ├── ProductCard.jsx
│   │   │   ├── TryOnResult.jsx
│   │   │   └── LoadingState.jsx
│   │   └── sidepanel.css
│   │
│   ├── popup/
│   │   ├── index.html
│   │   ├── main.jsx
│   │   └── Popup.jsx
│   │
│   └── shared/
│       ├── api.js
│       ├── auth.js
│       ├── config.js
│       ├── messaging.js
│       ├── storage.js
│       └── types.js
```

The popup can be minimal or optional. It can simply open the side panel.

---

## 7. Chrome Manifest Plan

Use Manifest V3.

Initial development manifest:

```json
{
  "manifest_version": 3,
  "name": "Wardrub Try-On",
  "version": "0.1.0",
  "description": "Virtually try on clothes while browsing online stores.",
  "permissions": [
    "storage",
    "activeTab",
    "scripting",
    "sidePanel",
    "contextMenus"
  ],
  "host_permissions": [
    "https://*/*",
    "http://*/*",
    "http://localhost:8000/*"
  ],
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["https://*/*", "http://*/*"],
      "js": ["contentScript.js"],
      "css": ["contentScript.css"],
      "run_at": "document_idle"
    }
  ],
  "side_panel": {
    "default_path": "sidepanel/index.html"
  },
  "action": {
    "default_title": "Wardrub"
  }
}
```

### Production Permission Goal

For production, reduce broad permissions where possible.

Possible approaches:

1. Use `activeTab` and inject only when the user clicks the extension.
2. Ask for optional host permissions for supported shopping domains.
3. Start with broad permissions during internal testing, then restrict before store submission.

---

## 8. Product Image Detection Plan

### MVP Detection Strategy

The content script should scan for likely product images:

- `img` elements with width and height above a threshold.
- Images near product-related text.
- Open Graph image fallback.
- Large images visible in viewport.

Initial heuristic:

```text
candidate if:
- rendered width >= 220px
- rendered height >= 220px
- visible on page
- not likely a logo/icon/avatar
- source URL exists
```

### Image Sources to Check

For each image element, inspect:

- `currentSrc`
- `src`
- `srcset`
- `data-src`
- `data-srcset`
- `data-original`
- `data-zoom-image`
- `data-image`

For CSS background images, inspect:

- `getComputedStyle(element).backgroundImage`

### Choosing Best `srcset` Candidate

When an image has `srcset`, choose the largest candidate by width descriptor:

```text
small.jpg 400w, medium.jpg 800w, large.jpg 1200w
```

Pick `large.jpg`.

### Product Metadata Extraction

Try to collect:

```json
{
  "image_url": "https://store.com/product.jpg",
  "page_url": "https://store.com/product/123",
  "page_title": "Example Jacket - Store",
  "merchant_domain": "store.com",
  "product_title": "Example Jacket",
  "price": "$89",
  "brand": "Example Brand"
}
```

MVP metadata sources:

1. `document.title`
2. Open Graph tags:
   - `og:title`
   - `og:image`
   - `product:price:amount`
   - `product:brand`
3. JSON-LD structured data:
   - `Product.name`
   - `Product.image`
   - `Product.brand`
   - `Product.offers.price`
4. Visible nearby text if needed.

---

## 9. Button Injection Plan

For each candidate image, inject a small overlay button:

```text
Try with Wardrub
```

### Behavior

- Button appears on hover or is always visible in the corner of candidate product images.
- On click:
  1. Prevent the website's default click behavior.
  2. Extract image URL and metadata.
  3. Send message to background worker.
  4. Background opens side panel.
  5. Side panel receives selected product.

### Message Shape

```json
{
  "type": "WARDRUB_PRODUCT_SELECTED",
  "payload": {
    "imageUrl": "https://store.com/image.jpg",
    "pageUrl": "https://store.com/product",
    "title": "Black Denim Jacket",
    "brand": "Example Brand",
    "price": "$89",
    "merchant": "store.com"
  }
}
```

---

## 10. Drag/Drop Plan

Drag/drop should be a phase-two enhancement.

### Why Not First

Dragging data between a website content script and an extension side panel can be inconsistent because:

- Content scripts run in isolated worlds.
- Websites may prevent default drag behavior.
- Product images are often wrapped in links or galleries.
- Some sites use canvas, background images, or lazy-loaded custom components.

### Later Implementation

Add draggable overlays to product images.

On drag start:

```js
event.dataTransfer.setData(
  "application/x-wardrub-product",
  JSON.stringify(productPayload)
);
event.dataTransfer.setData("text/uri-list", productPayload.imageUrl);
event.dataTransfer.setData("text/plain", productPayload.imageUrl);
```

Side panel drop zone reads:

1. `application/x-wardrub-product`
2. `text/uri-list`
3. `text/plain`

Fallback: if only an image URL is available, use that.

---

## 11. Backend API Additions

Add a new router:

```text
backend/app/routers/extension.py
```

Register it in:

```text
backend/app/main.py
```

### Endpoint 1: Try On Product From URL

```http
POST /api/extension/try-on-product
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json
```

Request:

```json
{
  "image_url": "https://example.com/product.jpg",
  "page_url": "https://example.com/products/123",
  "title": "Oversized Linen Shirt",
  "brand": "Example Brand",
  "price": "$59",
  "merchant": "example.com"
}
```

Response:

```json
{
  "garment_id": "temp_garment_123",
  "look_id": "temp_look_456",
  "processed_garment_url": "https://storage.googleapis.com/...",
  "result_url": "https://storage.googleapis.com/...",
  "status": "completed"
}
```

Backend flow:

```text
Validate authenticated user
  ↓
Validate image URL safely
  ↓
Download product image
  ↓
Validate content type and file size
  ↓
Upload original image to GCS
  ↓
Process image into clean garment representation
  ↓
Create temporary garment record in Firestore
  ↓
Load user's avatar
  ↓
Run virtual try-on
  ↓
Store generated result
  ↓
Create temporary look record
  ↓
Return result URL and IDs
```

### Endpoint 2: Save Temporary Garment

```http
POST /api/extension/save-garment
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json
```

Request:

```json
{
  "garment_id": "temp_garment_123"
}
```

Response:

```json
{
  "saved": true,
  "garment_id": "garment_123"
}
```

Purpose:

- Convert temporary browser-discovered garment into a permanent wardrobe item.

### Endpoint 3: Save Temporary Look

```http
POST /api/extension/save-look
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json
```

Request:

```json
{
  "look_id": "temp_look_456"
}
```

Response:

```json
{
  "saved": true,
  "look_id": "look_456"
}
```

Purpose:

- Convert generated extension try-on into a saved look.

### Endpoint 4: Extension Bootstrap

```http
GET /api/extension/bootstrap
Authorization: Bearer <Firebase ID Token>
```

Response:

```json
{
  "user": {
    "id": "firebase_uid",
    "email": "user@example.com"
  },
  "avatar_url": "https://storage.googleapis.com/...",
  "has_avatar": true
}
```

Purpose:

- Let the extension quickly initialize.
- Avoid multiple calls from side panel startup.

---

## 12. Backend Security Requirements

URL ingestion must be treated carefully because the server will fetch arbitrary URLs.

### SSRF Protection

Block requests to:

- `localhost`
- `127.0.0.0/8`
- `0.0.0.0/8`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `169.254.0.0/16`
- IPv6 private/local ranges
- internal GCP metadata IPs, especially `169.254.169.254`

Only allow:

- `http`
- `https`

Add redirect limits:

- Maximum 3 redirects.
- Re-validate every redirect target.

### Image Validation

Require:

- Allowed content types:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
- Maximum file size, e.g. 10 MB.
- Reasonable dimensions.
- Decode image with Pillow before trusting it.

### Abuse Protection

Add:

- Firebase auth required.
- Per-user rate limits.
- Request size limits.
- Timeout on image download.
- Logging for failed attempts.

### Metadata Sanitization

Sanitize fields:

- title
- brand
- price
- merchant
- page URL

Do not store arbitrary HTML.

---

## 13. Data Model Additions

Garments created from browser products should carry source metadata.

Example garment metadata:

```json
{
  "source": "chrome_extension",
  "source_url": "https://store.com/products/jacket",
  "source_image_url": "https://store.com/images/jacket.jpg",
  "merchant": "store.com",
  "product_title": "Black Denim Jacket",
  "brand": "Example Brand",
  "price": "$89",
  "saved_from_browser": true,
  "temporary": true,
  "created_at": "2026-04-28T00:00:00Z"
}
```

### Temporary vs Permanent Records

Use temporary records for quick try-ons.

Benefits:

- User can try many items without cluttering wardrobe.
- User saves only items they like.
- Temporary records can be garbage-collected later.

Recommended fields:

```json
{
  "temporary": true,
  "expires_at": "2026-05-05T00:00:00Z"
}
```

A scheduled cleanup job can remove expired temporary garments and looks.

---

## 14. Authentication Plan

The main app already uses Firebase Auth. The extension should authenticate against the same Firebase project.

### Option A: Firebase Auth Directly Inside Extension

The extension includes Firebase config and signs users in with Google.

Pros:

- Reuses existing Firebase identity.
- Backend can verify the same ID token.
- Clean long-term architecture.

Cons:

- Chrome extension OAuth configuration can be annoying.
- Popup-based Firebase auth may need special handling.

### Option B: Link Through Wardrub Web App

The extension opens the Wardrub web app for login. The web app gives the extension a short-lived linking token.

Pros:

- Easier if web login already works well.
- Avoids some extension OAuth issues.

Cons:

- Requires additional backend token exchange flow.
- More custom code.

### Recommendation

Start with Firebase Auth inside the extension. If Chrome extension auth becomes difficult, switch to web-app linking.

---

## 15. Extension API Client Plan

Create:

```text
extension/src/shared/api.js
```

Responsibilities:

- Read API base URL from config.
- Attach Firebase ID token.
- Call extension backend endpoints.
- Normalize errors for UI.

Example methods:

```js
bootstrapExtension()
tryOnProduct(productPayload)
saveGarment(garmentId)
saveLook(lookId)
```

---

## 16. Messaging Plan

Create:

```text
extension/src/shared/messaging.js
```

Message types:

```js
WARDRUB_PRODUCT_SELECTED
WARDRUB_OPEN_SIDE_PANEL
WARDRUB_GET_SELECTED_PRODUCT
WARDRUB_SELECTED_PRODUCT_UPDATED
WARDRUB_TRY_ON_STARTED
WARDRUB_TRY_ON_COMPLETED
WARDRUB_TRY_ON_FAILED
```

### Flow

```text
content script
  → chrome.runtime.sendMessage(WARDRUB_PRODUCT_SELECTED)
background
  → stores selected product in chrome.storage.session
background
  → opens side panel
side panel
  → reads selected product from storage/message
side panel
  → calls backend try-on endpoint
```

---

## 17. Handling Images That Backend Cannot Download

Some stores block server-side image downloads with CDN protections, referrer checks, signed URLs, or cookies.

### MVP

Try server-side URL download first.

### Fallback 1: Extension Fetches Blob

The extension fetches the image in the browser context and uploads the blob to backend.

Add backend endpoint:

```http
POST /api/extension/try-on-product-upload
Content-Type: multipart/form-data
```

Fields:

- image file
- page URL
- title
- brand
- price
- merchant

### Fallback 2: Screenshot Crop

Later, use Chrome APIs to capture a screenshot and crop the product image area.

This is more complex and should not be MVP.

---

## 18. Development Phases

## Phase 1: Backend URL Try-On Endpoint

Goal:

- Given an authenticated user and a product image URL, generate a try-on result.

Tasks:

1. Add `backend/app/routers/extension.py`.
2. Add request/response Pydantic models.
3. Implement secure image URL downloader.
4. Reuse existing storage service to upload original image.
5. Reuse existing garment processing pipeline.
6. Create temporary garment metadata.
7. Load current user's avatar.
8. Reuse try-on generation service.
9. Store result as temporary look.
10. Return result URL.
11. Add route registration in `backend/app/main.py`.
12. Test with a direct product image URL.

Deliverable:

```text
curl -X POST /api/extension/try-on-product ...
```

returns a generated try-on image.

---

## Phase 2: Extension Skeleton

Goal:

- Chrome extension loads locally and opens side panel.

Tasks:

1. Create `extension/` folder.
2. Set up Vite + React.
3. Add `manifest.json`.
4. Add background service worker.
5. Add side panel page.
6. Add minimal styling.
7. Add API config for local backend.
8. Add local build script.
9. Load unpacked extension in Chrome.

Deliverable:

```text
Click extension icon → Wardrub side panel opens.
```

---

## Phase 3: Extension Authentication

Goal:

- User can sign in and extension can call authenticated backend endpoints.

Tasks:

1. Add Firebase config to extension.
2. Implement sign-in flow.
3. Store auth state.
4. Get Firebase ID token.
5. Call `/api/extension/bootstrap`.
6. Display user's avatar or avatar missing state.

Deliverable:

```text
Side panel displays signed-in user's avatar.
```

---

## Phase 4: Product Selection From Page

Goal:

- User can select product image from current webpage.

Tasks:

1. Add content script.
2. Implement image candidate detection.
3. Inject **Try with Wardrub** button.
4. Extract image URL.
5. Extract basic product metadata.
6. Send selected product to background worker.
7. Store selected product in `chrome.storage.session`.
8. Open/focus side panel.
9. Side panel displays selected product.

Deliverable:

```text
Click Try with Wardrub on product image → image appears in side panel.
```

---

## Phase 5: Try-On Flow in Side Panel

Goal:

- Selected product can be tried on user avatar.

Tasks:

1. Add **Try On** button.
2. Call `/api/extension/try-on-product`.
3. Show loading state.
4. Display result image.
5. Show backend errors clearly.
6. Add retry action.

Deliverable:

```text
Selected browser product → generated Wardrub try-on result.
```

---

## Phase 6: Save Actions

Goal:

- User can save useful results.

Tasks:

1. Add **Save Garment** button.
2. Call `/api/extension/save-garment`.
3. Add **Save Look** button.
4. Call `/api/extension/save-look`.
5. Show success state.
6. Add **Open in Wardrub** link.

Deliverable:

```text
User can save browser product to wardrobe and save generated look.
```

---

## Phase 7: Drag/Drop Enhancement

Goal:

- Support dropping clothing items onto avatar/side panel.

Tasks:

1. Make product overlays draggable.
2. Attach product data to drag event.
3. Add side panel drop zone.
4. Parse drag payload.
5. Fallback to image URL if full product payload unavailable.
6. Test across several shopping websites.

Deliverable:

```text
User can drag product image into side panel to start try-on.
```

---

## Phase 8: Robustness and Store-Specific Polish

Goal:

- Improve reliability across major retailers.

Tasks:

1. Add JSON-LD product parsing.
2. Add Open Graph parsing.
3. Improve image gallery detection.
4. Add merchant-specific selectors for common stores.
5. Add blob upload fallback.
6. Add screenshot crop fallback if necessary.
7. Add better error messages for blocked images.
8. Add metrics/logging.

Deliverable:

```text
Extension works reliably across common shopping sites.
```

---

## 19. Testing Plan

### Backend Tests

Test cases:

- Valid image URL.
- Invalid URL.
- Non-image URL.
- Image over size limit.
- Redirect to private IP.
- Private IP URL blocked.
- Missing avatar.
- Auth missing.
- Auth invalid.
- Try-on generation failure.

### Extension Tests

Manual test pages:

- Simple product page with normal `img`.
- Product page using `srcset`.
- Lazy-loaded image page.
- CSS background image page.
- Page with many non-product images.

Test flows:

1. Sign in.
2. Display avatar.
3. Select product image.
4. Run try-on.
5. Save garment.
6. Save look.
7. Sign out.
8. Reload extension.

### Real Store Smoke Tests

Try common retailers after MVP:

- Zara
- H&M
- Uniqlo
- Nike
- Adidas
- ASOS
- Amazon fashion pages

---

## 20. Observability

Add logs for:

- Extension endpoint calls.
- Product image download failures.
- Image validation failures.
- Try-on generation duration.
- Try-on success/failure.
- Save garment/look actions.

Avoid logging sensitive tokens or full user personal data.

Useful backend metrics:

- `extension_tryon_started`
- `extension_tryon_completed`
- `extension_tryon_failed`
- `extension_image_download_failed`
- `extension_save_garment`
- `extension_save_look`

---

## 21. Main Risks

### Risk 1: Product Images Are Hard to Extract

Mitigation:

- Start with simple image detection.
- Add Open Graph and JSON-LD parsing.
- Add blob upload fallback.
- Add merchant-specific improvements later.

### Risk 2: Server Cannot Download CDN Images

Mitigation:

- Add browser-side blob upload fallback.
- Preserve original page referrer if safe/allowed.
- Later add screenshot crop fallback.

### Risk 3: Extension Auth Complexity

Mitigation:

- Try Firebase auth inside extension first.
- If difficult, use web-app linking flow.

### Risk 4: Try-On Latency

Mitigation:

- Show clear loading UI.
- Store async job status if generation takes too long.
- Consider background job endpoint later.

### Risk 5: Wardrobe Pollution

Mitigation:

- Use temporary garments by default.
- Save only on explicit user action.
- Add cleanup job for expired temporary records.

---

## 22. Future Features

After the MVP works, we can add:

- True drag/drop onto avatar.
- Multi-item outfit composition from different websites.
- Browser shopping cart import.
- Price tracking for saved items.
- Store/brand preference learning.
- Affiliate link support.
- Compare multiple products side by side.
- Share generated looks.
- Mobile browser/share-sheet equivalent.
- Automatic outfit recommendations from products on current page.
- Color and fit scoring before trying on.
- Similar product recommendations from user's existing wardrobe.

---

## 23. Recommended Immediate Next Step

Start with backend because it proves the hardest technical dependency.

### Step 1

Implement:

```text
backend/app/routers/extension.py
```

with:

```text
POST /api/extension/try-on-product
GET /api/extension/bootstrap
```

### Step 2

Test using a direct image URL from a product page.

### Step 3

Once the backend returns a try-on result, build the extension side panel around it.

This keeps the project moving with a clear vertical slice:

```text
Product image URL → backend → processed garment → avatar try-on → result image
```
