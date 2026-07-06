import { useState } from "react";
import JobFeed from "./components/JobFeed";
import Chat from "./components/Chat";
import ApplicationTracker from "./components/ApplicationTracker";

const TABS = [
  { id: "jobs", label: "Job Feed" },
  { id: "chat", label: "AI Assistant" },
  { id: "tracker", label: "Applications" },
];

export default function App() {
  const [tab, setTab] = useState("jobs");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Sam's Job Agent</h1>
            <p className="text-xs text-gray-400">IR · Capital Formation · Finance · NYC</p>
          </div>
          <nav className="flex gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === t.id
                    ? "bg-indigo-600 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6">
        {tab === "jobs" && <JobFeed />}
        {tab === "chat" && <Chat />}
        {tab === "tracker" && <ApplicationTracker />}
      </main>
    </div>
  );
}
