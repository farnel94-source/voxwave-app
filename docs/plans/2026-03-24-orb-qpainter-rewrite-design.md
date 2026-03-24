# Design : Réécriture de l'orbe en QPainter natif

**Date** : 2026-03-24
**Statut** : Approuvé
**Problème** : PySide6 6.11+ (Chromium 134+) casse la transparence QWebEngineView sur Windows — rectangle semi-transparent visible autour de l'orbe.
**Solution** : Remplacer QWebEngineView (HTML/CSS/JS) par un QWidget natif avec QPainter.

---

## Contexte

L'orbe VoxWave est actuellement un QWebEngineView (300x116px) qui charge `orb.html` (600 lignes HTML/CSS/JS). Ce widget embarque un moteur Chromium complet (~130 MB) pour dessiner un cercle avec un logo et des animations.

PySide6 6.11 (requise par Python 3.14) embarque Chromium 134+ qui ne gère plus correctement le canal alpha des fenêtres transparentes. Aucun workaround (flags Chromium, DWM Win32, color key, setMask) ne résout le problème.

### Approches rejetées

| Approche | Raison du rejet |
|----------|----------------|
| `--disable-gpu-compositing` | N'a pas d'effet sur le rectangle |
| `--disable-direct-composition` | N'a pas d'effet |
| `--disable-gpu` | N'a pas d'effet |
| DWM `DwmSetWindowAttribute` | N'a pas d'effet |
| Win32 Color Key (`LWA_COLORKEY`) | Chromium rend sur sa propre surface GPU, le color key ne l'atteint pas |
| `setMask()` | N'a pas résolu le rectangle + bugs supplémentaires |
| Downgrade PySide6 6.8.3 | Transparence OK mais casse l'injection de texte (focus management différent) |
| QML/QtQuick | +80-120 MB au bundle, transparence non garantie sur 6.11, courbe d'apprentissage |
| QGraphicsView | Over-engineering massif pour 20 éléments |

### Devil's Advocate — recommandations intégrées

1. **30 FPS** (timer 33ms) au lieu de 60 FPS — l'aura est un glow flou, 30 FPS suffit, divise le CPU par 2
2. **QPixmap cache** pour les couches statiques — réduit le coût CPU de ~60%
3. PySide6 6.8.3 testé et rejeté (injection cassée) — réécriture nécessaire

---

## Architecture

### Fichier unique : `src/gui/orb_widget.py`

Remplace `waveform_widget.py` + `orb/orb.html`.

```
OrbWidget(QWidget)
│
│  # Rendu
├── paintEvent(QPaintEvent)       ← point d'entrée, dessine tout
│   ├── _paint_aura(QPainter)     ← 5 couches (shadow, outer, core, particles, edge)
│   ├── _paint_logo(QPainter)     ← cercle fond + SVG path "vw"
│   ├── _paint_timer(QPainter)    ← "01:23" pendant recording
│   ├── _paint_processing(QPainter) ← "Transcription..." + dots animés
│   └── _paint_error(QPainter)    ← "Erreur" rouge
│
│  # Interactions
├── mousePressEvent()             ← début drag ou clic
├── mouseMoveEvent()              ← drag (seuil 5px)
├── mouseReleaseEvent()           ← fin drag / start / stop
├── contextMenuEvent()            ← right-click → settings
│
│  # Animation
├── _animation_tick()             ← QTimer 33ms (30 FPS) → update()
├── _amplitude_tick()             ← QTimer 50ms → lit amplitude micro
│
│  # Cache
├── _build_static_cache()         ← pré-rend shadow + edge ring dans QPixmap
└── _invalidate_cache()           ← appelé si DPI change
```

### Ce qui disparaît

- `QWebEngineView`, `QWebChannel`, `Bridge` (class)
- `src/gui/orb/orb.html` (600 lignes)
- Dépendance `PySide6-Addons` (~130 MB, contient WebEngine)

### Ce qui reste identique

