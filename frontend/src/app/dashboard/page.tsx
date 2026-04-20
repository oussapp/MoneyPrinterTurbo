"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { projects, auth } from "@/lib/api";

interface Project {
  id: string;
  topic: string;
  status: string;
  video_url: string | null;
  duration: number | null;
  aspect_ratio: string;
  credits_used: number;
  created_at: string;
}

interface UserInfo {
  id: string;
  email: string;
  display_name: string;
  credits: number;
  subscription_tier: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [projectList, setProjectList] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState<string[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    loadData();
  }, []);

  // Poll active jobs every 5s
  useEffect(() => {
    if (polling.length === 0) return;
    const interval = setInterval(async () => {
      const updated = await projects.list();
      setProjectList(updated.projects);
      const stillActive = updated.projects
        .filter((p: Project) => ["queued", "processing"].includes(p.status))
        .map((p: Project) => p.id);
      if (stillActive.length === 0) clearInterval(interval);
      setPolling(stillActive);
    }, 5000);
    return () => clearInterval(interval);
  }, [polling]);

  async function loadData() {
    try {
      const [userData, projData] = await Promise.all([auth.me(), projects.list()]);
      setUser(userData);
      setProjectList(projData.projects);
      const active = projData.projects
        .filter((p: Project) => ["queued", "processing"].includes(p.status))
        .map((p: Project) => p.id);
      setPolling(active);
    } catch {
      localStorage.removeItem("token");
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this project?")) return;
    await projects.delete(id);
    setProjectList(prev => prev.filter(p => p.id !== id));
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/");
  }

  const statusBadge = (s: string) => {
    const map: Record<string, { class: string; label: string }> = {
      draft: { class: "badge-info", label: "📝 Draft" },
      queued: { class: "badge-warning", label: "⏳ Queued" },
      processing: { class: "badge-warning", label: "🔄 Rendering" },
      complete: { class: "badge-success", label: "✅ Ready" },
      failed: { class: "badge-error", label: "❌ Failed" },
    };
    const info = map[s] || { class: "badge-info", label: s };
    return <span className={`badge ${info.class}`}>{info.label}</span>;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[var(--text-secondary)]">Loading studio...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Sidebar + Main Layout */}
      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 min-h-screen border-r border-[var(--border)] bg-[var(--bg-secondary)] p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center text-white font-bold">M</div>
            <span className="text-lg font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">Studio</span>
          </div>

          <nav className="flex-1 space-y-2">
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[var(--accent)]/10 text-[var(--accent)] font-medium text-sm">
              🎬 My Videos
            </Link>
            <Link href="/create" className="flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--text-secondary)] hover:bg-[var(--bg-card)] text-sm transition-colors">
              ➕ Create Video
            </Link>
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--text-secondary)] hover:bg-[var(--bg-card)] text-sm transition-colors">
              🎵 Music Library
            </Link>
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--text-secondary)] hover:bg-[var(--bg-card)] text-sm transition-colors">
              ⚙️ Settings
            </Link>
          </nav>

          {/* Credits */}
          <div className="glass-card p-4 mb-4">
            <div className="text-xs text-[var(--text-secondary)] mb-1">Credits</div>
            <div className="text-2xl font-bold">{user?.credits ?? 0}</div>
            <div className="text-xs text-[var(--text-secondary)] mb-3">{user?.subscription_tier === "free" ? "Free tier" : `${user?.subscription_tier} plan`}</div>
            <button className="btn-primary w-full text-xs py-2">Buy Credits</button>
          </div>

          {/* User */}
          <div className="flex items-center gap-3 pt-4 border-t border-[var(--border)]">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center text-white text-sm font-bold">
              {(user?.display_name || user?.email || "U")[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user?.display_name || "User"}</div>
              <button onClick={logout} className="text-xs text-[var(--text-secondary)] hover:text-red-400 transition-colors">Log out</button>
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold">My Videos</h1>
              <p className="text-sm text-[var(--text-secondary)] mt-1">{projectList.length} videos created</p>
            </div>
            <Link href="/create" className="btn-primary flex items-center gap-2">
              <span>+</span> New Video
            </Link>
          </div>

          {projectList.length === 0 ? (
            <div className="glass-card p-16 text-center animate-fade-in">
              <div className="text-6xl mb-6">🎬</div>
              <h2 className="text-xl font-bold mb-2">No videos yet</h2>
              <p className="text-[var(--text-secondary)] mb-6">Create your first AI-generated video in under 2 minutes.</p>
              <Link href="/create" className="btn-primary">Create Your First Video →</Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {projectList.map((p, i) => (
                <div key={p.id} className="glass-card overflow-hidden animate-fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                  {/* Thumbnail */}
                  <div className="h-40 bg-gradient-to-br from-purple-900/30 to-blue-900/30 flex items-center justify-center relative">
                    {p.status === "complete" && p.video_url ? (
                      <div className="text-5xl">🎥</div>
                    ) : p.status === "processing" || p.status === "queued" ? (
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                        <span className="text-xs text-[var(--text-secondary)]">Rendering...</span>
                      </div>
                    ) : (
                      <div className="text-5xl opacity-30">🎬</div>
                    )}
                    <div className="absolute top-3 right-3">{statusBadge(p.status)}</div>
                    {p.aspect_ratio && (
                      <div className="absolute bottom-3 left-3 badge badge-info text-xs">{p.aspect_ratio}</div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-5">
                    <h3 className="font-semibold mb-1 truncate">{p.topic}</h3>
                    <p className="text-xs text-[var(--text-secondary)] mb-4">
                      {p.duration ? `${p.duration}s` : "—"} • {new Date(p.created_at).toLocaleDateString()}
                    </p>
                    <div className="flex gap-2">
                      {p.status === "complete" && p.video_url && (
                        <a href={p.video_url} target="_blank" className="btn-primary text-xs py-2 px-4 flex-1 text-center">
                          ⬇ Download
                        </a>
                      )}
                      <button onClick={() => handleDelete(p.id)} className="btn-secondary text-xs py-2 px-4">
                        🗑
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
