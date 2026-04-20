"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { projects, music } from "@/lib/api";

const VOICES = [
  { value: "", label: "🎙️ Auto-detect" },
  { value: "en-US-ChristopherNeural-Male", label: "🇺🇸 Christopher (Male)" },
  { value: "en-US-JennyNeural-Female", label: "🇺🇸 Jenny (Female)" },
  { value: "en-GB-RyanNeural-Male", label: "🇬🇧 Ryan (British Male)" },
  { value: "en-GB-SoniaNeural-Female", label: "🇬🇧 Sonia (British Female)" },
  { value: "en-AU-WilliamNeural-Male", label: "🇦🇺 William (Aussie Male)" },
  { value: "es-ES-AlvaroNeural-Male", label: "🇪🇸 Álvaro (Spanish)" },
  { value: "fr-FR-HenriNeural-Male", label: "🇫🇷 Henri (French)" },
  { value: "de-DE-ConradNeural-Male", label: "🇩🇪 Conrad (German)" },
  { value: "ar-SA-HamedNeural-Male", label: "🇸🇦 Hamed (Arabic)" },
];

const MOODS = [
  { value: "random", label: "🎲 Random" },
  { value: "lofi", label: "☕ Lo-fi Chill" },
  { value: "cinematic", label: "🎬 Cinematic Epic" },
  { value: "upbeat", label: "🎉 Upbeat Fun" },
  { value: "acoustic", label: "🎸 Acoustic" },
  { value: "electronic", label: "🎧 Electronic" },
  { value: "dark", label: "🌑 Dark/Moody" },
];

const STEPS = ["Topic", "Style", "Review"];

