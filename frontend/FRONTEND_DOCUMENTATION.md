# Wardrub Frontend Documentation

## Overview

**Wardrub** is an AI-powered virtual wardrobe assistant that helps users manage their clothing, create virtual avatars, try on outfits digitally, and get personalized daily outfit recommendations based on weather and personal style analysis.

### Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.2.0 | UI Framework |
| Vite | 7.2.4 | Build Tool & Dev Server |
| Tailwind CSS | 4.1.18 | Styling |
| React Router DOM | 7.12.0 | Client-side Routing |
| Firebase | 10.14.0 | Authentication |
| Lucide React | 0.562.0 | Icons |

---

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx                 # Main app with routing
│   ├── main.jsx                # Entry point
│   ├── index.css               # Global styles & CSS variables
│   ├── config/
│   │   └── firebase.js         # Firebase configuration
│   ├── context/
│   │   ├── AuthContext.jsx     # Authentication state management
│   │   └── WardrobeContext.jsx # Wardrobe data & API integration
│   ├── pages/
│   │   ├── Login.jsx           # Google Sign-in
│   │   ├── Home.jsx            # Wardrobe management
│   │   ├── Capture.jsx         # Add clothes (photo/upload)
│   │   ├── DressingRoom.jsx    # Virtual try-on
│   │   ├── CreateAvatar.jsx    # Avatar creation
│   │   ├── DailyOutfit.jsx     # AI outfit recommendations
│   │   ├── Profile.jsx         # User profile & style analysis
│   │   └── SavedLooks.jsx      # Saved outfit gallery
│   └── components/
│       ├── BottomNav.jsx       # Navigation bar
│       ├── LoadingOverlay.jsx  # Full-screen loading state
│       ├── GarmentPreview.jsx  # Garment detail modal
│       ├── LookPreview.jsx     # Saved look detail modal
│       ├── AvatarPreview.jsx   # Avatar detail modal
│       ├── WardrobeGrid.jsx    # Garment grid display
│       ├── TryOnScreen.jsx     # Try-on interface component
│       ├── QualityFeedback.jsx # Image quality indicators
│       └── Camera.jsx          # Camera capture wrapper
├── vite.config.js              # Vite configuration
├── package.json                # Dependencies
└── index.html                  # HTML template
```

---

## Architecture

### Application Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        App.jsx                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    AuthProvider                              ││
│  │  ┌───────────────────────────────────────────────────────┐  ││
│  │  │                    AppRoutes                           │  ││
│  │  │                                                        │  ││
│  │  │   /login ──────────────────────► Login.jsx             │  ││
│  │  │                                                        │  ││
│  │  │   ┌──────────── ProtectedLayout ─────────────┐        │  ││
│  │  │   │  ┌────────────────────────────────────┐  │        │  ││
│  │  │   │  │         WardrobeProvider           │  │        │  ││
│  │  │   │  │                                    │  │        │  ││
│  │  │   │  │  / ──────────────► DailyOutfit     │  │        │  ││
│  │  │   │  │  /wardrobe ──────► Home            │  │        │  ││
│  │  │   │  │  /capture ───────► Capture         │  │        │  ││
│  │  │   │  │  /dressing-room ─► DressingRoom    │  │        │  ││
│  │  │   │  │  /create-avatar ─► CreateAvatar    │  │        │  ││
│  │  │   │  │  /profile ───────► Profile         │  │        │  ││
│  │  │   │  │  /looks ─────────► SavedLooks      │  │        │  ││
│  │  │   │  └────────────────────────────────────┘  │        │  ││
│  │  │   └──────────────────────────────────────────┘        │  ││
│  │  └───────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### State Management

The app uses React Context for global state:

#### AuthContext
Manages Firebase authentication state:
- `user` - Current Firebase user object
- `loading` - Auth state loading indicator
- `signInWithGoogle()` - Google OAuth sign-in
- `signOut()` - Sign out user
- `getIdToken()` - Get Firebase ID token for API calls

#### WardrobeContext
Manages wardrobe data and API interactions:
- **State**: `avatarUrl`, `garments`, `looks`, `userProfile`, `isLoading`, `loadingMessage`, `error`
- **Caching**: 5-minute TTL cache to prevent redundant API calls
- **API Methods**: See [API Integration](#api-integration) section

---

## Pages

### 1. Login (`/login`)

**Purpose**: Google OAuth authentication entry point

**Features**:
- Google Sign-in with popup
- Auto-redirect if already authenticated
- Beautiful animated background with blurred shapes
- Feature highlights list

**Key Components**: Firebase `signInWithPopup`

---

### 2. Daily Outfit (`/` or `/daily-outfit`)

**Purpose**: AI-generated outfit recommendations for the day

**Features**:
- Weather forecast display (4 time periods: Morning, Noon, Evening, Night)
- Multiple outfit suggestions with navigation
- Match score percentage
- Styling tips, color harmony notes, and style notes
- "Play around" button to customize in Dressing Room
- Manual regeneration of daily looks

**Data Flow**:
```
fetchDailyLooks() → /api/daily-looks/latest
fetchDayForecast() → /api/weather/forecast
handleRegenerate() → /api/daily-looks/generate?force=true
```

---

### 3. Wardrobe / Home (`/wardrobe`)

**Purpose**: View and manage clothing collection

**Features**:
- Category filter tabs (All, Tops, Bottoms, Dresses, Outerwear)
- Grid view of garments
- Long-press to enter delete mode
- Tap garment to view details (front/back views)
- Quick add button

**Interactions**:
- Category filter → `fetchGarments(category)`
- Long press (500ms) → Delete mode
- Tap garment → `GarmentPreview` modal

---

### 4. Capture (`/capture`)

**Purpose**: Add new clothes to wardrobe

**Two Input Modes**:

1. **Upload Photo** - AI auto-detection
   - Upload any image containing clothes
   - Gemini AI detects and extracts clothing items
   - Creates ghost mannequin versions automatically

2. **Take Photo** - Manual capture
   - Select category first (Top, Bottom, Dress, Outerwear)
   - Capture front view (required)
   - Optionally capture back view
   - Toggle AI ghost mannequin processing

**Visual Guides**: SVG garment outlines help users frame their photos correctly

**API Calls**:
- Upload mode: `processUploadedClothes(file)` → `/api/process-uploaded-clothes`
- Capture mode: `processGarment(front, back, category, ghostMannequin)` → `/api/process-garment`

---

### 5. Dressing Room (`/dressing-room`)

**Purpose**: Virtual try-on with multiple garments

**Features**:
- Avatar preview panel
- Category-organized garment carousels
- Multi-select with smart mutual exclusivity:
  - Dress excludes Top + Bottom
  - Top/Bottom excludes Dress
  - Outerwear can combine with anything
- Selection summary with remove buttons
- Try-on result modal with Save/Download/Share

**Preselection**: Supports `preselectedGarmentIds` via navigation state (from Daily Outfit)

**API Call**: `tryOnMultiple(garments)` → `/api/try-on-multiple`

---

### 6. Create Avatar (`/create-avatar`)

**Purpose**: Create or update virtual avatar

**Two Modes**:

1. **Upload Photo** - Full body photo
   - Best results with visible head-to-toe
   - Plain background recommended

2. **Take Selfie** - Face only
   - Your face applied to default avatar body
   - Quicker setup option

**Tips Section**: Context-aware tips based on selected mode

**API Call**: `createAvatar(files, mode)` → `/api/create-avatar`

---

### 7. Profile (`/profile`)

**Purpose**: User profile, style analysis, and recommendations

**Sections**:

1. **Profile Card**
   - Avatar with edit overlay
   - Season/undertone/body type display
   - Analyze Style button (upload photos)
   - Update Location button

2. **Color Recommendations** (if analyzed)
   - Best colors with swatches
   - Colors to avoid with visual strike-through

3. **Body Type & Fit** (if analyzed)
   - Body silhouette visualization
   - Recommended fits for tops and bottoms

**Location Options**: 
- Popular cities (London, New York, Paris, Tokyo, Sydney)
- Use current geolocation

**API Calls**:
- `fetchProfile()` → `/api/profile`
- `analyzeProfile(files)` → `/api/profile/analyze`
- `handleLocationSelect()` → `/api/profile/location`
- Color recommendations → `/api/profile/color-recommendations`
- Fit recommendations → `/api/profile/fit-recommendations`

---

### 8. Saved Looks (`/looks`)

**Purpose**: Gallery of saved try-on results

**Features**:
- Grid of saved looks
- Long-press delete mode
- Tap to view full-size with options
- Download and share functionality

**API Calls**:
- `fetchLooks()` → `/api/try-on/history`
- `deleteLook(id)` → `/api/look/{id}` (DELETE)

---

## Components

### BottomNav
Fixed bottom navigation with 4 tabs:
- Wardrobe (`/wardrobe`)
- Daily (`/`)
- Try On (`/dressing-room`)
- Looks (`/looks`)

Active state indicated by terracotta color highlight.

### LoadingOverlay
Full-screen loading state with:
- Animated spinner rings
- Dynamic loading message
- Progress dots animation
- Warning text about wait time

### GarmentPreview
Modal for garment details:
- Front/back view toggle (if available)
- Category badge
- Navigation arrows and flip button
- Delete confirmation flow

### LookPreview
Modal for saved looks:
- Full image display
- Download button
- Share button (Web Share API / clipboard fallback)
- Delete with confirmation

### AvatarPreview
Modal for avatar management:
- Full avatar display
- Update avatar button → navigates to CreateAvatar
- Delete avatar with confirmation

### WardrobeGrid
Reusable grid for displaying garments:
- Staggered fade-in animation
- Category badges
- Delete mode overlay
- Selection ring for selected items

### TryOnScreen
Embeddable try-on interface:
- Avatar display with selection summary
- Category carousels
- Multi-select logic with mutual exclusivity
- Try-on button

### QualityFeedback
Image quality feedback component:
- Visibility score progress bar
- Color-coded status (green/amber/red)
- "Add More Photos" prompt
- Also exports `VisibilityBadge` and `RecommendationBadge`

### Camera
Wrapper component for camera capture:
- Hidden file input with `capture="environment"`
- Imperative `trigger()` method via ref

---

## API Integration

### Backend Proxy
Vite dev server proxies `/api/*` to `http://localhost:8000`:

```javascript
// vite.config.js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

### Authentication
All API calls include Firebase ID token:
```javascript
const authFetch = async (url, options = {}) => {
  const token = await getIdToken()
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    }
  })
}
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/avatar` | GET | Fetch user avatar |
| `/api/avatar` | DELETE | Delete user avatar |
| `/api/wardrobe` | GET | Fetch garments (optional `?category=`) |
| `/api/garment/{id}` | DELETE | Delete garment |
| `/api/process-garment` | POST | Process captured garment |
| `/api/process-uploaded-clothes` | POST | AI-detect clothes in image |
| `/api/create-avatar` | POST | Create avatar from photo |
| `/api/try-on` | POST | Single garment try-on |
| `/api/try-on-multiple` | POST | Multi-garment try-on |
| `/api/try-on/history` | GET | Fetch saved looks |
| `/api/look/{id}` | DELETE | Delete saved look |
| `/api/profile` | GET | Fetch user profile |
| `/api/profile/analyze` | POST | Analyze style from photos |
| `/api/profile/location` | PUT | Update user location |
| `/api/profile/color-recommendations` | GET | Get color recommendations |
| `/api/profile/fit-recommendations` | GET | Get fit recommendations |
| `/api/daily-looks/latest` | GET | Fetch today's outfit suggestions |
| `/api/daily-looks/generate` | POST | Manually regenerate looks |
| `/api/weather/forecast` | GET | Get day weather forecast |

---

## Styling System

### CSS Variables (Design Tokens)

```css
:root {
  /* Color Palette */
  --color-cream: #F5F0E8;      /* Background */
  --color-charcoal: #1A1A1A;   /* Primary text */
  --color-warm-gray: #8B8680;  /* Secondary text */
  --color-terracotta: #C4704B; /* Accent/CTA */
  --color-sage: #7A8B6E;       /* Secondary accent */
  --color-blush: #D4A5A5;      /* Tertiary accent */
  
  /* Glass Effect */
  --glass-bg: rgba(245, 240, 232, 0.7);
  --glass-border: rgba(138, 134, 128, 0.2);
}
```

### Typography

- **Headings**: Syne (font-weight: 600)
- **Body**: DM Sans

### Animations

| Class | Effect |
|-------|--------|
| `.animate-shimmer` | Loading skeleton shimmer |
| `.animate-fade-in` | Fade in with slight translate up |
| `.animate-pulse-soft` | Subtle opacity pulse |
| `.animate-float` | Gentle vertical float |
| `.animate-scale-up` | Scale from 90% to 100% |
| `.stagger-1` to `.stagger-5` | Animation delays (0.1s increments) |

### Utility Classes

| Class | Purpose |
|-------|---------|
| `.safe-top` | Safe area padding for notched phones |
| `.safe-bottom` | Safe area bottom padding |
| `.nav-bottom-spacing` | Clear fixed bottom nav (100px + safe area) |
| `.scroll-pb-nav` | Scroll padding for nav clearance |
| `.page-container` | Responsive max-width container |
| `.page-padding` | Responsive horizontal padding |

---

## Configuration

### Environment Variables

Create `.env` file in frontend root:

```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_API_URL=                   # Optional: defaults to '' (same origin)
```

### Vite Configuration

```javascript
// vite.config.js
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    host: true,
    allowedHosts: ['localhost', '.ngrok-free.dev', '.ngrok.io'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

---

## Development

### Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

### Development Server

- **URL**: http://localhost:5174
- **API Proxy**: All `/api/*` requests forwarded to backend at port 8000

### Mobile Testing

The server is configured with `host: true` and allows ngrok hosts for mobile testing:

```bash
# Expose to internet via ngrok
ngrok http 5174
```

---

## Mobile/PWA Considerations

### Safe Areas
The app handles notched phone displays with safe area utilities:
- Status bar: `.safe-top`
- Home indicator: `.safe-bottom`
- Bottom nav clearance: `.nav-bottom-spacing`

### Touch Interactions
- Tap highlight disabled globally
- Long-press (500ms) for delete modes
- Touch-scroll with momentum (`-webkit-overflow-scrolling: touch`)

### Viewport
```css
html {
  height: -webkit-fill-available;  /* iOS Safari PWA fix */
}
```

---

## Error Handling

### Error Display
Errors show as dismissible toast notifications:
- Tap to dismiss
- Auto-styled with terracotta background
- Positioned at top of screen

### Loading States
- Full-screen `LoadingOverlay` for long operations
- Skeleton loaders for initial data fetch
- Button disabled states during submission

---

## Data Flow Diagrams

### Garment Processing Flow
```
User selects input mode
         │
    ┌────┴────┐
    ▼         ▼
 Upload    Capture
    │         │
    │    Select category
    │         │
    │    Take front photo
    │         │
    │    (Optional) Take back
    │         │
    └────┬────┘
         │
   Submit to API
         │
    Processing...
    (10-30 seconds)
         │
    Garment added
    to wardrobe
         │
    Navigate to Home
```

### Try-On Flow
```
Enter Dressing Room
         │
   Fetch garments
         │
   Select garments
   (multi-select with
    mutual exclusivity)
         │
   Click "Try On"
         │
   API processes
   combination
         │
   Show result modal
         │
  ┌──────┼──────┐
  ▼      ▼      ▼
Save  Download  Share
```

---

## Best Practices

### Code Conventions
- Functional components with hooks
- Context for global state
- `useCallback` for memoized functions passed to children
- `useMemo` for expensive computations
- Proper cleanup in `useEffect`

### Performance
- Image lazy loading with `loading="lazy"`
- 5-minute cache TTL for API responses
- Skeleton loaders instead of spinners for content

### Accessibility
- Semantic HTML elements
- Alt text on images
- Touch targets minimum 44px
- Color contrast compliance with design system

---

## Future Improvements

Potential areas for enhancement:
1. Offline support with service workers
2. Image compression before upload
3. Skeleton components for individual items
4. Gesture-based navigation
5. Dark mode support
6. Internationalization (i18n)
7. Unit and integration tests

---

## Support

For backend API documentation, see the backend README.

For image processing service documentation, see the image-edit-service README.
