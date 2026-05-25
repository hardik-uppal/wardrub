# Wardrub Magazine Feed Technical Implementation Plan

We will implement the **Magazine Feed** feature, transitioning Wardrub from a simple try-on demo to an interactive, personalized daily style guide. The feed will showcase daily cover looks, multiple fits, styling tutorials ("One Item, Three Ways"), and boost utilization of underused clothes.

---

## 1. Product Scope

- **Primary Placement:** The Magazine Feed will replace the current static `DailyOutfit` page as the primary **Home Screen** (rendered at `/` and `/daily-outfit`).
- **Onboarding Gates:** A minimum of **5 uploaded garments** (with metadata already analyzed) is required to compile the feed. Users with fewer than 5 items will be shown a premium onboarding UI checklist.
- **On-Demand Try-On:** To optimize latency and costs, try-on generation is **on-demand** (via a "Run Try-On" button on each look card) rather than pre-rendered for all feed cards. Cards will load instantly with garment collages, and try-ons will render on user request.

---

## 2. Technical Design & Architecture

### Data Models (`backend/app/models/magazine_feed.py`)

We need structured models for look cards, swap suggestions, feedback events, and the complete feed structure.

```python
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class SwapSuggestion(BaseModel):
    replace_item_id: str = Field(..., description="Garment ID to be replaced")
    with_item_id: str = Field(..., description="Alternative Garment ID from user's closet")
    reason: str = Field(..., description="Why this replacement works")

class LookCard(BaseModel):
    id: str = Field(..., description="Unique look identifier")
    title: str = Field(..., description="Editorial style title (e.g. 'Soft Sunday Neutrals')")
    subtitle: Optional[str] = Field(None, description="Optional sub-header")
    section: str = Field(..., description="cover, daily, one_item_three_ways, underused")
    garment_ids: List[str] = Field(..., description="List of garment IDs in this outfit")
    hero_item_id: Optional[str] = Field(None, description="Featured garment in this look")
    occasion: Optional[str] = Field(None, description="Occasion name (e.g. Work, Brunch)")
    why_it_works: str = Field(..., description="AI editorial explanation of style cohesion")
    styling_tips: List[str] = Field(default_factory=list, description="List of styling tips")
    swaps: List[SwapSuggestion] = Field(default_factory=list, description="Alternative garments list")
    score: float = Field(..., description="Scoring match percentage (0.0 to 1.0)")
    tryon_image_url: Optional[str] = Field(None, description="Pre-rendered tryon image URL if ran")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class MagazineFeed(BaseModel):
    user_id: str = Field(..., description="Owner ID")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    cover_look: LookCard = Field(..., description="The main featured look of the day")
    daily_fits: List[LookCard] = Field(default_factory=list, description="3 fits for the day")
    one_item_three_ways: List[LookCard] = Field(default_factory=list, description="3 fits styling one garment")
    underused_edit: LookCard = Field(..., description="Outfit showcasing a rarely worn garment")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class LookFeedback(BaseModel):
    id: str = Field(..., description="Feedback event unique ID")
    user_id: str = Field(..., description="User ID who left feedback")
    look_id: str = Field(..., description="Look card ID")
    action: str = Field(..., description="love, save, dislike, wore_this")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### Database Services (`backend/app/services/firestore.py`)

Add methods to `FirestoreService` for persistence:
- `save_magazine_feed(user_id: str, date_str: str, feed: MagazineFeed) -> bool`
- `get_magazine_feed(user_id: str, date_str: str) -> Optional[MagazineFeed]`
- `get_latest_magazine_feed(user_id: str) -> Optional[MagazineFeed]`
- `save_look_feedback(feedback: LookFeedback) -> bool`
- `list_user_feedback(user_id: str) -> List[LookFeedback]`

---

### AI Curation Pipeline (`backend/app/services/magazine_feed_service.py`)

A new `MagazineFeedService` will coordinate:
1. **Garment Gathering:** Query Firestore for user's analyzed clothes. Ensure there are at least 5 garments.
2. **Deterministic Combinations:** Generate possible tops + bottoms, outerwear layering, or dress combos.
3. **Internal Scoring:** Run `OutfitScorerService` to grade color harmony, weather range suitability, and style tag cohesion. Rank combinations.
4. **Editorial Generation via Gemini:**
   - Supply Gemini 2.0 Flash with the top-scoring combinations and individual garment details (descriptions, colors, styles, weather comfort, fit).
   - Supply past user preferences/dislikes to influence curation.
   - prompt Gemini to structure the response as a valid JSON matching the `MagazineFeed` schema, generating witty titles, descriptions, and styling/swap recommendations.
   - For "One Item, Three Ways", prompt Gemini to choose the most versatile garment in their wardrobe and build 3 distinct outfits (e.g. casual, semi-formal, street).
   - For "Underused Edit", identify a garment with low recommendations/recent uploads and style a look around it.

---

### API Router (`backend/app/routers/outfit.py`)

Expose these endpoints:
- `GET /api/magazine-feed` - Get today's feed (generated or cached). Checks if the user has >= 5 items. If not, returns onboarding status.
- `POST /api/magazine-feed/generate` - Force regenerates the feed, clearing today's cache.
- `POST /api/magazine-feed/feedback` - Receives and saves a feedback action.

---

### UI/UX Layout (`frontend/src/pages/MagazineFeed.jsx`)

1. **Onboarding State (< 5 items):**
   - High-end progress indicator (e.g. "2 / 5 garments added").
   - Guide list:
     - [x] Create style profile
     - [ ] Upload at least 5 garments
   - Direct button link to `/capture`.
2. **Editorial Magazine Feed (>= 5 items):**
   - Glassmorphic panels with subtle glowing borders.
   - Bold editorial font pairing (e.g., serif headers, modern sans-serif content).
   - **Today's Cover Look:** Prominent feature card, showing the primary outfit with a beautifully structured collage of garment icons. Includes styling notes, occasion, and the interactive try-on button.
   - **Three Fits from Your Closet:** Horizontal swipe container containing 3 styled cards.
   - **One Item, Three Ways:** 3 columns or a horizontal slider showing how to wear a single featured garment in 3 contexts.
   - **Underused Edit:** Highlighted in contrasting neon/accent colors to prompt interaction.
3. **On-Demand VTON Integration:**
   - Click "Run Try-on".
   - Shows loading overlay with animation.
   - Backend calls `/api/try-on-multiple` to render the garments onto the user's avatar.
   - The card's collage is replaced with the try-on result URL, which is then persisted in Firestore.

---

## 3. Milestones & Task Checklist

- [ ] **Milestone 1: Backend Data Models & API Contracts**
  - Define `LookCard`, `MagazineFeed`, `LookFeedback` schemas.
  - Implement Firestore save/get methods for feeds and feedback.
  - Create endpoint skeletons in `routers/outfit.py`.
- [ ] **Milestone 2: Curation Engine & Gemini Integration**
  - Implement candidate selection and internal scoring integration.
  - Formulate the Gemini prompt for editorial styling copy, title, swap suggestions.
  - Support feed caching and force-regeneration.
- [ ] **Milestone 3: UI Design System & Onboarding**
  - Add basic route mapping in `App.jsx`.
  - Create onboarding view for users with < 5 items.
  - Create the layout skeleton with Glassmorphic sections.
- [ ] **Milestone 4: Feed Rendering & Copy Display**
  - Integrate feed fetching and display item lists/collages.
  - Render title, description, occasions, styling tips.
- [ ] **Milestone 5: Interactive Try-On & Feedback Loop**
  - Connect feedback buttons to backend endpoints.
  - Implement on-demand try-on integration (calling Vertex AI try-on on click, showing result).
