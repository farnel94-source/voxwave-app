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
