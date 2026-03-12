# VoxWave Landing Page — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium dark landing page for VoxWave that converts visitors into downloads.

**Architecture:** Next.js 15 App Router single page with 10 sections composed in `page.tsx`. Each section is an independent React component in `components/`. Framer Motion handles scroll-triggered animations. Tailwind CSS 4 provides the design system. Static export deployed to Vercel.

**Tech Stack:** Next.js 15 (App Router), Tailwind CSS 4, Framer Motion, TypeScript, Vercel

**Design doc:** `docs/plans/2026-03-12-landing-page-design.md`

---

## Chunk 1: Project Scaffolding & Design System

### Task 1: Scaffold Next.js project

**Files:**
- Create: `landing/` (entire project directory)

- [ ] **Step 1: Create Next.js project**

```bash
cd /home/farne/projets/voice_text
npx create-next-app@latest landing --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --turbopack
```

Select defaults: No to `src/` directory, Yes to App Router, Yes to Tailwind, Yes to TypeScript.

- [ ] **Step 2: Install Framer Motion**

```bash
cd /home/farne/projets/voice_text/landing
npm install framer-motion
```

- [ ] **Step 3: Verify project runs**

```bash
cd /home/farne/projets/voice_text/landing
npm run dev
```

Expected: Server starts on http://localhost:3000, default Next.js page renders.
Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/
git commit -m "chore: scaffold Next.js 15 landing page project"
```

---

### Task 2: Design system — layout, fonts, colors

**Files:**
- Modify: `landing/app/layout.tsx`
- Modify: `landing/app/globals.css`
- Delete: `landing/app/page.tsx` (will rewrite)

- [ ] **Step 1: Replace `landing/app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-bg-primary: #0A0A0A;
  --color-bg-secondary: #111111;
  --color-bg-card: #1A1A1A;
  --color-text-primary: #FFFFFF;
  --color-text-secondary: #A1A1AA;
  --color-text-tertiary: #71717A;
  --color-accent-start: #6366F1;
  --color-accent-end: #8B5CF6;
  --color-border: #27272A;
}

html {
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
}

/* Hero waveform bars animation */
@keyframes waveform {
  0%, 100% { transform: scaleY(0.3); }
  50% { transform: scaleY(1); }
}

/* Marquee scroll animation */
@keyframes marquee {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
```

- [ ] **Step 2: Replace `landing/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "VoxWave — Dictée vocale intelligente pour Windows & Linux",
  description:
    "Parle, VoxWave écrit. Dictée vocale avec nettoyage IA, injection instantanée et mode hors-ligne. Gratuit.",
  keywords: [
    "dictée vocale",
    "voice to text",
    "speech to text",
    "Windows",
    "Linux",
    "Whisper",
    "IA",
  ],
  openGraph: {
    title: "VoxWave — Parle. VoxWave écrit.",
    description:
      "Dictée vocale intelligente avec nettoyage IA. Gratuit pour Windows & Linux.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={inter.className}>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Replace `landing/app/page.tsx` with placeholder**

```tsx
export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <h1 className="text-4xl font-bold text-text-primary">
        VoxWave — Coming Soon
      </h1>
    </main>
  );
}
```

- [ ] **Step 4: Verify design system renders**

```bash
cd /home/farne/projets/voice_text/landing
npm run dev
```

Expected: Dark background (#0A0A0A), white text "VoxWave — Coming Soon" centered, Inter font.

- [ ] **Step 5: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/app/
git commit -m "feat: setup design system with dark theme, Inter font, Tailwind custom colors"
```

---

## Chunk 2: Navbar + Hero

### Task 3: Navbar component

**Files:**
- Create: `landing/components/navbar.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/navbar.tsx`**

```tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Open Source", href: "#open-source" },
  { label: "Comparaison", href: "#comparison" },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-bg-primary/80 backdrop-blur-xl"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <a href="#" className="text-xl font-bold text-text-primary">
          VoxWave
        </a>

        {/* Desktop links */}
        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-text-secondary transition-colors hover:text-text-primary"
            >
              {link.label}
            </a>
          ))}
          <a
            href="#download"
            className="rounded-full bg-gradient-to-r from-accent-start to-accent-end px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Télécharger
          </a>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex flex-col gap-1.5 md:hidden"
          aria-label="Menu"
        >
          <span
            className={`h-0.5 w-6 bg-text-primary transition-transform ${menuOpen ? "translate-y-2 rotate-45" : ""}`}
          />
          <span
            className={`h-0.5 w-6 bg-text-primary transition-opacity ${menuOpen ? "opacity-0" : ""}`}
          />
          <span
            className={`h-0.5 w-6 bg-text-primary transition-transform ${menuOpen ? "-translate-y-2 -rotate-45" : ""}`}
          />
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-border/50 bg-bg-primary/95 px-6 py-4 backdrop-blur-xl md:hidden"
        >
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className="block py-3 text-text-secondary hover:text-text-primary"
            >
              {link.label}
            </a>
          ))}
          <a
            href="#download"
            onClick={() => setMenuOpen(false)}
            className="mt-2 block rounded-full bg-gradient-to-r from-accent-start to-accent-end px-5 py-3 text-center text-sm font-medium text-white"
          >
            Télécharger
          </a>
        </motion.div>
      )}
    </motion.nav>
  );
}
```

- [ ] **Step 2: Add Navbar to `landing/app/page.tsx`**

```tsx
import Navbar from "@/components/navbar";

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="pt-20">
        <div className="flex min-h-screen items-center justify-center">
          <h1 className="text-4xl font-bold">VoxWave</h1>
        </div>
      </main>
    </>
  );
}
```

- [ ] **Step 3: Verify navbar renders**

```bash
cd /home/farne/projets/voice_text/landing && npm run dev
```

Expected: Fixed navbar with blur effect, gradient CTA button, hamburger on mobile.

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/navbar.tsx landing/app/page.tsx
git commit -m "feat: add fixed navbar with blur backdrop and mobile menu"
```

