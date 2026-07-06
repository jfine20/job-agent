import { useState, useEffect } from "react";

const API = "http://localhost:8000";

const STATUS_COLORS = {
  applied: "bg-blue-100 text-blue-800",
  phone_screen: "bg-yellow-100 text-yellow-800",
  interviewing: "bg-purple-100 text-purple-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-800",
};

function ScoreBadge({ score }) {
  const color =
    score >= 8 ? "bg-green-500" : score >= 5 ? "bg-yellow-500" : "bg-red-400";
  return (
    <span className={`${color} text-white text-xs font-bold px-2 py-1 rounded-full`}>
      {score?.toFixed(1)}/10
    </span>
  );
}

function JobCard({ job, onTrack }) {
  const [expanded, setExpanded] = useState(false);
  const [tailoring, setTailoring] = useState(false);
  const [tailored, setTailored] = useState(null);

  const handleTailor = async () => {
    setTailoring(true);
    try {
      const res = await fetch(`${API}/api/jobs/${job.id}/tailor`, { method: "POST" });
      const data = await res.json();
      setTailored(data);
    } finally {
      setTailoring(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{job.title}</h3>
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm text-gray-600">{job.company} · {job.location}</p>
            {job.source && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SOURCE_COLORS[job.source] || "bg-gray-100 text-gray-600"}`}>
                {job.source}
              </span>
            )}
          </div>
        </div>
        <ScoreBadge score={job.fit_score} />
      </div>

      {job.fit_summary && (
        <p className="mt-2 text-sm text-gray-500 italic">{job.fit_summary}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-blue-600 hover:underline"
        >
          {expanded ? "Hide description" : "Show description"}
        </button>
        <button
          onClick={handleTailor}
          disabled={tailoring}
          className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-full hover:bg-indigo-700 disabled:opacity-50"
        >
          {tailoring ? "Generating..." : "Tailor Resume"}
        </button>
        <button
          onClick={() => onTrack(job)}
          className="text-xs bg-green-600 text-white px-3 py-1 rounded-full hover:bg-green-700"
        >
          Track Application
        </button>
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs bg-gray-800 text-white px-3 py-1 rounded-full hover:bg-gray-900"
          >
            Apply
          </a>
        )}
      </div>

      {expanded && (
        <div className="mt-3 text-xs text-gray-600 bg-gray-50 rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">
          {job.description}
        </div>
      )}

      {tailored && (
        <div className="mt-3 space-y-3">
          <div className="bg-indigo-50 rounded p-3">
            <p className="text-xs font-semibold text-indigo-800 mb-1">Tailored Resume Bullets</p>
            <pre className="text-xs text-indigo-700 whitespace-pre-wrap">{tailored.tailored_bullets}</pre>
          </div>
          <div className="bg-green-50 rounded p-3">
            <p className="text-xs font-semibold text-green-800 mb-1">Cover Letter</p>
            <pre className="text-xs text-green-700 whitespace-pre-wrap">{tailored.cover_letter}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

const SOURCE_COLORS = {
  greenhouse: "bg-green-100 text-green-700",
  lever: "bg-blue-100 text-blue-700",
  indeed: "bg-orange-100 text-orange-700",
};

export default function JobFeed() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [minScore, setMinScore] = useState(5);
  const [sortBy, setSortBy] = useState("score");
  const [filterSource, setFilterSource] = useState("all");
  const [tracked, setTracked] = useState(null);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/jobs?min_score=${minScore}`);
      setJobs(await res.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, [minScore]);

  const sortedJobs = [...jobs]
    .filter(j => filterSource === "all" || j.source === filterSource)
    .sort((a, b) => {
      if (sortBy === "score") return (b.fit_score || 0) - (a.fit_score || 0);
      if (sortBy === "date") return new Date(b.scraped_at) - new Date(a.scraped_at);
      if (sortBy === "company") return a.company.localeCompare(b.company);
      return 0;
    });

  const triggerScrape = async () => {
    setScraping(true);
    await fetch(`${API}/api/jobs/scrape`, { method: "POST" });
    // Scrape takes ~60s, poll until count grows
    const start = jobs.length;
    const poll = setInterval(async () => {
      const res = await fetch(`${API}/api/jobs?min_score=${minScore}`);
      const data = await res.json();
      if (data.length > start) {
        setJobs(data);
        setScraping(false);
        clearInterval(poll);
      }
    }, 5000);
    setTimeout(() => { setScraping(false); clearInterval(poll); fetchJobs(); }, 120000);
  };

  const trackJob = async (job) => {
    await fetch(`${API}/api/applications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: job.id,
        company: job.company,
        title: job.title,
        apply_url: job.apply_url,
        status: "applied",
      }),
    });
    setTracked(job.title);
    setTimeout(() => setTracked(null), 3000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Min score:</label>
          <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="text-sm border border-gray-300 rounded px-2 py-1">
            {[0, 3, 5, 7, 8].map((v) => <option key={v} value={v}>{v}+</option>)}
          </select>
          <label className="text-sm font-medium text-gray-700">Sort:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="text-sm border border-gray-300 rounded px-2 py-1">
            <option value="score">Best fit</option>
            <option value="date">Newest</option>
            <option value="company">Company A-Z</option>
          </select>
          <label className="text-sm font-medium text-gray-700">Source:</label>
          <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)} className="text-sm border border-gray-300 rounded px-2 py-1">
            <option value="all">All</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="indeed">Indeed</option>
          </select>
          <span className="text-sm text-gray-500">{sortedJobs.length} jobs</span>
        </div>
        <button
          onClick={triggerScrape}
          disabled={scraping}
          className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {scraping ? "Scraping..." : "Scrape Now"}
        </button>
      </div>

      {tracked && (
        <div className="mb-3 bg-green-100 text-green-800 text-sm px-4 py-2 rounded-lg">
          Added "{tracked}" to your application tracker.
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No jobs yet. Click "Scrape Now" to find matches.
        </div>
      ) : (
        <div className="space-y-3">
          {sortedJobs.map((job) => (
            <JobCard key={job.id} job={job} onTrack={trackJob} />
          ))}
        </div>
      )}
    </div>
  );
}
