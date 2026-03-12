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
