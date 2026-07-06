import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const STATUSES = [
  { value: "applied", label: "Applied", color: "bg-blue-100 text-blue-800" },
  { value: "phone_screen", label: "Phone Screen", color: "bg-yellow-100 text-yellow-800" },
  { value: "interviewing", label: "Interviewing", color: "bg-purple-100 text-purple-800" },
  { value: "offer", label: "Offer", color: "bg-green-100 text-green-800" },
  { value: "rejected", label: "Rejected", color: "bg-red-100 text-red-800" },
  { value: "withdrawn", label: "Withdrawn", color: "bg-gray-100 text-gray-800" },
];

function StatusBadge({ status }) {
  const s = STATUSES.find((x) => x.value === status) || STATUSES[0];
  return (
    <span className={`text-xs font-medium px-2 py-1 rounded-full ${s.color}`}>
      {s.label}
    </span>
  );
}

export default function ApplicationTracker() {
  const [apps, setApps] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company: "", title: "", apply_url: "", status: "applied", notes: "" });

  const fetchApps = async () => {
    const res = await fetch(`${API}/api/applications`);
    setApps(await res.json());
  };

  useEffect(() => { fetchApps(); }, []);

  const addApp = async () => {
    if (!form.company || !form.title) return;
    await fetch(`${API}/api/applications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setForm({ company: "", title: "", apply_url: "", status: "applied", notes: "" });
    setShowForm(false);
    fetchApps();
  };

  const updateStatus = async (id, status) => {
    await fetch(`${API}/api/applications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    fetchApps();
  };

  const deleteApp = async (id) => {
    await fetch(`${API}/api/applications/${id}`, { method: "DELETE" });
    fetchApps();
  };

  const counts = STATUSES.reduce((acc, s) => {
    acc[s.value] = apps.filter((a) => a.status === s.value).length;
    return acc;
  }, {});

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        {STATUSES.map((s) => (
          <div key={s.value} className={`text-xs px-3 py-1 rounded-full ${s.color} font-medium`}>
            {s.label}: {counts[s.value] || 0}
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center mb-3">
        <h3 className="font-medium text-gray-700">{apps.length} applications</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
        >
          + Add Manually
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Company *"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <input
              placeholder="Job title *"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <input
            placeholder="Apply URL"
            value={form.apply_url}
            onChange={(e) => setForm({ ...form, apply_url: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
          <textarea
            placeholder="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button onClick={addApp} className="bg-green-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-green-700">
              Save
            </button>
            <button onClick={() => setShowForm(false)} className="text-sm text-gray-500 px-4 py-2 hover:text-gray-700">
              Cancel
            </button>
          </div>
        </div>
      )}

      {apps.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No applications yet. Apply to jobs from the Job Feed and they'll appear here.
        </div>
      ) : (
        <div className="space-y-2">
          {apps.map((app) => (
            <div key={app.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-gray-900">{app.title}</span>
                  <span className="text-gray-400">·</span>
                  <span className="text-gray-600 text-sm">{app.company}</span>
                  <StatusBadge status={app.status} />
                </div>
                {app.notes && <p className="text-xs text-gray-500 mt-1">{app.notes}</p>}
                <p className="text-xs text-gray-400 mt-1">
                  Applied {new Date(app.applied_date).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <select
                  value={app.status}
                  onChange={(e) => updateStatus(app.id, e.target.value)}
                  className="text-xs border border-gray-300 rounded px-2 py-1"
                >
                  {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
                {app.apply_url && (
                  <a href={app.apply_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline">Link</a>
                )}
                <button onClick={() => deleteApp(app.id)} className="text-xs text-red-400 hover:text-red-600">
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