---

### Task 4: Hero section with workflow animation

**Files:**
- Create: `landing/components/hero.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/hero.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const RAW_TEXT = "euh donc en fait j'aimerais euh réserver une table pour ce soir";
const FILLERS = ["euh", "donc", "en fait"];
const CLEAN_TEXT = "J'aimerais réserver une table pour ce soir.";

type Phase = "waveform" | "typing" | "pause" | "cleaning" | "result" | "reset";

function WaveformBars() {
  return (
    <div className="flex items-center justify-center gap-1 h-12">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className="w-1 rounded-full bg-gradient-to-t from-accent-start to-accent-end"
          style={{
            animation: `waveform 1.2s ease-in-out infinite`,
            animationDelay: `${i * 0.05}s`,
            height: "100%",
          }}
        />
      ))}
    </div>
  );
}

function TypedText({ text, onDone }: { text: string; onDone: () => void }) {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        onDone();
      }
    }, 40);
    return () => clearInterval(interval);
  }, [text, onDone]);

  return (
    <span className="text-text-secondary">
      {displayed}
      <span className="animate-pulse text-accent-start">|</span>
    </span>
  );
}

function CleanedText({ raw, fillers }: { raw: string; fillers: string[] }) {
  const words = raw.split(" ");
  return (
    <span>
      {words.map((word, i) => {
        const isFiller = fillers.some(
          (f) => word.toLowerCase() === f.toLowerCase()
        );
        return (
          <motion.span
            key={i}
            initial={{ opacity: 1 }}
            animate={
              isFiller
                ? { opacity: 0.3, textDecoration: "line-through" }
                : { opacity: 1 }
            }
            transition={{ duration: 0.4, delay: i * 0.05 }}
            className={isFiller ? "text-red-400/60" : "text-text-secondary"}
          >
            {word}{" "}
          </motion.span>
        );
      })}
    </span>
  );
}

export default function Hero() {
  const [phase, setPhase] = useState<Phase>("waveform");

  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];

    const run = () => {
      setPhase("waveform");
      timers.push(setTimeout(() => setPhase("typing"), 2500));
      timers.push(setTimeout(() => setPhase("pause"), 5000));
      timers.push(setTimeout(() => setPhase("cleaning"), 5500));
      timers.push(setTimeout(() => setPhase("result"), 6500));
      timers.push(setTimeout(() => setPhase("reset"), 8000));
      timers.push(setTimeout(() => run(), 8200));
    };

    run();
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-20 text-center">
      {/* Gradient glow behind */}
      <div className="pointer-events-none absolute top-1/4 h-96 w-96 rounded-full bg-accent-start/10 blur-[120px]" />

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-5xl font-bold tracking-tight md:text-7xl"
      >
        Parle.{" "}
        <span className="bg-gradient-to-r from-accent-start to-accent-end bg-clip-text text-transparent">
          VoxWave
        </span>{" "}
        écrit.
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mt-6 max-w-xl text-lg text-text-secondary md:text-xl"
      >
        Dictée vocale intelligente pour Windows & Linux. Gratuit.
      </motion.p>

      {/* CTA buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="mt-8 flex flex-col gap-4 sm:flex-row"
      >
        <a
          href="#download"
          className="rounded-full bg-gradient-to-r from-accent-start to-accent-end px-8 py-3 text-base font-medium text-white transition-opacity hover:opacity-90"
        >
          Télécharger gratuitement
        </a>
        <a
          href="#features"
          className="rounded-full border border-border px-8 py-3 text-base font-medium text-text-secondary transition-colors hover:border-text-tertiary hover:text-text-primary"
        >
          Voir en action ↓
        </a>
      </motion.div>

      {/* Platform badges */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-6 flex items-center gap-4 text-sm text-text-tertiary"
      >
        <span>Windows</span>
        <span className="h-3 w-px bg-border" />
        <span>Linux</span>
      </motion.div>

      {/* Animation demo box */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.6 }}
        className="mt-12 w-full max-w-2xl rounded-2xl border border-border bg-bg-secondary p-8"
      >
        <div className="min-h-[80px] text-left text-base">
          <AnimatePresence mode="wait">
            {phase === "waveform" && (
              <motion.div
                key="waveform"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <WaveformBars />
              </motion.div>
            )}
            {phase === "typing" && (
              <motion.div
                key="typing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <TypedText text={RAW_TEXT} onDone={() => {}} />
              </motion.div>
            )}
            {(phase === "pause" || phase === "cleaning") && (
              <motion.div
                key="cleaning"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <CleanedText raw={RAW_TEXT} fillers={FILLERS} />
              </motion.div>
            )}
            {phase === "result" && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-lg font-medium text-text-primary"
              >
                {CLEAN_TEXT}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Phase indicator dots */}
        <div className="mt-4 flex items-center justify-center gap-2">
          {(["waveform", "typing", "cleaning", "result"] as const).map((p) => (
            <div
              key={p}
              className={`h-1.5 w-1.5 rounded-full transition-colors ${
                phase === p || (phase === "pause" && p === "cleaning")
                  ? "bg-accent-start"
                  : "bg-border"
              }`}
            />
          ))}
        </div>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Add Hero to `landing/app/page.tsx`**

```tsx
import Navbar from "@/components/navbar";
import Hero from "@/components/hero";

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
      </main>
    </>
  );
}
```

- [ ] **Step 3: Verify hero renders with animation**

```bash
cd /home/farne/projets/voice_text/landing && npm run dev
```

Expected: Title "Parle. VoxWave écrit." with gradient text, subtitle, CTA buttons, demo box with cycling animation (waveform → typing → cleaning → result → loop).

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/hero.tsx landing/app/page.tsx
git commit -m "feat: add hero section with animated workflow demo"
```