- API publique : `show_recording()`, `show_processing()`, `show_idle()`, `show_error()`, `set_error_text()`, `update_step()`, `show_preview()`
- Signals thread-safe : `sig_show_recording`, `sig_show_processing`, etc.
- `ensure_topmost()` Win32
- `_restore_foreground_window()`
- `app.py` change seulement l'import

---

## États visuels

| État | Cercle logo | Aura | Zone expand | Animation |
|------|------------|------|-------------|-----------|
| idle | 44px, bg rgba(15,23,42,0.6), border slate 0.3 | respiration sin(t) | cachée (width 0) | breathe 3.5s |
| recording | idem + border bleu 0.5 | réactive amplitude | timer MM:SS visible | breathe 1.8s |
| processing | idem | off | "Transcription..." + 3 dots | dot-bounce 1.4s |
| error | idem + glow rouge | off | "Erreur" #F87171 | shake 0.45s |
| success (transition) | glow vert + bounce | off | — | bounce 0.5s → idle |

---

## Système d'aura (5 couches)

### Couches statiques (QPixmap cache)

Pré-rendues dans `_build_static_cache()` au démarrage et quand le DPI change.

**Couche 0 — Shadow layer**
- QRadialGradient du centre vers rayon 42px
- Stops : rgba(0,0,0, 0.10) → rgba(0,0,0, 0.05) à 60% → rgba(0,0,0, 0) à 100%
- Dessinée dans un QPixmap 90x90 (× DPR), clippée en cercle

**Couche 4 — Edge ring**
- QPen rgba(0,0,0, 0.15), width 1.5px
- Arc de cercle à rayon variable (outer aura radius - 1)
- Note : le rayon varie avec l'amplitude → en réalité semi-dynamique
- Optimisation : pré-rendre pour amplitude=0, recalculer en recording

### Couches dynamiques (30 FPS)

Recalculées à chaque `_animation_tick()`.

**Couche 1 — Outer aura**
- QRadialGradient, rayon = CORE_BASE_RADIUS + 20 + breathe×6 + intensity×30
- Stops : indigo rgba(99,102,241) → bleu rgba(59,130,246) → transparent
- Opacités dynamiques basées sur `intensity` (amplitude lissée)

**Couche 2 — Core glow**
- QRadialGradient du centre, rayon = CORE_BASE_RADIUS + intensity×35
- Stops : cyan rgba(34,211,238) → bleu rgba(59,130,246) → transparent
- Opacités dynamiques

**Couche 3 — 15 particules**
- Position : angle = (i/15)×2π + time×0.5 + i×132.5°
- Distance : CORE_BASE_RADIUS + sin(time×3 + i×54)×6 + intensity×40
- Taille : 1.5 + intensity×1.5 px
- Couleur : rgba(147, 197, 253, opacité_dynamique)
- Dessinées avec `QPainter.drawEllipse()`

### Pipeline de rendu aura

1. Créer QPixmap temporaire 90×90 (× DPR)
2. Remplir transparent
3. Clip en cercle (QPainterPath)
4. Dessiner couche 0 (depuis cache) avec opacité dynamique
5. Dessiner couches 1-3 (dynamiques)
6. Dessiner couche 4 (edge ring)
7. `drawPixmap()` centré sur le logo dans le widget principal

---

## Logo

### Cercle fond
- 44×44px, `drawEllipse()`
- Background : QBrush rgba(15, 23, 42, 0.6)
- Border : QPen rgba(148, 163, 184, 0.3), width 1px
- Border recording : rgba(59, 130, 246, 0.5)
- Border error : rgba(239, 68, 68, 0.5)

### SVG path "vw"
- QPainterPath avec 6 cubicTo() :
  ```
  M(20,45) C(22,45 26,60 32,60) C(38,60 38,40 42,40)
  C(46,40 46,58 50,58) C(54,58 54,40 58,40)
  C(62,40 62,58 66,58) C(70,58 74,42 80,42)
  ```
- Échelle : viewBox 100×100 → 28×28px (factor 0.28)
- Stroke : QLinearGradient blanc→gris (rgba(255,255,255,0.9) → rgba(200,200,210,0.7))
- QPen width : 3.5 × 0.28 ≈ 1.0px
- Stroke linecap/linejoin : round
- RenderHint : Antialiasing activé

