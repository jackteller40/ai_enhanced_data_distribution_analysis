import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Chat() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [currentProfileId, setCurrentProfileId] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.getProfile()
      .then((data) => setCurrentProfileId(data.profile_id))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.getMessages(conversationId)
      .then((data) => setMessages(data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    if (!content.trim()) return;
    setSending(true);
    try {
      const newMessage = await api.sendMessage(conversationId, { content });
      setMessages((prev) => [...prev, newMessage]);
      setContent("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (loading) return <p className="p-6">Loading...</p>;

  return (
    <div className="flex flex-col h-screen max-w-xl mx-auto">

      <div className="flex items-center gap-4 px-6 py-4 border-b border-gray-200">
        <button onClick={() => navigate("/matches")} className="text-xl bg-transparent border-none cursor-pointer">
          ←
        </button>
        <h2 className="text-lg font-medium m-0">Chat</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-2">
        {error && <p className="text-red-500">{error}</p>}
        {messages.length === 0 && (
          <p className="text-gray-400 text-center">No messages yet. Say hi!</p>
        )}

        {messages.map((msg) => {
          const isMine = msg.sender_id === currentProfileId;
          return (
            <div key={msg.id} className={`flex flex-col max-w-[70%] ${isMine ? "self-end items-end" : "self-start items-start"}`}>
              <div className={`px-4 py-2 text-sm ${isMine ? "bg-blue-500 text-white rounded-t-2xl rounded-bl-2xl rounded-br-sm" : "bg-gray-100 text-black rounded-t-2xl rounded-br-2xl rounded-bl-sm"}`}>
                {msg.content}
              </div>
              <p className="text-xs text-gray-400 mt-1 mx-1">
                {new Date(msg.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSend} className="flex gap-3 px-6 py-3 border-t border-gray-200">
        <input
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Message..."
          disabled={sending}
          className="flex-1 px-4 py-2 text-sm rounded-full border border-gray-300 outline-none"
        />
        <button
          type="submit"
          disabled={sending || !content.trim()}
          className="px-5 py-2 text-sm rounded-full bg-blue-500 text-white border-none cursor-pointer disabled:opacity-50"
        >
          {sending ? "..." : "Send"}
        </button>
      </form>

    </div>
  );
}