---

## Chunk 3: App Marquee + Features Cards

### Task 5: App marquee (scrolling app icons)

**Files:**
- Create: `landing/components/app-marquee.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/app-marquee.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

const apps = [
  "VS Code",
  "Chrome",
  "Word",
  "Slack",
  "Terminal",
  "Discord",
  "Notion",
  "LibreOffice",
  "Telegram",
  "Firefox",
  "Obsidian",
  "Teams",
];

export default function AppMarquee() {
  return (
    <section className="border-y border-border/50 py-12">
      <motion.p
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        className="mb-8 text-center text-sm text-text-tertiary"
      >
        Fonctionne dans toutes vos applications
      </motion.p>

      <div className="relative overflow-hidden">
        {/* Fade edges */}
        <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-24 bg-gradient-to-r from-bg-primary to-transparent" />
        <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-24 bg-gradient-to-l from-bg-primary to-transparent" />

        <div
          className="flex w-max gap-12"
          style={{ animation: "marquee 30s linear infinite" }}
        >
          {/* Duplicate for seamless loop */}
          {[...apps, ...apps].map((app, i) => (
            <div
              key={i}
              className="flex items-center gap-2 text-text-tertiary"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-bg-card text-xs font-medium">
                {app[0]}
              </div>
              <span className="whitespace-nowrap text-sm">{app}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx after Hero**

- [ ] **Step 3: Verify marquee scrolls**

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/app-marquee.tsx landing/app/page.tsx
git commit -m "feat: add scrolling app compatibility marquee"
```

