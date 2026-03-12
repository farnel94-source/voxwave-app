# Design Doc — Landing Page VoxWave

**Date** : 2026-03-12
**Approche choisie** : A — Single Page Premium (Next.js + Tailwind + Framer Motion)
**Inspirations** : Wispr Flow, Linear, Vercel

---

## Contexte

VoxWave a besoin d'une vitrine web pour son lancement. Le produit est techniquement prêt (note 8.2/10), mais sans landing page = impossible de distribuer.

### Décisions stratégiques
- **Gratuit au lancement** — pas de pricing affiché, juste "Télécharger gratuitement"
- **Open source** : version locale (Whisper) sur GitHub, version complète (cloud) = l'app VoxWave
- **$5/mois prévu dans ~2 mois** après feedback users
- **API payées par Farnel** au lancement (Groq, OpenAI)
- **Hébergement** : Vercel (gratuit), domaine custom plus tard

---

## Stack technique

- **Framework** : Next.js 15 (App Router)
- **Styling** : Tailwind CSS 4
- **Animations** : Framer Motion
- **Déploiement** : Vercel
- **Typo** : Inter (Google Fonts) ou Geist Sans (Vercel)

---

## Design system

### Couleurs
| Token | Valeur | Usage |
|-------|--------|-------|
| `bg-primary` | `#0A0A0A` | Fond principal |
| `bg-secondary` | `#111111` | Cartes, sections alternées |
| `bg-card` | `#1A1A1A` | Cards features |
| `text-primary` | `#FFFFFF` | Titres, texte important |
| `text-secondary` | `#A1A1AA` | Descriptions, sous-titres |
| `text-tertiary` | `#71717A` | Labels, metadata |
| `accent-start` | `#6366F1` | Gradient début (indigo) |
| `accent-end` | `#8B5CF6` | Gradient fin (violet) |
| `border` | `#27272A` | Bordures cartes |

### Typographie
- **Titres** : Inter, 600-700 weight, letter-spacing -0.02em
- **Corps** : Inter, 400 weight, line-height 1.6
- **Hiérarchie** : H1 (56-72px) → H2 (36-48px) → H3 (24-30px) → Body (16-18px)
- **Anti-aliasing** : `-webkit-font-smoothing: antialiased`

### Animations (Framer Motion)
- **Fade-in au scroll** : `whileInView`, opacity 0→1, y 20→0, duration 0.6s
- **Stagger** : 0.1s entre chaque élément d'un groupe
- **Hero animation** : custom timeline (voir section Hero)
- **Pas de surcharge** : animations subtiles, jamais distrayantes

---

## Sections de la page

### 1. Navbar (fixe)
```
[Logo VoxWave]     Features   Open Source   Télécharger     [CTA: Télécharger ↓]
```
- Position fixed, `backdrop-filter: blur(12px)`, bg semi-transparent
- CTA bouton accent gradient à droite
- Liens = ancres smooth scroll
- Mobile : hamburger menu

### 2. Hero
**Titre** : "Parle. VoxWave écrit."
**Sous-titre** : "Dictée vocale intelligente pour Windows & Linux. Gratuit."
**CTA** : [Télécharger gratuitement] + [Voir en action ↓]
**Badges** : icônes Windows + Linux

**Animation hero (boucle 8s)** :
1. (0-3s) Waveform animée (barres CSS qui bougent, style orb)
2. (3-5s) Texte brut s'écrit lettre par lettre :
   *"euh donc en fait j'aimerais euh réserver une table pour ce soir"*
3. (5-5.5s) Pause
4. (5.5-6.5s) Fillers "euh", "donc", "en fait" se barrent (strikethrough + fade)
5. (6.5-7s) Texte final apparaît : *"J'aimerais réserver une table pour ce soir."*
6. (7-8s) Pause → reset → loop

### 3. Bandeau apps compatibles
Défilement horizontal continu (CSS marquee ou Framer Motion).
Icônes : VS Code, Chrome, Word, Slack, Terminal, Discord, Notion, LibreOffice, Telegram, etc.
Titre : *"Fonctionne dans toutes vos applications"*

### 4. Features (4 cartes)
Layout : grille 2x2 desktop, stack mobile.
Cards avec fond `bg-card`, bordure `border`, hover glow subtil.

| Icône | Titre | Description |
|-------|-------|-------------|
| ⚡ | **< 1 seconde** | Le texte apparaît instantanément. Le nettoyage se fait en arrière-plan. |
| 🧠 | **S'adapte au contexte** | Détecte VS Code, Terminal, Word... et ajuste le nettoyage automatiquement. Mode brut disponible. |
| 🌐 | **Cloud + Hors-ligne** | Fonctionne en ligne (rapide) et hors-ligne (privé). Bascule automatique si la connexion tombe. |
| 🧹 | **Nettoyage IA** | Supprime les "euh", corrige la ponctuation, garde votre style naturel. |

