import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000";

const SOURCE_STYLE = {
  greenhouse:       { bg: "bg-emerald-100", text: "text-emerald-700", label: "Greenhouse" },
  lever:            { bg: "bg-sky-100",     text: "text-sky-700",     label: "Lever" },
  linkedin:         { bg: "bg-blue-100",    text: "text-blue-700",    label: "LinkedIn" },
  efinancialcareers:{ bg: "bg-violet-100",  text: "text-violet-700",  label: "eFinancial" },
  wellfound:        { bg: "bg-orange-100",  text: "text-orange-700",  label: "Wellfound" },
  builtin:          { bg: "bg-pink-100",    text: "text-pink-700",    label: "Built In" },
  indeed:           { bg: "bg-yellow-100",  text: "text-yellow-700",  label: "Indeed" },
};

const TYPE_STYLE = {
  pe:        { color: "bg-indigo-50 text-indigo-700 border border-indigo-200", label: "Private Equity" },
  vc:        { color: "bg-purple-50 text-purple-700 border border-purple-200", label: "Venture Capital" },
  real_estate:{ color: "bg-amber-50 text-amber-700 border border-amber-200",  label: "Real Estate" },
  climate:   { color: "bg-green-50 text-green-700 border border-green-200",   label: "Climate" },
  asset_mgmt:{ color: "bg-blue-50 text-blue-700 border border-blue-200",      label: "Asset Mgmt" },
  wealth:    { color: "bg-rose-50 text-rose-700 border border-rose-200",      label: "Wealth" },
  fintech:   { color: "bg-cyan-50 text-cyan-700 border border-cyan-200",      label: "Fintech" },
  other:     { color: "bg-gray-50 text-gray-600 border border-gray-200",      label: "Other" },
};

const SCORE_COLOR = (s) =>
  s >= 8 ? "bg-green-500 text-white" :
  s >= 6 ? "bg-lime-500 text-white" :
  s >= 4 ? "bg-yellow-400 text-gray-900" :
           "bg-red-400 text-white";

