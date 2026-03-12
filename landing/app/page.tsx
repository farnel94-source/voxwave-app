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
