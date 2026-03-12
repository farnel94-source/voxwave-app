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
              Voir sur GitHub
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
              <span className="text-green-400">
                ✓ VoxWave is running
              </span>
            </pre>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
