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
      'Supprime les "euh", corrige la ponctuation, garde votre style naturel.',
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
