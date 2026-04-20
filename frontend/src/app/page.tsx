"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function HomePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("token"));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center text-white font-bold text-lg">M</div>
          <span className="text-xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">MoneyPrinter</span>
        </div>
        <div className="flex items-center gap-4">
          {isLoggedIn ? (
            <Link href="/dashboard" className="btn-primary">Dashboard →</Link>
          ) : (
            <>
              <Link href="/login" className="btn-secondary">Log In</Link>
              <Link href="/login?mode=register" className="btn-primary">Get Started Free</Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div className="animate-fade-in max-w-3xl">
          <div className="badge badge-info mb-6 text-sm">✨ AI-Powered Video Creation</div>
          <h1 className="text-5xl md:text-7xl font-bold leading-tight mb-6">
            Create <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">Viral Videos</span>
            <br />in Minutes
          </h1>
          <p className="text-lg text-[var(--text-secondary)] max-w-xl mx-auto mb-10 leading-relaxed">
            Enter a topic. Choose a style. Get a professional short-form video with AI voiceover, 
            captions, stock footage, and background music — ready for TikTok, Shorts & Reels.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/login?mode=register" className="btn-primary text-lg px-10 py-4">
              Start Creating — It&apos;s Free →
            </Link>
            <a href="#demo" className="btn-secondary text-lg px-10 py-4">
              See Demo ▶
            </a>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-4">3 free videos • No credit card required</p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 max-w-5xl w-full" style={{animationDelay: "0.2s"}}>
          {[
            { icon: "🎬", title: "AI Script & Voice", desc: "GPT writes the script, Edge-TTS or ElevenLabs narrates it" },
            { icon: "🎥", title: "Stock B-Roll", desc: "Auto-matched HD clips from Pexels & Pixabay" },
            { icon: "🎵", title: "Music & Captions", desc: "Mood-based BGM from Jamendo + animated subtitles" },
          ].map((f, i) => (
            <div key={i} className="glass-card p-8 text-left animate-fade-in" style={{animationDelay: `${0.1 * (i+1)}s`}}>
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Pricing */}
        <div className="mt-32 max-w-5xl w-full mb-20">
          <h2 className="text-3xl font-bold text-center mb-12">Simple Pricing</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: "Free", price: "$0", credits: "3 videos", features: ["HD export", "Edge-TTS voices", "Pexels stock", "Basic captions"], cta: "Get Started", highlight: false },
              { name: "Pro", price: "$19/mo", credits: "100 videos/mo", features: ["4K export", "ElevenLabs voices", "Priority queue", "Custom branding", "API access"], cta: "Upgrade to Pro", highlight: true },
              { name: "Studio", price: "$69/mo", credits: "500 videos/mo", features: ["Everything in Pro", "Bulk generation", "Webhook notifications", "Dedicated support", "White-label"], cta: "Contact Sales", highlight: false },
            ].map((plan, i) => (
              <div key={i} className={`glass-card p-8 text-left relative ${plan.highlight ? 'border-purple-500/50' : ''}`}
                   style={plan.highlight ? {boxShadow: '0 0 40px rgba(124,58,237,0.15)'} : {}}>
                {plan.highlight && <div className="absolute -top-3 left-1/2 -translate-x-1/2 badge badge-info">Most Popular</div>}
                <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
                <div className="text-3xl font-bold mb-1">{plan.price}</div>
                <div className="text-sm text-[var(--text-secondary)] mb-6">{plan.credits}</div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((f, j) => (
                    <li key={j} className="text-sm text-[var(--text-secondary)] flex items-center gap-2">
                      <span className="text-[var(--success)]">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button className={plan.highlight ? "btn-primary w-full" : "btn-secondary w-full"}>
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-8 text-center text-sm text-[var(--text-secondary)]">
        © 2026 MoneyPrinter Studio. Built with ❤️ and AI.
      </footer>
    </div>
  );
}
