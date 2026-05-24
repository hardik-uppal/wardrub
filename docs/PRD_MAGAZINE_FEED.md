# PRD: Wardrub Magazine Feed

**Status:** Draft for review  
**Owner:** Hardik + Bud  
**Created:** 2026-05-24  
**Product:** Wardrub  
**Working tagline:** Your closet, curated like a fashion magazine.

---

## 1. Executive Summary

Wardrub should evolve from a virtual try-on utility into a daily style companion. The **Magazine Feed** is a personalized editorial feed that creates outfit ideas, style stories, and daily looks using clothes the user already owns.

Instead of asking the user to manually pick garments and run try-on every time, Wardrub proactively answers:

> “What can I wear today from my own closet?”

The feed should feel like a fashion magazine built around the user’s wardrobe: curated, visual, opinionated, and useful. Photorealistic virtual try-on is optional for v1. The MVP can create high-value outfit cards using garment photos, extracted metadata, styling logic, and LLM-generated editorial copy.

---

## 2. Product Thesis

Virtual try-on is impressive, but it is not the only core user value. Users often need help with **choice, curation, and confidence** more than they need a perfect generated image.

The Magazine Feed is a better first wedge because it is:

- easier to ship than high-fidelity VTON,
- habit-forming as a daily/weekly experience,
- powered by the user’s existing wardrobe data,
- a strong foundation for learning personal taste,
- compatible with future VTON as a premium visual layer.

If Wardrub becomes the app that says, “Here are five good looks from clothes you already own,” it can become a daily product, not just a novelty try-on demo.

---

## 3. Goals

### Product Goals

1. Make Wardrub useful even before perfect virtual try-on exists.
2. Turn uploaded wardrobe items into actionable outfit recommendations.
3. Create a premium, editorial experience that feels curated rather than algorithmic.
4. Learn user taste through lightweight feedback.
5. Provide a natural surface for future chatbot, social voting, shopping, and VTON features.

### User Goals

1. Discover outfits from clothes they already own.
2. Save time choosing what to wear.
3. Feel more confident that an outfit “works.”
4. Reuse under-worn items in new combinations.
5. Get recommendations for different occasions, weather, moods, and constraints.

### Business/Product Goals

1. Increase repeat usage.
2. Increase wardrobe upload completion.
3. Create a differentiated product experience beyond generic try-on.
4. Generate future monetization paths:
   - premium style feed,
   - AI stylist/chatbot,
   - affiliate “complete the look” suggestions,
   - premium try-on renders.

---

## 4. Non-Goals for MVP

The MVP should **not** require:

- photorealistic try-on generation for every outfit,
- body measurement accuracy,
- size/fit prediction,
- full social/friend collaboration,
- automated shopping purchases,
- professional stylist-grade accuracy,
- a large wardrobe dataset from day one.

V1 should prove: **given a small wardrobe, can Wardrub create useful and delightful outfit ideas?**

---

## 5. Target User

### Primary User

A style-curious person who owns clothes but still struggles with outfit decisions.

They may say:

- “I have clothes but don’t know what to wear.”
- “I always wear the same combinations.”
- “I want to look put together without overthinking.”
- “I want a Pinterest/magazine-like feed, but from my own closet.”

### Early Wardrub User

For our current product stage, assume:

- user has uploaded 10–50 clothing items,
- item photos may be imperfect,
- metadata may need AI tagging plus occasional correction,
- user is okay with recommendations shown as garment cards before full try-on.

---

## 6. Core User Stories

### Wardrobe Upload

- As a user, I upload clothes so Wardrub can understand what I own.
- As a user, I can correct wrong tags so recommendations improve.

### Feed Consumption

- As a user, I open Wardrub and see a personalized feed of looks from my closet.
- As a user, I can browse looks by mood, occasion, weather, or item.
- As a user, I can understand why an outfit works.
- As a user, I can save a look for later.

### Feedback

- As a user, I can say “love this,” “not my style,” “too formal,” “too casual,” or “I wore this.”
- As a user, I expect future recommendations to adapt to my feedback.

### Item-Centric Exploration

- As a user, I can pick one clothing item and ask, “show me three ways to wear this.”

### Future Chatbot

- As a user, I can ask: “What should I wear for dinner tonight?” and Wardrub returns a magazine-style answer using my wardrobe.

---

## 7. MVP Scope

### MVP Feature Set

1. **Wardrobe Item Tagging**
   - Infer category, color, style, material, formality, season, and occasion tags.
   - Store generated metadata with confidence.
   - Allow manual correction later; manual correction can be a post-MVP feature if needed.

