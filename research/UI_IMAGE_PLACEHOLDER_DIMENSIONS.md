# UI Image Placeholder Dimensions

**Repo:** `Jarakeen/BFF`  
**Branch reviewed:** `phase13.5`  
**Purpose:** Record the dimensions and behavior of UI image boxes intended for boss/mechanic artwork that do not currently have an image source wired in.

## Summary

The current UI has two clearly intentional, unwired artwork surfaces relevant to boss and mechanic imagery.

| App area | Image box | Defined size | Runtime behavior | Source file |
|---|---|---:|---|---|
| Mechanics → Boss Guide | Boss Artwork | **280 × 170 px minimum** | Width and height may expand with the layout. This is not a fixed-size box. | `ui/mechanics_page.py` |
| Combat Reference | Mechanic / Attack Visual | **260 px minimum height** | No explicit width. It expands with the right-hand layout column. | `ui/reference_data_page.py` |

---

## Mechanics → Boss Guide

### Boss Artwork

The Boss Guide creates a `QLabel("BOSS ARTWORK")` and applies:

```python
artwork.setMinimumSize(280, 170)
```

### Dimensions

- **Minimum width:** 280 px
- **Minimum height:** 170 px
- **Minimum aspect ratio:** approximately **1.647:1**
- **Sizing behavior:** flexible; the layout may enlarge the image box beyond the minimum dimensions
- **Current image source:** none wired

### Suggested source-art resolutions

To preserve the current minimum aspect ratio while giving Qt enough image data for scaling and high-DPI displays:

| Source resolution | Scale |
|---|---:|
| 280 × 170 | 1× UI minimum |
| 560 × 340 | 2× |
| 840 × 510 | 3× |
| **1120 × 680** | **4× recommended source size** |

**Recommended boss-art source size:** `1120 × 680 px`.

This keeps the exact intended ratio while providing enough resolution for larger window layouts without creating unnecessarily huge source files.

---

## Combat Reference

### Mechanic / Attack Visual

The Combat Reference page creates a visual placeholder labeled:

> MECHANIC / ATTACK VISUAL

The placeholder is explicitly intended for artwork, icons, combat-log samples, or positioning diagrams and applies:

```python
visual.setMinimumHeight(260)
```

### Dimensions

- **Minimum height:** 260 px
- **Width:** dynamic
- **Fixed aspect ratio:** none
- **Sizing behavior:** width expands with the right-hand column of the page
- **Current image source:** none wired

Because only the minimum height is defined, there is no reliable static pixel width for this surface. Its width depends on the application window and layout allocation.

### Recommendation before building a mechanic-art library

Choose and enforce a standard aspect ratio for this image surface before creating a large mechanic-image library. Otherwise the same artwork may display at substantially different shapes depending on the application window size.

---

## Image-capable surfaces excluded from the unwired-placeholder inventory

The following UI surfaces were reviewed but excluded because they already have image-loading or image-source behavior.

### Mechanics → Raid Map

- Minimum preview height: **430 px**
- Source: `ui/mechanics_boss_map_support.py`
- Already loads saved raid-map images with `QPixmap`

### Encounters → Positioning Preview

- Minimum preview height: **300 px**
- Source: `ui/encounters_page.py`
- Already displays captured positioning images

### Build Screenshot Import

- Source: `ui/build_screenshot_import_support.py`
- Already loads selected screenshots into its preview surface

### Collectibles detail artwork

- Detail icon box: **112 × 112 px fixed**
- Source: `ui/collectibles_page.py`
- Already has an image-loading path

### Generic Foundry Hero Portrait

- Portrait box: **90 × 90 px fixed**
- Source: `ui/components/foundry_hero_panel.py`
- Already accepts a `QPixmap` through the `portrait` parameter and renders through `set_portrait()`

### Other excluded image/icon systems

Gear icons, scribing icons, ability icons, sidebar branding, card/header icons, splash artwork, and other semantic/theme assets already have functioning asset-resolution or image-loading paths and are not future-art placeholders.

---

## Styling note

Both unwired artwork placeholders currently use the same Qt styling property:

```python
bossArtworkPlaceholder = True
```

This is used by both:

- the Boss Artwork surface, and
- the Mechanic / Attack Visual surface.

Sharing the property is harmless for common visual styling, but the two surfaces currently have different sizing contracts. Before artwork sourcing becomes extensive, it would be useful to establish explicit image-box roles and standard aspect ratios so boss and mechanic artwork can be created once and render consistently across every supported theme.

---

## Current artwork-needed inventory

### Boss images

- UI minimum: **280 × 170 px**
- Recommended source artwork: **1120 × 680 px**
- Aspect ratio: **1.647:1**

### Mechanic / attack images

- UI minimum height: **260 px**
- Width: **dynamic / undefined in static UI code**
- Recommended next step: define a standard aspect ratio before mass-producing mechanic artwork
