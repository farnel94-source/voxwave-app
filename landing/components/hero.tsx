"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const RAW_TEXT =
  "euh donc en fait j'aimerais euh réserver une table pour ce soir";
const FILLERS = ["euh", "donc", "en fait"];
const CLEAN_TEXT = "J'aimerais réserver une table pour ce soir.";

type Phase = "waveform" | "typing" | "pause" | "cleaning" | "result" | "reset";

function WaveformBars() {
  return (
    <div className="flex h-12 items-center justify-center gap-1">
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

function CleanedText({
  raw,
  fillers,
}: {
  raw: string;
  fillers: string[];
}) {
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
    const timers: ReturnType<typeof setTimeout>[] = [];

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

  const noop = useCallback(() => {}, []);

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
                <TypedText text={RAW_TEXT} onDone={noop} />
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