### Glow (drop-shadow)
Simulé avec `drawEllipse()` flou derrière le cercle :
- Idle : blanc rgba(255,255,255, 0.1-0.2), rayon +2-4px
- Recording : blanc rgba(255,255,255, 0.2-0.4), rayon +3-6px
- Success : vert rgba(74,222,128, 0.8-1.0), rayon +6px
- Error : rouge rgba(239,68,68, 0.7-0.9), rayon +4px

---

## Animations

Toutes pilotées par `_animation_tick()` (QTimer 33ms = 30 FPS).
Temps : `time.monotonic()` converti en secondes.

| Animation | Formule | Durée |
|-----------|---------|-------|
| breathe idle | `sin(t × 2π/3.5) × 0.5 + 0.5` | 3.5s cycle |
| breathe recording | `sin(t × 2π/1.8) × 0.5 + 0.5` | 1.8s cycle |
| success bounce | `scale = interp(t, [0, 0.2, 0.35, 0.5], [1, 1.06, 0.98, 1])` | 0.5s once |
| shake error | `dx = interp(t, [...], [0,-3,3,-2,2,-1,1,0])` | 0.45s once |
| dot bounce | `dy = -4 × max(0, sin(π × phase))` par dot (décalage 0.14s) | 1.4s cycle |
| amplitude smooth | `amplitude += (target - amplitude) × 0.12` | continu |

---

## Texte

Tous rendus avec `QPainter.drawText()` + font Segoe UI.

| Élément | Taille | Couleur | Alignement |
|---------|--------|---------|------------|
| Timer | 12px, tabular | rgba(255,255,255, 0.75) | centre, 42px width |
| Processing | 12px | rgba(255,255,255, 0.45) | gauche |
| Dots | 3px circles | rgba(255,255,255, 0.7) | inline après texte |
| Error | 12px, bold | #F87171 | gauche |

---

## Interactions souris

| Action | Événement | Seuil | Résultat |
|--------|-----------|-------|----------|
| Clic gauche (idle) | mouseRelease, dist < 5px | 5px | `on_start()` |
| Clic gauche (recording) | mouseRelease, dist < 5px | 5px | `on_stop()` |
| Drag | mouseMove, dist ≥ 5px | 5px | `self.move(pos + delta)` |
| Clic droit | contextMenuEvent | — | `on_settings()` |

`_restore_foreground_window()` appelé avant start/stop (identique à l'actuel).

---

## Gestion DPI

- `devicePixelRatioF()` lu dans `_build_static_cache()`
- `moveEvent()` compare le DPR actuel vs celui du cache → `_invalidate_cache()` si différent
- QPixmap créés avec le bon DPR : `pixmap.setDevicePixelRatio(dpr)`
- `QPainter.setRenderHint(Antialiasing | SmoothPixmapTransform)`

---

## Migration

1. Créer branche `feat/orb-qpainter`
2. Créer `src/gui/orb_widget.py` avec la même API publique
3. Modifier `app.py` : `from src.gui.orb_widget import OrbWidget` (au lieu de WaveformWidget)
4. Tester sur Windows
5. Supprimer `src/gui/waveform_widget.py` + `src/gui/orb/orb.html`
6. Remplacer `PySide6>=6.6.0` par `PySide6-Essentials>=6.6.0` dans requirements.txt (supprime WebEngine)
7. Mettre à jour `voxwave.spec` (supprimer les datas orb.html, ajouter hiddenimports si nécessaire)

---

## Gains attendus

| Métrique | Avant (QWebEngineView) | Après (QPainter) |
|----------|----------------------|-----------------|
| Taille .exe | ~210 MB | ~80-100 MB |
| RAM idle | ~150 MB | ~30 MB |
| Démarrage | 2-3s (init Chromium) | <0.5s |
| Transparence | Cassée sur PySide6 6.11+ | Toujours OK |
| Fichiers | waveform_widget.py + orb.html | orb_widget.py seul |
| Dépendances | PySide6 + PySide6-Addons | PySide6-Essentials seul |