---

### Task 6: Features cards (4 cards grid)

**Files:**
- Create: `landing/components/features.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/features.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

const features = [
  {
    icon: "⚡",
    title: "< 1 seconde",
    description:
      "Le texte apparaît instantanément. Le nettoyage se fait en arrière-plan.",
  },
  {
    icon: "🧠",
    title: "S'adapte au contexte",
    description:
      "Détecte VS Code, Terminal, Word... et ajuste le nettoyage automatiquement. Mode brut disponible.",
  },
  {
    icon: "🌐",
    title: "Cloud + Hors-ligne",
    description:
      "Fonctionne en ligne (rapide) et hors-ligne (privé). Bascule automatique si la connexion tombe.",
  },
  {
    icon: "🧹",
    title: "Nettoyage IA",
    description:
      "Supprime les \"euh\", corrige la ponctuation, garde votre style naturel.",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-24">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="mb-16 text-center text-3xl font-bold md:text-4xl"
      >
        Tout ce qu&apos;il faut.{" "}
        <span className="text-text-secondary">Rien de superflu.</span>
      </motion.h2>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.2 }}
        className="grid gap-6 md:grid-cols-2"
      >
        {features.map((feature) => (
          <motion.div
            key={feature.title}
            variants={itemVariants}
            className="group rounded-2xl border border-border bg-bg-card p-8 transition-colors hover:border-accent-start/30"
          >
            <span className="text-3xl">{feature.icon}</span>
            <h3 className="mt-4 text-xl font-semibold">{feature.title}</h3>
            <p className="mt-2 leading-relaxed text-text-secondary">
              {feature.description}
            </p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx after AppMarquee**

- [ ] **Step 3: Verify grid renders with scroll animation**

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/features.tsx landing/app/page.tsx
git commit -m "feat: add features section with 4 animated cards"
```

---

## Chunk 4: Context Showcase + How It Works

### Task 7: Context showcase (adaptive app detection)

**Files:**
- Create: `landing/components/context-showcase.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/context-showcase.tsx`**

```tsx
"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const contexts = [
  {
    app: "VS Code",
    icon: "{ }",
    color: "#007ACC",
    input: '"crée une fonction qui vérifie si un nombre est premier"',
    output: "def is_prime(n):\n    if n <= 1:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
    mode: "Code — pas de nettoyage LLM",
  },
  {
    app: "Word",
    icon: "W",
    color: "#2B579A",
    input: '"crée une fonction qui vérifie si un nombre est premier"',
    output:
      "Créez une fonction qui prend un nombre en paramètre et retourne vrai s'il est premier.",
    mode: "Professionnel — ponctuation et style",
  },
  {
    app: "Slack",
    icon: "#",
    color: "#4A154B",
    input: '"crée une fonction qui vérifie si un nombre est premier"',
    output: "crée une fonction qui vérifie si un nombre est premier",
    mode: "Naturel — style conversationnel",
  },
];

export default function ContextShowcase() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % contexts.length);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  const active = contexts[activeIndex];

  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-4 text-center text-3xl font-bold md:text-4xl"
      >
        S&apos;adapte à votre environnement
      </motion.h2>
      <motion.p
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        className="mb-12 text-center text-text-secondary"
      >
        Même dictée, résultat différent selon l&apos;application.
      </motion.p>

      {/* App selector tabs */}
      <div className="mb-8 flex justify-center gap-4">
        {contexts.map((ctx, i) => (
          <button
            key={ctx.app}
            onClick={() => setActiveIndex(i)}
            className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-all ${
              i === activeIndex
                ? "border-accent-start/50 bg-accent-start/10 text-text-primary"
                : "border-border text-text-tertiary hover:text-text-secondary"
            }`}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded text-xs font-bold text-white"
              style={{ backgroundColor: ctx.color }}
            >
              {ctx.icon}
            </span>
            {ctx.app}
          </button>
        ))}
      </div>

      {/* Result display */}
      <div className="mx-auto max-w-2xl rounded-2xl border border-border bg-bg-secondary p-8">
        <div className="mb-4 text-sm text-text-tertiary">
          🎙️ {active.input}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <pre className="whitespace-pre-wrap rounded-xl border border-border bg-bg-primary p-6 font-mono text-sm leading-relaxed text-text-primary">
              {active.output}
            </pre>
            <p className="mt-4 text-sm text-text-tertiary">
              Mode : {active.mode}
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx after Features**