2. **Outfit Candidate Generator**
   - Build valid combinations from uploaded clothes.
   - Start simple:
     - top + bottom + shoes,
     - optional jacket/outerwear,
     - optional accessory.
   - Filter obviously bad combinations.

3. **Editorial Look Cards**
   - Generate title, short description, why-it-works explanation, occasion, and swap suggestions.
   - Example card:
     - Title: “Soft Sunday Neutrals”
     - Items: cream tee + relaxed denim + white sneakers
     - Why it works: “Low contrast, clean silhouette, relaxed without looking lazy.”

4. **Magazine Feed UI**
   - Feed sections:
     - Today’s Cover Look
     - Three Fits From Your Closet
     - One Item, Three Ways
     - Underused Item Pick
   - Mobile-first, visually editorial.

5. **Feedback Buttons**
   - Love
   - Save
   - Not my style
   - Too formal / too casual
   - I wore this

6. **Basic Preference Loop**
   - Store feedback events.
   - Use feedback to re-rank future looks.

---

## 8. Post-MVP / Future Scope

### V1.5

- Weather-aware outfits.
- Calendar/occasion-aware suggestions.
- Chatbot interface for outfit requests.
- Better “complete the look” shopping recommendations.
- Social/friend voting.
- Wardrobe gap analysis.

### V2

- Photorealistic try-on render for selected look cards.
- Personalized avatar integration.
- Style profile learning.
- Multi-person/family wardrobe.
- Travel packing assistant.
- Outfit planning calendar.

---

## 9. Key Product Principle: Taste Beats Volume

The feed should not generate endless random outfit combinations. The user does not need 100 looks. They need 3–7 good ones.

The product should optimize for:

- confidence,
- taste,
- novelty without weirdness,
- practical context,
- explainability.

Bad version:

> Here are 57 combinations.

Good version:

> Here are 5 looks. Start with this one.

---

## 10. Data Model Draft

### WardrobeItem

```ts
type WardrobeItem = {
  id: string;
  userId: string;
  imageUrl: string;
  originalImageUrl?: string;

  category: "top" | "bottom" | "shoes" | "outerwear" | "dress" | "accessory" | "unknown";
  subcategory?: string; // tee, shirt, jeans, chinos, sneaker, blazer, etc.

  primaryColor?: string;
  secondaryColors?: string[];
  pattern?: "solid" | "striped" | "checked" | "floral" | "graphic" | "other";
  material?: string;
  fit?: "slim" | "regular" | "relaxed" | "oversized" | "unknown";

  styleTags: string[]; // minimal, streetwear, formal, casual, sporty, classic
  occasionTags: string[]; // work, brunch, date, travel, gym, wedding, casual
  seasonTags: string[]; // spring, summer, fall, winter, all-season

  formalityScore?: number; // 0 casual -> 1 formal
  warmthScore?: number; // 0 hot weather -> 1 cold weather
  colorConfidence?: number;
  tagConfidence?: number;

  createdAt: string;
  updatedAt: string;
};
```

### LookCard

```ts
type LookCard = {
  id: string;
  userId: string;

  title: string;
  subtitle?: string;
  section: "cover" | "daily" | "one_item_three_ways" | "underused" | "occasion";

  itemIds: string[];
  heroItemId?: string;

  occasion?: string;
  moodTags: string[];
  styleTags: string[];
  seasonTags: string[];

  whyItWorks: string;
  stylingTips: string[];
  swaps: Array<{
    replaceItemId: string;
    withItemId: string;
    reason: string;
  }>;

  score: number;
  scoreReasons: string[];

  generatedAt: string;
};
```

### LookFeedback

```ts
type LookFeedback = {
  id: string;
  userId: string;
  lookId: string;
  action: "love" | "save" | "not_my_style" | "too_formal" | "too_casual" | "wore_this" | "hide";
  createdAt: string;
};
```

---

## 11. Recommendation Pipeline

### Step 1: Analyze Wardrobe Items

Use a vision model to extract metadata from item photos.

Minimum tags:

- category,
- subcategory,
- color,
- pattern,
- formality,
- style tags,
- occasion tags,
- season tags.

### Step 2: Generate Candidate Looks

Start with deterministic rules:

- top + bottom + shoes,
- dress + shoes,
- optional outerwear,
- optional accessory.

Filter rules:

- avoid too many dominant patterns,
- avoid clashing formality extremes unless intentional,
- avoid season mismatch,
- require at least one neutral anchor if colors are loud,
- do not recommend incomplete looks unless labeled as incomplete.

### Step 3: Score Candidates

Initial scoring factors:

- category completeness,
- color harmony,
- occasion match,
- season/weather match,
- novelty,
- underused item boost,
- user feedback similarity,
- diversity from other cards in the feed.