export default function CreatePage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Form state
  const [topic, setTopic] = useState("");
  const [script, setScript] = useState("");
  const [useCustomScript, setUseCustomScript] = useState(false);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [voice, setVoice] = useState("");
  const [bgmMood, setBgmMood] = useState("random");
  const [videoSource, setVideoSource] = useState("pexels");

  useEffect(() => {
    if (!localStorage.getItem("token")) router.push("/login");
  }, []);

  async function handleCreate() {
    setError("");
    setSubmitting(true);
    try {
      await projects.create({
        topic,
        script: useCustomScript ? script : undefined,
        aspect_ratio: aspectRatio,
        voice_name: voice,
        bgm_mood: bgmMood,
        video_source: videoSource,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Top Bar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-[var(--border)]">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center text-white font-bold">M</div>
          <span className="text-lg font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">Studio</span>
        </Link>
        <Link href="/dashboard" className="btn-secondary text-sm py-2 px-4">← Back</Link>
      </nav>

      <div className="max-w-2xl mx-auto px-6 py-12 animate-fade-in">
        <h1 className="text-3xl font-bold mb-2">Create New Video</h1>
        <p className="text-[var(--text-secondary)] mb-10">AI will generate a complete video from your topic.</p>

        {/* Progress Steps */}
        <div className="flex items-center gap-0 mb-12">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center flex-1">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                i <= step 
                  ? "bg-gradient-to-br from-purple-600 to-blue-500 text-white" 
                  : "bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border)]"
              }`}>
                {i < step ? "✓" : i + 1}
              </div>
              <div className={`ml-3 text-sm font-medium ${i <= step ? "text-white" : "text-[var(--text-secondary)]"}`}>
                {s}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mx-4 ${i < step ? "bg-purple-500" : "bg-[var(--border)]"}`} />
              )}
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-6 text-sm text-red-400">{error}</div>
        )}

        {/* ── Step 1: Topic ── */}
        {step === 0 && (
          <div className="glass-card p-8 animate-fade-in">
            <h2 className="text-xl font-bold mb-6">What's your video about?</h2>
            
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Topic / Subject</label>
              <input
                type="text"
                className="input-field text-lg"
                placeholder="e.g., 5 Stoic Principles for a Better Life"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-[var(--text-secondary)] mt-2">AI will generate a script based on this topic</p>
            </div>

            <div className="mb-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useCustomScript}
                  onChange={(e) => setUseCustomScript(e.target.checked)}
                  className="w-4 h-4 accent-purple-500"
                />
                <span className="text-sm">I want to write my own script</span>
              </label>
            </div>

            {useCustomScript && (
              <div className="mb-6 animate-fade-in">
                <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Your Script</label>
                <textarea
                  className="input-field min-h-[150px] resize-y"
                  placeholder="Write your video narration here..."
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                />
              </div>
            )}

            {/* Quick Templates */}
            <div className="mb-6">
              <div className="text-xs font-medium text-[var(--text-secondary)] mb-3">Quick Ideas:</div>
              <div className="flex flex-wrap gap-2">
                {["How to Make Money Online", "Top 10 Life Hacks", "Psychology Facts", "Healthy Meal Prep", "Morning Routine Tips"].map((t) => (
                  <button key={t} onClick={() => setTopic(t)} 
                    className="text-xs px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] hover:border-purple-500/50 transition-colors">
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <button onClick={() => setStep(1)} disabled={!topic.trim()} className="btn-primary w-full">
              Next: Choose Style →
            </button>
          </div>
        )}

        {/* ── Step 2: Style ── */}
        {step === 1 && (
          <div className="glass-card p-8 animate-fade-in">
            <h2 className="text-xl font-bold mb-6">Customize Your Video</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {/* Aspect Ratio */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Aspect Ratio</label>
                <div className="flex gap-3">
                  {[
                    { value: "9:16", label: "9:16", icon: "📱", desc: "TikTok/Reels" },
                    { value: "16:9", label: "16:9", icon: "🖥", desc: "YouTube" },
                    { value: "1:1", label: "1:1", icon: "⬜", desc: "Instagram" },
                  ].map((ar) => (
                    <button key={ar.value} onClick={() => setAspectRatio(ar.value)}
                      className={`flex-1 p-4 rounded-xl border text-center transition-all ${
                        aspectRatio === ar.value 
                          ? "border-purple-500 bg-purple-500/10" 
                          : "border-[var(--border)] hover:border-purple-500/30"
                      }`}>
                      <div className="text-2xl mb-1">{ar.icon}</div>
                      <div className="text-sm font-bold">{ar.label}</div>
                      <div className="text-xs text-[var(--text-secondary)]">{ar.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Video Source */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Stock Footage</label>
                <select className="select-field" value={videoSource} onChange={(e) => setVideoSource(e.target.value)}>
                  <option value="pexels">🎥 Pexels (Recommended)</option>
                  <option value="pixabay">📹 Pixabay</option>
                  <option value="local">📂 Local Files</option>
                </select>
              </div>

              {/* Voice */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Voice</label>
                <select className="select-field" value={voice} onChange={(e) => setVoice(e.target.value)}>
                  {VOICES.map((v) => (
                    <option key={v.value} value={v.value}>{v.label}</option>
                  ))}
                </select>
              </div>

              {/* Music */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">Background Music</label>
                <select className="select-field" value={bgmMood} onChange={(e) => setBgmMood(e.target.value)}>
                  {MOODS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(0)} className="btn-secondary flex-1">← Back</button>
              <button onClick={() => setStep(2)} className="btn-primary flex-1">Review & Create →</button>
            </div>
          </div>
        )}

        {/* ── Step 3: Review ── */}
        {step === 2 && (
          <div className="glass-card p-8 animate-fade-in">
            <h2 className="text-xl font-bold mb-6">Review Your Video</h2>

            <div className="space-y-4 mb-8">
              {[
                { label: "Topic", value: topic },
                { label: "Script", value: useCustomScript ? "Custom script" : "AI-generated" },
                { label: "Aspect Ratio", value: aspectRatio },
                { label: "Voice", value: VOICES.find(v => v.value === voice)?.label || "Auto" },
                { label: "Music", value: MOODS.find(m => m.value === bgmMood)?.label || "Random" },
                { label: "Stock Source", value: videoSource === "pexels" ? "Pexels" : videoSource === "pixabay" ? "Pixabay" : "Local" },
                { label: "Credits", value: "1 credit" },
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center py-3 border-b border-[var(--border)] last:border-0">
                  <span className="text-sm text-[var(--text-secondary)]">{item.label}</span>
                  <span className="text-sm font-medium">{item.value}</span>
                </div>
              ))}
            </div>

            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 mb-6 text-sm">
              ⚡ This will use <strong>1 credit</strong>. Your video will be ready in 2-5 minutes.
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="btn-secondary flex-1">← Back</button>
              <button onClick={handleCreate} disabled={submitting} className="btn-primary flex-1">
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Creating...
                  </span>
                ) : (
                  "🚀 Generate Video"
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
