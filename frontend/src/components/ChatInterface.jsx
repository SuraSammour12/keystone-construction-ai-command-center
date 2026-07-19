import React, { useState, useRef, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your Construction AI Command Center. I can analyze budgets, schedules, risks, draft emails, and manage budget transfers.\n\nTry asking:\n\n- Give me a status report for Alpha Tower\n- Draft an email to the contractor about delays\n- Transfer budget from Beta Mall to Alpha Tower\n- Show me all projects overview",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await axios.post(`${API}/chat`, { message: userMessage });
      const data = res.data;

      let assistantContent = data.response;

      if (data.scores) {
        const scores = Object.entries(data.scores)
          .filter(([_, v]) => v > 0)
          .map(([k, v]) => `${k}: ${v}/10`)
          .join(" | ");
        if (scores) {
          assistantContent += `\n\nQuality Scores: ${scores}`;
        }
      }
      if (data.attempts > 0) {
        assistantContent += `\nAttempts: ${data.attempts}`;
      }
      if (data.requires_approval) {
        assistantContent += `\n\nThis action requires approval. Check the Approvals tab.`;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: assistantContent },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: Could not reach the AI backend. Make sure the Flask server is running on port 5000.",
        },
      ]);
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl flex flex-col h-[70vh] shadow-sm">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-amber-600 text-white"
                  : "bg-gray-100 text-gray-800 border border-gray-200"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-500">
              <span className="animate-pulse">
                Agents are working on your request... This may take 30-60 seconds.
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your projects..."
            rows={1}
            className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-800 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-amber-600 hover:bg-amber-700 disabled:bg-gray-300 disabled:text-gray-500 text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;