function Badge({ children, className }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

function JobCard({ job, onTrack, onDismiss }) {
  const [expanded, setExpanded] = useState(false);
  const [tailoring, setTailoring] = useState(false);
  const [tailored, setTailored] = useState(null);

  const src = SOURCE_STYLE[job.source] || { bg: "bg-gray-100", text: "text-gray-600", label: job.source };
  const typ = TYPE_STYLE[job.company_type] || TYPE_STYLE.other;

  const handleTailor = async () => {
    setTailoring(true);
    try {
      const r = await fetch(`${API}/api/jobs/${job.id}/tailor`, { method: "POST" });
      setTailored(await r.json());
    } finally {
      setTailoring(false);
    }
  };

  return (
    <div className={`bg-white rounded-2xl border shadow-sm hover:shadow-md transition-all duration-150 overflow-hidden ${job.is_new ? "border-indigo-300 ring-1 ring-indigo-200" : "border-gray-200"}`}>
      <div className="p-5">
        <div className="flex items-start gap-3">
          {/* Score */}
          <div className={`flex-shrink-0 w-12 h-12 rounded-xl flex flex-col items-center justify-center font-bold ${SCORE_COLOR(job.fit_score)}`}>
            <span className="text-lg leading-tight">{job.fit_score?.toFixed(0)}</span>
            <span className="text-xs opacity-80">/10</span>
          </div>

          {/* Main info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-gray-900 leading-snug">{job.title}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{job.company} &middot; {job.location}</p>
              </div>
              {job.is_new && (
                <span className="flex-shrink-0 bg-indigo-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">NEW</span>
              )}
            </div>

            {/* Badges */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              <Badge className={`${src.bg} ${src.text}`}>{src.label}</Badge>
              {job.company_type && <Badge className={typ.color}>{typ.label}</Badge>}
              {job.seniority && <Badge className="bg-gray-100 text-gray-600">{job.seniority}</Badge>}
              {job.salary_range && <Badge className="bg-green-100 text-green-700">{job.salary_range}</Badge>}
            </div>

            {/* AI summary */}
            {job.fit_summary && (
              <p className="mt-2 text-sm text-gray-500 italic leading-relaxed">{job.fit_summary}</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-100">
          <button onClick={() => setExpanded(!expanded)} className="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            {expanded ? "Hide description" : "Show description"}
          </button>
          <button
            onClick={handleTailor}
            disabled={tailoring}
            className="text-sm bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium"
          >
            {tailoring ? "Writing..." : "Tailor for me"}
          </button>
          <button
            onClick={() => onTrack(job)}
            className="text-sm bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700 font-medium"
          >
            Track
          </button>
          {job.apply_url && (
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm bg-gray-900 text-white px-3 py-1 rounded-lg hover:bg-gray-700 font-medium"
            >
              Apply →
            </a>
          )}
          <button
            onClick={() => onDismiss(job.id)}
            className="text-sm text-gray-400 hover:text-red-500 ml-auto"
          >
            Dismiss
          </button>
        </div>
      </div>

      {/* Description */}
      {expanded && (
        <div className="px-5 pb-4">
          <div className="bg-gray-50 rounded-xl p-4 text-xs text-gray-600 max-h-52 overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {job.description}
          </div>
        </div>
      )}

      {/* Tailored output */}
      {tailored && (
        <div className="px-5 pb-5 space-y-3">
          <div className="bg-indigo-50 rounded-xl p-4">
            <p className="text-xs font-semibold text-indigo-800 mb-2 uppercase tracking-wide">Tailored Resume Bullets</p>
            <pre className="text-xs text-indigo-700 whitespace-pre-wrap leading-relaxed">{tailored.tailored_bullets}</pre>
          </div>
          {tailored.cover_letter && (
            <div className="bg-emerald-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-emerald-800 mb-2 uppercase tracking-wide">Cover Letter</p>
              <pre className="text-xs text-emerald-700 whitespace-pre-wrap leading-relaxed">{tailored.cover_letter}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function JobFeed() {
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState("");
  const [toast, setToast] = useState("");

  // Filters
  const [minScore, setMinScore] = useState(0);
  const [sortBy, setSortBy] = useState("score");
  const [filterSource, setFilterSource] = useState("all");
  const [filterType, setFilterType] = useState("all");
  const [filterSeniority, setFilterSeniority] = useState("all");
  const [showNew, setShowNew] = useState(false);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ min_score: minScore });
      if (filterSource !== "all") params.set("source", filterSource);
      if (filterType !== "all") params.set("company_type", filterType);
      if (filterSeniority !== "all") params.set("seniority", filterSeniority);
      const [jobsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/jobs?${params}`),
        fetch(`${API}/api/jobs/stats/summary`),
      ]);
      const jobsData = await jobsRes.json();
      setJobs(Array.isArray(jobsData) ? jobsData : []);
      if (statsRes.ok) setStats(await statsRes.json());
    } finally {
      setLoading(false);
    }
  }, [minScore, filterSource, filterType, filterSeniority]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const triggerScrape = async () => {
    setScraping(true);
    setScrapeMsg("Searching LinkedIn, eFinancialCareers, Greenhouse, Lever, Wellfound, Indeed…");
    await fetch(`${API}/api/jobs/scrape`, { method: "POST" });
    const before = jobs.length;
    const poll = setInterval(async () => {
      const r = await fetch(`${API}/api/jobs?min_score=${minScore}`);
      const data = await r.json();
      if (data.length > before) {
        setJobs(data);
        setScraping(false);
        setScrapeMsg("");
        clearInterval(poll);
        showToast(`Found ${data.length - before} new jobs!`);
      }
    }, 6000);
    setTimeout(() => { setScraping(false); setScrapeMsg(""); clearInterval(poll); fetchJobs(); }, 150000);
  };

  const trackJob = async (job) => {
    await fetch(`${API}/api/applications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: job.id, company: job.company, title: job.title, apply_url: job.apply_url, status: "applied" }),
    });
    showToast(`"${job.title}" added to tracker`);
  };

  const dismissJob = async (id) => {
    await fetch(`${API}/api/jobs/${id}/seen`, { method: "PATCH" });
    await fetch(`${API}/api/jobs/${id}`, { method: "DELETE" });
    setJobs(prev => prev.filter(j => j.id !== id));
  };

  const sorted = [...jobs]
    .filter(j => !showNew || j.is_new)
    .sort((a, b) => {
      if (sortBy === "score") return (b.fit_score || 0) - (a.fit_score || 0);
      if (sortBy === "date") return new Date(b.scraped_at) - new Date(a.scraped_at);
      if (sortBy === "company") return a.company.localeCompare(b.company);
      return 0;
    });

  const newCount = jobs.filter(j => j.is_new).length;

  return (
    <div>
      {/* Stats bar */}
      {stats && (
        <div className="flex flex-wrap gap-2 mb-4 text-xs text-gray-500">
          <span className="font-medium text-gray-700">{stats.total} total jobs</span>
          {newCount > 0 && <span className="text-indigo-600 font-semibold">{newCount} new</span>}
          {Object.entries(stats.by_source || {}).map(([src, n]) => (
            <span key={src}>{SOURCE_STYLE[src]?.label || src}: {n}</span>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-2xl p-4 mb-4 flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-600">Min score</label>
          <select value={minScore} onChange={e => setMinScore(Number(e.target.value))} className="text-sm border border-gray-300 rounded-lg px-2 py-1">
            {[0,3,5,6,7,8].map(v => <option key={v} value={v}>{v}+</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-600">Sort</label>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-2 py-1">
            <option value="score">Best fit</option>
            <option value="date">Newest</option>
            <option value="company">Company</option>
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-600">Source</label>
          <select value={filterSource} onChange={e => setFilterSource(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-2 py-1">
            <option value="all">All sources</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="linkedin">LinkedIn</option>
            <option value="efinancialcareers">eFinancial</option>
            <option value="wellfound">Wellfound</option>
            <option value="builtin">Built In</option>
            <option value="indeed">Indeed</option>
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-600">Industry</label>
          <select value={filterType} onChange={e => setFilterType(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-2 py-1">
            <option value="all">All types</option>
            <option value="pe">Private Equity</option>
            <option value="vc">Venture Capital</option>
            <option value="real_estate">Real Estate</option>
            <option value="climate">Climate</option>
            <option value="asset_mgmt">Asset Mgmt</option>
            <option value="wealth">Wealth</option>
            <option value="fintech">Fintech</option>
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-600">Level</label>
          <select value={filterSeniority} onChange={e => setFilterSeniority(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-2 py-1">
            <option value="all">All levels</option>
            <option value="entry">Entry</option>
            <option value="associate">Associate</option>
            <option value="manager">Manager</option>
          </select>
        </div>
        <label className="flex items-center gap-1.5 cursor-pointer ml-auto">
          <input type="checkbox" checked={showNew} onChange={e => setShowNew(e.target.checked)} className="rounded" />
          <span className="text-xs font-medium text-gray-600">New only</span>
        </label>
        <span className="text-xs text-gray-400">{sorted.length} showing</span>
        <button
          onClick={triggerScrape}
          disabled={scraping}
          className="ml-auto bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition-colors"
        >
          {scraping ? "Searching…" : "Search Now"}
        </button>
      </div>

      {/* Scrape progress */}
      {scraping && scrapeMsg && (
        <div className="mb-4 bg-indigo-50 border border-indigo-200 rounded-xl px-4 py-3 text-sm text-indigo-700 flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
          {scrapeMsg}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="mb-3 bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-2 rounded-xl">{toast}</div>
      )}

      {/* Job list */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading…</div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No jobs yet.</p>
          <p className="text-sm">Hit "Search Now" to scrape LinkedIn, eFinancialCareers, Greenhouse, Lever, Wellfound, and more.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map(job => (
            <JobCard key={job.id} job={job} onTrack={trackJob} onDismiss={dismissJob} />
          ))}
        </div>
      )}
    </div>
  );
}
