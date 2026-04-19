import { useState, useEffect } from "react";
import { api } from "../api";

export default function Queue({ onLogout }) {
  const [suggestion, setSuggestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // For the demo, we'll default to romantic matching. 
  // You can easily add a toggle button later to switch to 'roommate'
  const [matchType, setMatchType] = useState("romantic");

  // Fetch a new suggestion when the component mounts or matchType changes
  useEffect(() => {
    fetchNextSuggestion();
  }, [matchType]);

  async function fetchNextSuggestion() {
    setLoading(true);
    setError(null);
    setSuggestion(null); // Clear the old card while loading

    try {
      const data = await api.getQueue(matchType);
      // If the backend returns a list, grab the top match.
      if (data && data.length > 0) {
        setSuggestion(data[0]);
      } else {
        setSuggestion(null); // Triggers the "Empty Queue" UI
      }
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to load your queue.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(actionType) {
    if (!suggestion) return;

    // Optimistic UI: Immediately hide the card to make it feel fast
    const currentSuggestionId = suggestion.id;
    setSuggestion(null); 
    setLoading(true);

    try {
      if (actionType === "like") {
        await api.likeSuggestion(currentSuggestionId);
      } else if (actionType === "reject") {
        await api.rejectSuggestion(currentSuggestionId);
      }
      // Immediately fetch the next person in line
      await fetchNextSuggestion();
    } catch (err) {
      console.error(err);
      setError("Failed to register your choice. Please try again.");
      setLoading(false);
    }
  }

  // --- UI Rendering ---

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Simple Header */}
      <header className="bg-white shadow-sm px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-blue-600">MatchApp</h1>
        <button 
          onClick={onLogout}
          className="text-sm font-medium text-gray-500 hover:text-gray-800"
        >
          Sign Out
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        
        {/* Loading State */}
        {loading && !suggestion && !error && (
          <div className="text-gray-500 font-medium animate-pulse text-lg">
            Finding your best matches...
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-xl text-center max-w-sm w-full shadow-sm border border-red-100">
            <p className="mb-4">{error}</p>
            <button 
              onClick={fetchNextSuggestion}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty Queue State */}
        {!loading && !suggestion && !error && (
          <div className="text-center max-w-sm w-full p-8 bg-white rounded-3xl shadow-sm border border-gray-100">
            <div className="text-4xl mb-4">🌟</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">You're all caught up!</h2>
            <p className="text-gray-500">
              Check back later for more {matchType} suggestions.
            </p>
          </div>
        )}

        {/* The Swipe Card */}
        {suggestion && (
          <div className="w-full max-w-sm bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100 flex flex-col">
            
            {/* Photo Section */}
            <div className="relative aspect-[4/5] bg-gray-200">
              <img
                src={suggestion.candidate_profile.photos?.[0] || "https://via.placeholder.com/400x500?text=No+Photo"}
                alt={suggestion.candidate_profile.display_name}
                className="w-full h-full object-cover"
                onError={(e) => { e.target.src = "https://via.placeholder.com/400x500?text=Image+Error"; }}
              />
              {/* Gradient overlay for text readability */}
              <div className="absolute bottom-0 left-0 w-full p-6 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
                <h2 className="text-3xl font-bold text-white leading-tight flex items-end gap-2">
                  {suggestion.candidate_profile.display_name}
                  <span className="text-xl font-normal text-white/80">
                    '{String(suggestion.candidate_profile.graduation_year).slice(-2)}
                  </span>
                </h2>
                <p className="text-white/90 text-lg font-medium mt-1">
                  {suggestion.candidate_profile.major}
                </p>
              </div>
            </div>

            {/* Profile Data Section */}
            <div className="p-6 space-y-5 flex-grow">
              
              {/* LLM Agent Explanation */}
              <div className="bg-blue-50 border border-blue-100 p-4 rounded-xl relative">
                <div className="absolute -top-3 -left-2 text-2xl">✨</div>
                <p className="text-blue-800 text-sm font-medium italic pl-4">
                  "{suggestion.agent_explanation || "Our algorithm thinks you two would hit it off."}"
                </p>
              </div>

              {/* Bio */}
              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">About Me</h3>
                <p className="text-gray-700 text-base leading-relaxed">
                  {suggestion.candidate_profile.bio || "No bio provided."}
                </p>
              </div>

              {/* Tags/Pills */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
                {suggestion.candidate_profile.likes_going_out !== null && (
                  <span className={`text-xs px-3 py-1.5 rounded-full font-semibold ${suggestion.candidate_profile.likes_going_out ? 'bg-purple-100 text-purple-700' : 'bg-teal-100 text-teal-700'}`}>
                    {suggestion.candidate_profile.likes_going_out ? '🎉 Loves going out' : '☕ Prefers staying in'}
                  </span>
                )}
                {suggestion.candidate_profile.clubs?.map((club, index) => (
                  <span key={index} className="bg-gray-100 text-gray-700 text-xs px-3 py-1.5 rounded-full font-semibold">
                    {club}
                  </span>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-4 p-5 bg-gray-50 border-t border-gray-100">
              <button
                onClick={() => handleAction("reject")}
                className="flex items-center justify-center py-3.5 rounded-xl text-red-600 bg-white border border-red-100 hover:bg-red-50 hover:border-red-200 font-bold shadow-sm transition-all active:scale-95"
              >
                Pass
              </button>
              <button
                onClick={() => handleAction("like")}
                className="flex items-center justify-center py-3.5 rounded-xl text-white bg-blue-600 hover:bg-blue-700 font-bold shadow-sm transition-all active:scale-95"
              >
                Connect
              </button>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}