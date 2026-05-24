# UI Improvement Plan: Enhancing Responsiveness

The current frontend codebase uses React with custom CSS and Tailwind CSS. The layout has some basic responsive utilities (like `.page-container` and `.page-padding` in `index.css`), but the components themselves often lack explicit responsive design.

## Identified Issues
1. **Inconsistent Component Layouts:** Many components (e.g., `WardrobeGrid.jsx`, `TryOnScreen.jsx`) likely use fixed or mobile-first-only layouts that don't scale well to desktop.
2. **Missing Media Queries:** While there are some global responsive classes, individual components do not leverage them enough for conditional layout changes (e.g., grid columns, font sizes, spacing).
3. **Implicit Dependencies:** Components lack a clear strategy for managing responsiveness beyond basic media queries, leading to duplicated styles.

## Proposed Strategy
1. **Standardize Layouts:** Leverage Tailwind's responsive modifiers (`sm:`, `md:`, `lg:`) consistently within components to adapt to screen sizes.
2. **Modernize Styling:** Ensure all layouts follow a mobile-first approach, expanding functionality (like grid columns or sidebar navigation) only on larger screens.
3. **Component Refactoring:**
    *   **Grids:** Use `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` for listing views.
    *   **Containers:** Consistent use of `max-w-7xl` or similar for desktop layouts to prevent excessive stretching.
    *   **Navigation:** Transition `BottomNav.jsx` to a sidebar layout on desktop using `hidden md:flex`.
4. **Tooling:** Tailwind is already installed. Use its full power for responsive design rather than relying heavily on custom CSS classes in `index.css`.

## Concrete Steps
- [x] **Audit Components:** Review `WardrobeGrid`, `TryOnScreen`, `DressingRoom` for hardcoded widths and heights.
- [x] **Update Global Styles:** Refine `index.css` to act as a source of truth for design tokens (colors, spacings).
- [x] **Component-Level Responsive Updates:**
    - [x] `WardrobeGrid.jsx`: Implement dynamic grid columns.
    - [x] `DressingRoom.jsx`: Ensure image containers scale proportionally without fixed pixel heights.
    - [x] `BottomNav.jsx`: Add responsiveness to hide on desktop and replace with a sidebar.
- [x] **Test Responsive Breakpoints:** Verify functionality on a range of devices (mobile, tablet, desktop).

## Future Features / Ideas
- **Magazine-Style Feed (Chatbot UI):** Idea from Vanika to build a daily/weekly "magazine" feed showcasing different curated looks built purely from the clothes the user already owns in their virtual wardrobe. Consider a chatbot interface as the primary interaction model for browsing and generating these looks.
  - Product spec: `docs/PRD_MAGAZINE_FEED.md`
  - Product process: `docs/PRODUCT_DEVELOPMENT_PROCESS.md`
