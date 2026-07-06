import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/chat/history`)
      .then((r) => r.json())
      .then(setMessages)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    await fetch(`${API}/api/chat`, { method: "DELETE" });
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-180px)]">
      <div className="flex justify-between items-center mb-3">
        <p className="text-sm text-gray-500">
          Ask me about job strategy, interview prep, how to position your experience, or paste a job description for feedback.
        </p>
        <button onClick={clearChat} className="text-xs text-red-400 hover:text-red-600">
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <p className="text-lg mb-2">Hi Sam! I'm here to help with your job search.</p>
            <p className="text-sm">Try asking: "What roles should I prioritize?" or paste a job description for feedback.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-100 text-gray-800 rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-400 px-4 py-3 rounded-2xl rounded-bl-sm text-sm">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask anything about your job search..."
          className="flex-1 border border-gray-300 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="bg-indigo-600 text-white px-5 py-2 rounded-xl text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