- [ ] **Step 3: Verify auto-cycling between apps works**

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/context-showcase.tsx landing/app/page.tsx
git commit -m "feat: add context-aware showcase section with app switching"
```

---

### Task 8: How it works (3 steps)

**Files:**
- Create: `landing/components/how-it-works.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/how-it-works.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

const steps = [
  {
    number: "1",
    title: "Configurez votre raccourci",
    description: "Choisissez la touche qui lance la dictée. F8, Ctrl+Shift+V, ou ce que vous voulez.",
  },
  {
    number: "2",
    title: "Parlez",
    description: "Appuyez, parlez naturellement, relâchez. VoxWave écoute.",
  },
  {
    number: "3",
    title: "Texte collé automatiquement",
    description: "Le texte nettoyé apparaît directement dans votre application active.",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function HowItWorks() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-16 text-center text-3xl font-bold md:text-4xl"
      >
        Simple comme{" "}
        <span className="text-text-secondary">1, 2, 3</span>
      </motion.h2>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
        className="grid gap-8 md:grid-cols-3"
      >
        {steps.map((step, i) => (
          <motion.div
            key={step.number}
            variants={itemVariants}
            className="relative text-center"
          >
            {/* Connector line (desktop only) */}
            {i < steps.length - 1 && (
              <div className="absolute right-0 top-8 hidden h-px w-full translate-x-1/2 bg-gradient-to-r from-border to-transparent md:block" />
            )}

            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-bg-card text-2xl font-bold text-accent-start">
              {step.number}
            </div>
            <h3 className="mb-2 text-lg font-semibold">{step.title}</h3>
            <p className="text-sm leading-relaxed text-text-secondary">
              {step.description}
            </p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx after ContextShowcase**

- [ ] **Step 3: Verify 3 steps with connector lines**

- [ ] **Step 4: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/how-it-works.tsx landing/app/page.tsx
git commit -m "feat: add how-it-works section with 3 steps"
```

---

## Chunk 5: Open Source + Comparison + CTA + Footer

### Task 9: Open Source section

**Files:**
- Create: `landing/components/open-source.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/open-source.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

export default function OpenSource() {
  return (
    <section id="open-source" className="mx-auto max-w-6xl px-6 py-24">
      <div className="overflow-hidden rounded-2xl border border-border bg-bg-secondary">
        <div className="grid items-center gap-8 p-8 md:grid-cols-2 md:p-12">
          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold md:text-4xl">
              Open Source{" "}
              <span className="text-text-secondary">au coeur</span>
            </h2>
            <p className="mt-4 leading-relaxed text-text-secondary">
              La version locale de VoxWave est gratuite et open source sur
              GitHub. VoxWave App ajoute le cloud IA, le nettoyage LLM
              intelligent et les mises à jour automatiques.
            </p>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-6 inline-flex items-center gap-2 rounded-full border border-border px-6 py-3 text-sm font-medium text-text-primary transition-colors hover:border-text-tertiary"
            >
              ⭐ Voir sur GitHub
            </a>
          </motion.div>

          {/* Terminal mockup */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-xl border border-border bg-bg-primary p-6"
          >
            <div className="mb-4 flex gap-2">
              <div className="h-3 w-3 rounded-full bg-red-500/60" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
              <div className="h-3 w-3 rounded-full bg-green-500/60" />
            </div>
            <pre className="font-mono text-sm leading-relaxed">
              <span className="text-text-tertiary">$</span>{" "}
              <span className="text-accent-start">git clone</span>{" "}
              <span className="text-text-secondary">
                https://github.com/voxwave/voxwave
              </span>
              {"\n"}
              <span className="text-text-tertiary">$</span>{" "}
              <span className="text-accent-start">cd</span>{" "}
              <span className="text-text-secondary">voxwave</span>
              {"\n"}
              <span className="text-text-tertiary">$</span>{" "}
              <span className="text-accent-start">pip install</span>{" "}
              <span className="text-text-secondary">-r requirements.txt</span>
              {"\n"}
              <span className="text-text-tertiary">$</span>{" "}
              <span className="text-accent-start">python -m voxwave</span>
              {"\n\n"}
              <span className="text-green-400">✓ VoxWave is running</span>
            </pre>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx**

- [ ] **Step 3: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/open-source.tsx landing/app/page.tsx
git commit -m "feat: add open source section with terminal mockup"
```

---

### Task 10: Comparison table

**Files:**
- Create: `landing/components/comparison.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/comparison.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

const rows = [
  { label: "Prix", voxwave: "Gratuit", wispr: "$12/mois", dragon: "$699", os: "Gratuit" },
  { label: "Windows + Linux", voxwave: true, wispr: false, dragon: true, os: true },
  { label: "Mode hors-ligne", voxwave: true, wispr: false, dragon: true, os: false },
  { label: "Nettoyage IA", voxwave: true, wispr: true, dragon: false, os: false },
  { label: "Injection < 1s", voxwave: true, wispr: true, dragon: false, os: false },
  { label: "Adaptatif par app", voxwave: true, wispr: false, dragon: false, os: false },
];

function Cell({ value }: { value: boolean | string }) {
  if (typeof value === "string") {
    return <span className="font-medium">{value}</span>;
  }
  return value ? (
    <span className="text-green-400">✓</span>
  ) : (
    <span className="text-text-tertiary">✗</span>
  );
}

export default function Comparison() {
  return (
    <section id="comparison" className="mx-auto max-w-4xl px-6 py-24">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-12 text-center text-3xl font-bold md:text-4xl"
      >
        VoxWave vs. le reste
      </motion.h2>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="overflow-x-auto rounded-2xl border border-border"
      >
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-bg-secondary">
              <th className="p-4 text-left font-medium text-text-tertiary" />
              <th className="p-4 text-center font-semibold text-accent-start">
                VoxWave
              </th>
              <th className="p-4 text-center font-medium text-text-secondary">
                Wispr Flow
              </th>
              <th className="p-4 text-center font-medium text-text-secondary">
                Dragon
              </th>
              <th className="p-4 text-center font-medium text-text-secondary">
                OS Built-in
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={row.label}
                className={`border-b border-border/50 ${i % 2 === 0 ? "bg-bg-primary" : "bg-bg-secondary/50"}`}
              >
                <td className="p-4 font-medium text-text-secondary">
                  {row.label}
                </td>
                <td className="p-4 text-center">
                  <Cell value={row.voxwave} />
                </td>
                <td className="p-4 text-center">
                  <Cell value={row.wispr} />
                </td>
                <td className="p-4 text-center">
                  <Cell value={row.dragon} />
                </td>
                <td className="p-4 text-center">
                  <Cell value={row.os} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Add to page.tsx**

- [ ] **Step 3: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/comparison.tsx landing/app/page.tsx
git commit -m "feat: add competitor comparison table"
```

---

### Task 11: CTA final + Footer

**Files:**
- Create: `landing/components/cta-final.tsx`
- Create: `landing/components/footer.tsx`
- Modify: `landing/app/page.tsx`

- [ ] **Step 1: Create `landing/components/cta-final.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";

export default function CtaFinal() {
  return (
    <section
      id="download"
      className="relative mx-auto max-w-4xl px-6 py-32 text-center"
    >
      {/* Background glow */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="h-64 w-64 rounded-full bg-accent-start/10 blur-[100px]" />
      </div>

      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="relative text-4xl font-bold md:text-5xl"
      >
        Arrêtez de taper.
        <br />
        <span className="bg-gradient-to-r from-accent-start to-accent-end bg-clip-text text-transparent">
          Commencez à parler.
        </span>
      </motion.h2>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="relative mt-8"
      >
        <a
          href="#"
          className="inline-block rounded-full bg-gradient-to-r from-accent-start to-accent-end px-10 py-4 text-lg font-medium text-white transition-opacity hover:opacity-90"
        >
          Télécharger gratuitement — Windows & Linux
        </a>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Create `landing/components/footer.tsx`**

```tsx
export default function Footer() {
  return (
    <footer className="border-t border-border/50 px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-text-tertiary sm:flex-row">
        <span className="font-medium text-text-secondary">VoxWave</span>
        <div className="flex gap-6">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-text-primary"
          >
            GitHub
          </a>
          <a href="#" className="transition-colors hover:text-text-primary">
            Contact
          </a>
          <a href="#" className="transition-colors hover:text-text-primary">
            Mentions légales
          </a>
        </div>
        <span>Made with 🎙️</span>
      </div>
    </footer>
  );
}
```

- [ ] **Step 3: Final `landing/app/page.tsx` with all sections**

```tsx
import Navbar from "@/components/navbar";
import Hero from "@/components/hero";
import AppMarquee from "@/components/app-marquee";
import Features from "@/components/features";
import ContextShowcase from "@/components/context-showcase";
import HowItWorks from "@/components/how-it-works";
import OpenSource from "@/components/open-source";
import Comparison from "@/components/comparison";
import CtaFinal from "@/components/cta-final";
import Footer from "@/components/footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <AppMarquee />
        <Features />
        <ContextShowcase />
        <HowItWorks />
        <OpenSource />
        <Comparison />
        <CtaFinal />
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 4: Full visual check**

```bash
cd /home/farne/projets/voice_text/landing && npm run dev
```

Expected: Complete single-page landing with all 10 sections, scroll animations, dark premium theme.

- [ ] **Step 5: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/components/cta-final.tsx landing/components/footer.tsx landing/app/page.tsx
git commit -m "feat: add CTA final, footer, and assemble complete landing page"
```

---

## Chunk 6: Polish & Deploy

### Task 12: Responsive polish

**Files:**
- Modify: various components as needed

- [ ] **Step 1: Test mobile view (Chrome DevTools, 375px width)**

Check each section:
- Navbar: hamburger menu works
- Hero: text readable, CTA full-width
- Marquee: scrolls without overflow
- Features: single column stack
- Context showcase: tabs wrap properly
- Comparison: table scrollable horizontally
- CTA: text wraps nicely

- [ ] **Step 2: Fix any layout issues found**

- [ ] **Step 3: Commit**

```bash
cd /home/farne/projets/voice_text
git add landing/
git commit -m "fix: responsive polish for mobile and tablet"
```

---

### Task 13: Build & deploy to Vercel

**Files:**
- No new files

- [ ] **Step 1: Test production build**

```bash
cd /home/farne/projets/voice_text/landing
npm run build
```

Expected: Build succeeds with no errors. Check for any TypeScript or lint errors.

- [ ] **Step 2: Test production server locally**

```bash
cd /home/farne/projets/voice_text/landing
npm run start
```

Expected: Production server on http://localhost:3000, all sections render correctly.

- [ ] **Step 3: Deploy to Vercel**

```bash
cd /home/farne/projets/voice_text/landing
npx vercel
```

Follow prompts: link to Vercel account, select project name "voxwave-landing".

- [ ] **Step 4: Verify live URL**

Open the Vercel URL in browser. Check all sections render, animations work, mobile view ok.

- [ ] **Step 5: Commit Vercel config if generated**

```bash
cd /home/farne/projets/voice_text
git add landing/.vercel landing/vercel.json 2>/dev/null
git commit -m "chore: add Vercel deployment config" 2>/dev/null || true
```