### Step 4: Generate Editorial Copy

LLM receives structured candidate data and returns:

- title,
- subtitle,
- why it works,
- styling tips,
- occasion,
- swaps,
- warnings if needed.

### Step 5: Render Feed

Render a compact, high-quality editorial UI:

- large cover card,
- horizontal carousels,
- item thumbnails,
- concise copy,
- feedback buttons.

---

## 12. UX Direction

### Product Feel

Wardrub should feel like:

- a personal stylist,
- a fashion magazine,
- a smart closet,
- not a database grid.

### Example Feed Sections

#### Today’s Cover Look

The single strongest recommendation.

#### Three Fits From Your Closet

Three practical looks for today.

#### One Shirt, Three Ways

Select an uploaded item and style it in multiple contexts.

#### The Underused Edit

Looks built around clothes the user rarely wears.

#### Weekend / Work / Dinner Edits

Occasion-oriented sections.

### Example Look Card Copy

**The Clean Founder Uniform**  
White oxford + navy chinos + brown sneakers.

Why it works: crisp contrast, low visual noise, and enough polish for meetings without looking stiff.

Wear it for: work, coffee meetings, casual dinner.

Swap: add the navy overshirt if it gets cold.

---

## 13. Success Metrics

### Activation

- % users who upload at least 10 wardrobe items.
- % users who view first generated feed.
- Time from signup to first useful look.

### Engagement

- Feed opens per week.
- Look saves per user.
- Feedback actions per user.
- “I wore this” events.

### Quality

- Love/save rate per look.
- Hide/not-my-style rate.
- Repeat recommendation complaints.
- Manual tag correction rate.

### Retention

- D1/D7 return rate.
- Weekly active users who view feed.
- Number of users returning for daily outfit choice.

---

## 14. MVP Milestones

### Milestone 1: Spec + Data Model

- [ ] Review this PRD.
- [ ] Decide MVP scope.
- [ ] Confirm data model.
- [ ] Confirm where feed lives in navigation.

### Milestone 2: Wardrobe Metadata

- [ ] Add/confirm metadata fields for wardrobe items.
- [ ] Implement vision tagging service.
- [ ] Backfill tags for existing uploaded clothes.

### Milestone 3: Outfit Generator

- [ ] Build deterministic candidate generator.
- [ ] Build simple ranking function.
- [ ] Add section grouping.

### Milestone 4: Editorial Generator

- [ ] Create LLM prompt for look-card copy.
- [ ] Store generated cards.
- [ ] Add regeneration path.

### Milestone 5: Feed UI

- [ ] Create Magazine Feed page.
- [ ] Add card layouts.
- [ ] Add feedback actions.
- [ ] Add save/share hooks.

### Milestone 6: Feedback Loop

- [ ] Persist feedback.
- [ ] Use feedback in ranking.
- [ ] Add basic preference profile.

---

## 15. Open Decisions for Review

1. Should Magazine Feed become the **home screen**, or live as a separate tab?
2. Do we require at least 10 uploaded items before showing the feed?
3. Should v1 use LLM-generated looks live, or pre-generate/cache daily feed cards?
4. How opinionated should the copy be? Safe stylist vs witty Bud-style editorial voice?
5. Do we include chatbot in v1, or keep it as v1.5?
6. Should we prioritize existing wardrobe only, or include “complete the look” shopping suggestions early?
7. What is the minimum visual bar: garment collage, card thumbnails, or generated try-on?

---

## 16. Risks

### Risk: Bad Tags Create Bad Looks

Mitigation:

- confidence scores,
- manual correction,
- conservative rules,
- feedback loop.

### Risk: Feed Gets Repetitive With Few Clothes

Mitigation:

- show upload prompts,
- “one item three ways,”
- rotate themes,
- underused item sections,
- shopping gap suggestions later.

### Risk: Looks Feel Generic

Mitigation:

- style profile,
- strong editorial copy,
- personal feedback,
- occasion/weather context.

### Risk: Overbuilding Before Validation

Mitigation:

- ship non-VTON MVP first,
- validate save/love/wore-this rates,
- only then invest deeper into try-on integration.

---

## 17. Recommendation

Build this before making VTON the only product center.

The right product sequence:

1. **Wardrobe ingestion** — understand what the user owns.
2. **Magazine feed** — create daily value from owned clothes.
3. **Feedback/taste learning** — personalize recommendations.
4. **Try-on enhancement** — render selected looks when it matters.
5. **Chat/social/shopping** — expand once the core loop works.

The core loop should be:

> Upload clothes → get curated looks → give feedback → recommendations improve → return tomorrow.

That loop is strong enough to become the heart of Wardrub.