### 5. Section "S'adapte au contexte" (showcase)
Section dédiée à la feature killer — détection automatique de l'environnement.

**Animation** : même input vocal, 3 résultats différents selon l'app.
```
Input vocal : "crée une fonction qui prend un nombre et retourne vrai si c'est premier"

[VS Code]  →  def is_prime(n): ...        (code, pas de nettoyage LLM)
[Word]     →  Créez une fonction qui...    (professionnel, ponctuation)
[Slack]    →  crée une fonction qui...     (naturel, casual)
```
Animation : switch automatique entre les 3 apps toutes les 3 secondes, avec transition fade.

### 6. Comment ça marche (3 étapes)
Layout horizontal avec ligne connectrice (style Linear).
Chaque étape fade-in stagger au scroll.

```
  [1]────────────[2]────────────[3]
  Configurez      Parlez        Texte collé
  votre                         automatiquement
  raccourci
```

### 7. Open Source
Section crédibilité + différenciation.

**Titre** : "Open Source au coeur"
**Texte** : "La version locale de VoxWave est gratuite et open source sur GitHub. VoxWave App ajoute le cloud IA, le nettoyage LLM et les mises à jour automatiques."
**CTA** : [Voir sur GitHub ⭐]

Layout : texte à gauche, terminal/code mockup à droite montrant `git clone`.

### 8. Tableau comparatif
Tableau minimaliste dark, lignes alternées.

| | VoxWave | Wispr Flow | Dragon | OS Built-in |
|--|---------|------------|--------|-------------|
| Prix | **Gratuit** | $12/mois | $699 | Gratuit |
| Windows + Linux | ✅ | ❌ Win seul | ✅ | ✅ |
| Mode hors-ligne | ✅ | ❌ | ✅ | ❌ |
| Nettoyage IA | ✅ | ✅ | ❌ | ❌ |
| Injection < 1s | ✅ | ✅ | ❌ | ❌ |
| Adaptatif par app | ✅ | ❌ | ❌ | ❌ |

### 9. CTA final
Grand titre centré + bouton accent.

**Titre** : "Arrêtez de taper. Commencez à parler."
**CTA** : [Télécharger gratuitement — Windows & Linux]

Fond : gradient subtil radial (accent très dilué).

### 10. Footer
Minimaliste, une seule ligne.

```
[Logo VoxWave]     GitHub    Contact    Mentions légales     Made with 🎙️
```

---

## Responsive

| Breakpoint | Comportement |
|------------|-------------|
| **Desktop** (1280px+) | Layout complet, grille 2x2, tableau horizontal |
| **Tablet** (768-1279px) | Grille 1 colonne, tableau scrollable |
| **Mobile** (<768px) | Stack vertical, navbar hamburger, CTA plein écran |

---

## Structure fichiers (Next.js)

```
landing/
├── app/
│   ├── layout.tsx          # Layout racine (fonts, metadata, dark bg)
│   ├── page.tsx            # Page principale (compose les sections)
│   └── globals.css         # Tailwind + custom CSS (animations keyframes)
├── components/
│   ├── navbar.tsx
│   ├── hero.tsx            # + animation workflow
│   ├── app-marquee.tsx     # Bandeau apps défilant
│   ├── features.tsx        # 4 cartes
│   ├── context-showcase.tsx # Section "S'adapte au contexte"
│   ├── how-it-works.tsx    # 3 étapes
│   ├── open-source.tsx
│   ├── comparison.tsx      # Tableau comparatif
│   ├── cta-final.tsx
│   └── footer.tsx
├── public/
│   ├── logo.svg
│   └── icons/              # Icônes apps (vscode, chrome, etc.)
├── tailwind.config.ts
├── package.json
└── next.config.ts
```

---

## Approches rejetées (Devil's Advocate)

### Approche B : Multi-pages + Docs
**Rejetée car** : over-engineering pour 0 users. Pas de contenu docs à écrire avant d'avoir du feedback. Scope creep garanti.

### Approche C : Template adapté
**Rejetée car** : paradoxe de personnalisation — adapter un template SaaS générique à VoxWave (open source + gratuit + desktop) demande autant de travail que from scratch, dans du code étranger.

### Approche D : HTML statique + Tailwind CDN (proposée par Devil's Advocate)
**Rejetée car** : c'est Claude qui code, pas Farnel. La courbe d'apprentissage React n'est pas un problème. Le résultat Next.js + Framer Motion sera plus premium et plus maintenable à long terme.

---

## Risques identifiés

| Risque | Mitigation |
|--------|-----------|
| Framer Motion trop lourd (150KB) | Lazy load animations, code split |
| Animation hero complexe | Fallback statique si JS désactivé |
| SEO (SPA JS-heavy) | Next.js SSR par défaut, metadata statique |
| Vercel free tier limité | Landing page statique = très peu de bandwidth |
| Pas de vidéo démo | Animation CSS remplace, espace prévu pour vidéo plus tard |
