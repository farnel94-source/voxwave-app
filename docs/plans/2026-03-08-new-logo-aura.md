# Plan: Nouveau logo SVG + aura canvas dans orb.html

## Approche choisie: A — SVG inline + canvas aura

## Fichiers a modifier
1. `src/gui/orb/orb.html` — fichier principal (SVG + canvas + adaptation JS)
2. `src/gui/icons.py` — adapter `_load_logo()` pour SVG→PNG (tray/taskbar)
3. `src/gui/orb/logo.svg` — nouveau fichier SVG du logo

## Taches

### T1: Creer le SVG du logo "The Wave" (5 min)
- Creer `src/gui/orb/logo.svg` avec le design ondes "VW"
- Design: 3 ondes stylisees formant un "W", couleur blanche/bleue
- Viewbox 100x100, optimise pour affichage 100px dans le widget

### T2: Remplacer le logo PNG par SVG inline dans orb.html (5 min)
- Remplacer `<img class="logo-icon" src="logo.png">` par SVG inline
- Garder les memes classes CSS (.logo-icon) et dimensions (100x100)
- Adapter les animations CSS (breathe, breathe-active, success-bounce)
  - `filter: drop-shadow()` fonctionne identiquement sur SVG inline
  - `object-fit: contain` → inutile sur SVG inline, retirer
- Garder les event listeners (contextmenu, drag)

### T3: Ajouter le canvas d'aura derriere le SVG (10 min)
- Ajouter `<canvas id="aura-canvas">` dans `.icon-area`, AVANT le SVG (z-index inferieur)
- Position: absolute, centre sur le logo, taille ~140x140 (depasse du logo pour l'aura)
- Gerer `devicePixelRatio` pour rendu HD:
  ```js
  const dpr = window.devicePixelRatio || 1;
  canvas.width = 140 * dpr;
  canvas.height = 140 * dpr;
  canvas.style.width = '140px';
  canvas.style.height = '140px';
  ctx.scale(dpr, dpr);
  ```

### T4: Implementer l'aura radial gradient reactive (10 min)
- Fonction `drawAura(amplitude)`:
  - `ctx.clearRect(0, 0, w, h)`
  - Gradient radial du centre vers l'exterieur
  - Couleur: bleu (#60A5FA) en recording, blanc subtil en idle
  - Rayon et opacite drives par amplitude (0.0 → 1.0)
  - Pulsation de base lente (sin) meme sans voix (coherent avec l'ancien ring)
- Connecter a `animateRing()` existant → renommer en `animateAura()`
- Remplacer la logique ring (border, boxShadow) par canvas draw

### T5: Gerer les etats idle/recording/processing/error sur le canvas (5 min)
- **Idle**: aura eteinte (canvas vide) OU glow blanc ultra-subtil → CPU zero si pas d'animation
  - `cancelAnimationFrame` + clear canvas quand idle
- **Recording**: aura bleue reactive a l'amplitude (requestAnimationFrame actif)
- **Processing**: aura figee faible OU eteinte (pas de RAF)
- **Error**: flash rouge sur l'aura (via CSS drop-shadow sur le SVG, comme avant)
- **Success flash**: garder la logique existante (classe .success sur le SVG)

### T6: Supprimer l'ancien anneau .ring (3 min)
- Retirer `<div class="ring" id="ring">` du HTML
- Retirer le CSS `.ring { ... }`
- Retirer les refs JS: `const ring = ...`, toute la logique ring dans animateRing
- Verifier que stopRingAnimation/startRingAnimation sont remplaces par les equivalents aura

### T7: Generer le nouveau logo.png pour tray/taskbar (5 min)
- Option A: Convertir le SVG en PNG via un script Python (cairosvg ou PIL)
- Option B: Garder logo.png actuel pour le tray (le SVG est uniquement dans orb.html)
- → **Choix: Option B** — le tray/taskbar garde logo.png actuel. Le SVG est pour l'orb uniquement.
  - `icons.py` ne change PAS
  - Pas de nouvelle dependance (cairosvg)
  - Le logo.png sera mis a jour manuellement plus tard si besoin

### T8: Test visuel de tous les etats (5 min)
- Lancer l'app sur Windows via le worktree
- Verifier: idle (respiration subtile), recording (aura reactive), processing (dots), error (shake+rouge), success flash (vert)
- Verifier le drag, click start/stop, right-click settings
- Verifier que le tray icon fonctionne toujours

## Comptage
- **N** = 8 taches
- **M** = 1 module (gui/orb principalement)
- **I** = 2 taches independantes max (T1 et T7)
- → **Pas d'Agent Teams** (M < 3, I < 3). Execution sequentielle.

## Ordre d'execution
T1 → T2 → T3 → T4 → T5 → T6 → T8 (T7 = skip, on garde logo.png)
