import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Matches({ onLogout }) {
  const navigate = useNavigate();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getMatches()
      .then((data) => setMatches(data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="p-6">Loading...</p>;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      <header className="bg-white shadow-sm px-6 py-4 flex justify-between items-center sticky top-0 z-10">
        <h1 className="text-2xl font-extrabold text-blue-600 tracking-tight">Matches</h1>
        <div className="flex items-center gap-6">
          <button
            onClick={() => navigate("/queue")}
            className="text-sm font-semibold text-gray-600 hover:text-blue-600 transition-colors"
          >
            Queue
          </button>
          <button 
                onClick={() => navigate('/profile')}
                className="text-sm font-semibold text-gray-600 hover:text-blue-600 transition-colors"
                >
                Edit Profile
                </button>
          <button
            onClick={onLogout}
            className="text-sm font-semibold text-gray-400 hover:text-red-500 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-xl mx-auto w-full px-4 py-6">

        {error && (
          <p className="text-red-500 text-center">{error}</p>
        )}

        {!loading && matches.length === 0 && !error && (
          <div className="text-center p-8 bg-white rounded-3xl shadow-sm border border-gray-100">
            <div className="text-4xl mb-4">💫</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">No matches yet</h2>
            <p className="text-gray-500 mb-6">Head to the queue to start connecting.</p>
            <button
              onClick={() => navigate("/queue")}
              className="px-6 py-2 bg-blue-600 text-white rounded-full font-semibold hover:bg-blue-700 transition-colors"
            >
              Go to queue
            </button>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {matches.map((match) => (
            <button
              key={match.match_id}
              onClick={() => navigate(`/chat/${match.conversation_id}`)}
              className="flex items-center gap-4 bg-white px-5 py-4 rounded-2xl shadow-sm border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all text-left w-full"
            >
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-lg flex-shrink-0">
                {match.other_display_name?.[0]?.toUpperCase() || "?"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 truncate">{match.other_display_name}</p>
                <p className="text-sm text-gray-400 capitalize">{match.match_type} match</p>
              </div>
              <span className="text-gray-300 text-xl">›</span>
            </button>
          ))}
        </div>

      </main>
    </div>
  );
}