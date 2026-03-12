"use client";

import { motion } from "framer-motion";

const rows = [
  {
    label: "Prix",
    voxwave: "Gratuit",
    wispr: "$12/mois",
    dragon: "$699",
    os: "Gratuit",
  },
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
                className={`border-b border-border/50 ${
                  i % 2 === 0 ? "bg-bg-primary" : "bg-bg-secondary/50"
                }`}
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
