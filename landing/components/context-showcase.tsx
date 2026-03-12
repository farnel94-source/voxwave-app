"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const contexts = [
  {
    app: "VS Code",
    icon: "{ }",
    color: "#007ACC",
    input:
      '"crée une fonction qui vérifie si un nombre est premier"',
    output:
      "def is_prime(n):\n    if n <= 1:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
    mode: "Code — pas de nettoyage LLM",
  },
  {
    app: "Word",
    icon: "W",
    color: "#2B579A",
    input:
      '"crée une fonction qui vérifie si un nombre est premier"',
    output:
      "Créez une fonction qui prend un nombre en paramètre et retourne vrai s'il est premier.",
    mode: "Professionnel — ponctuation et style",
  },
  {
    app: "Slack",
    icon: "#",
    color: "#4A154B",
    input:
      '"crée une fonction qui vérifie si un nombre est premier"',
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
      <div className="mb-8 flex flex-wrap justify-center gap-4">
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
