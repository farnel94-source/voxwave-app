"use client";

import { motion } from "framer-motion";

const steps = [
  {
    number: "1",
    title: "Configurez votre raccourci",
    description:
      "Choisissez la touche qui lance la dictée. F8, Ctrl+Shift+V, ou ce que vous voulez.",
  },
  {
    number: "2",
    title: "Parlez",
    description:
      "Appuyez, parlez naturellement, relâchez. VoxWave écoute.",
  },
  {
    number: "3",
    title: "Texte collé automatiquement",
    description:
      "Le texte nettoyé apparaît directement dans votre application active.",
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
