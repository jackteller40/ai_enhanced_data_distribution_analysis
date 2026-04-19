import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const GENDER_OPTIONS = ["woman", "man", "nonbinary", "queer/other"];
const PREF_GENDER_OPTIONS = ["women", "men", "nonbinary/queer identities", "everyone"];
const LOOKING_FOR_OPTIONS = ["romantic", "roommate"];
const SEARCHING_OPTIONS = ["something serious", "open for anything", "short-term fun"];
const SLEEP_OPTIONS = ["early bird", "night owl", "flexible"];
const GUEST_OPTIONS = ["often", "sometimes", "rarely"];

const MARIST_MAJORS = [
  "Accounting", "Biology", "Business Administration", "Communication", 
  "Computer Science", "Criminal Justice", "Economics", "English", 
  "Environmental Science", "Fashion Design", "Fashion Merchandising", 
  "Finance", "History", "Information Technology", "Mathematics", 
  "Political Science", "Psychology", "Social Work", "Spanish", "Studio Art"
];
const GRAD_YEARS = Array.from({ length: 2035 - 1960 + 1 }, (_, i) => 1960 + i).reverse();

export default function Profile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    // Base Profile
    display_name: "", major: "", graduation_year: "2026", bio: "",
    favorite_bar: "", likes_going_out: "", smokes: "", nicotine_lover: "",
    height_ft: "", height_in: "", gender: "", looking_for: [], romantically_searching_for: "",
    clubs: "", varsity_sports: "", interests: "",
    
    // Romantic Prefs
    interested_in_genders: [], min_grad_yr: "", max_grad_yr: "",
    min_preferred_height: "", max_preferred_height: "",
    
    // Roommate Prefs
    roommate_gender_preference: "", sleep_schedule: "",
    cleanliness: "3", noise_tolerance: "3",
    ok_with_pets: "", guests_frequency: "", on_campus: ""
  });

  useEffect(() => {
    Promise.all([
      api.getProfile().catch(() => null),
      api.getRomanticPreferences().catch(() => null),
      api.getRoommatePreferences().catch(() => null),
    ]).then(([profile, romantic, roommate]) => {
      setForm(prev => ({
        ...prev,
        // Base profile
        ...(profile && {
          display_name: profile.display_name || "",
          major: profile.major || "",
          graduation_year: profile.graduation_year || "2026",
          bio: profile.bio || "",
          favorite_bar: profile.favorite_bar || "",
          likes_going_out: profile.likes_going_out === null ? "" : String(profile.likes_going_out),
          smokes: profile.smokes === null ? "" : String(profile.smokes),
          nicotine_lover: profile.nicotine_lover === null ? "" : String(profile.nicotine_lover),
          height_ft: profile.height ? Math.floor(profile.height / 12) : "",
          height_in: profile.height ? profile.height % 12 : "",
          gender: profile.gender || "",
          looking_for: profile.looking_for || [],
          romantically_searching_for: profile.romantically_searching_for || "",
          clubs: (profile.clubs || []).join(", "),
          varsity_sports: (profile.varsity_sports || []).join(", "),
          interests: (profile.interests || []).join(", "),
        }),
        // Romantic prefs
        ...(romantic && {
          interested_in_genders: romantic.interested_in_genders || [],
          min_grad_yr: romantic.min_grad_yr || "",
          max_grad_yr: romantic.max_grad_yr || "",
          min_preferred_height: romantic.min_preferred_height || "",
          max_preferred_height: romantic.max_preferred_height || "",
        }),
        // Roommate prefs
        ...(roommate && {
          roommate_gender_preference: roommate.roommate_gender_preference || "",
          sleep_schedule: roommate.sleep_schedule || "",
          cleanliness: roommate.cleanliness || "3",
          noise_tolerance: roommate.noise_tolerance || "3",
          ok_with_pets: roommate.ok_with_pets === null ? "" : String(roommate.ok_with_pets),
          guests_frequency: roommate.guests_frequency || "",
          on_campus: roommate.on_campus === null ? "" : String(roommate.on_campus),
        }),
      }));
    }).finally(() => setLoading(false));
}, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function toggleArray(field, value) {
    setForm((prev) => {
      const current = prev[field] || [];
      return current.includes(value)
        ? { ...prev, [field]: current.filter((v) => v !== value) }
        : { ...prev, [field]: [...current, value] };
    });
  }

  function parseArray(str) {
    return str.split(",").map((s) => s.trim()).filter(Boolean);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null); setSuccess(false); setSaving(true);
    
    try {
      // 1. Save Base Profile
      const profilePayload = {
        display_name: form.display_name,
        major: form.major || null,
        graduation_year: form.graduation_year ? parseInt(form.graduation_year) : null,
        bio: form.bio || null,
        favorite_bar: form.favorite_bar || null,
        likes_going_out: form.likes_going_out === "" ? null : form.likes_going_out === "true",
        smokes: form.smokes === "" ? null : form.smokes === "true",
        nicotine_lover: form.nicotine_lover === "" ? null : form.nicotine_lover === "true",
        height: (form.height_ft || form.height_in) ? (parseInt(form.height_ft || 0) * 12) + parseInt(form.height_in || 0) : null,
        gender: form.gender || null,
        looking_for: form.looking_for,
        romantically_searching_for: form.romantically_searching_for || null,
        clubs: parseArray(form.clubs),
        varsity_sports: parseArray(form.varsity_sports),
        interests: parseArray(form.interests),
      };

      const promises = [api.updateProfile(profilePayload)];

      // 2. Save Romantic Prefs (if applicable)
      if (form.looking_for.includes("romantic")) {
        promises.push(api.updateRomanticPreferences({
          interested_in_genders: form.interested_in_genders.length ? form.interested_in_genders : null,
          min_grad_yr: form.min_grad_yr ? parseInt(form.min_grad_yr) : null,
          max_grad_yr: form.max_grad_yr ? parseInt(form.max_grad_yr) : null,
          min_preferred_height: form.min_preferred_height ? parseInt(form.min_preferred_height) : null,
          max_preferred_height: form.max_preferred_height ? parseInt(form.max_preferred_height) : null,
        }));
      }

      // 3. Save Roommate Prefs (if applicable)
      if (form.looking_for.includes("roommate")) {
        promises.push(api.updateRoommatePreferences({
          roommate_gender_preference: form.roommate_gender_preference || null,
          sleep_schedule: form.sleep_schedule || null,
          cleanliness: parseInt(form.cleanliness),
          noise_tolerance: parseInt(form.noise_tolerance),
          ok_with_pets: form.ok_with_pets === "" ? null : form.ok_with_pets === "true",
          guests_frequency: form.guests_frequency || null,
          on_campus: form.on_campus === "" ? null : form.on_campus === "true",
        }));
      }

      // Execute all API calls concurrently
      await Promise.all(promises);
      
      setSuccess(true);
      setTimeout(() => navigate("/queue"), 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-center mt-20 text-gray-500 font-medium">Loading your profile...</div>;

  const inputClass = "w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none";
  const labelClass = "block text-sm font-bold text-gray-700 mb-1";
  const sectionHeaderClass = "text-xl font-extrabold text-gray-900 border-b border-gray-100 pb-2 mt-8 mb-4";

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 sticky top-0 z-10">
          <h1 className="text-xl font-bold text-gray-900">Profile & Preferences</h1>
          <button onClick={() => navigate('/queue')} className="text-sm font-semibold text-gray-500 hover:text-gray-900">Cancel</button>
        </div>

        <div className="p-6 md:p-8">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-6 text-sm font-medium">{error}</div>}
          {success && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-6 text-sm font-medium">Saved! Redirecting...</div>}

          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* --- BASE PROFILE --- */}
            <h2 className={sectionHeaderClass}>The Basics</h2>
            
            <div>
              <label className={labelClass}>Display name *</label>
              <input name="display_name" value={form.display_name} onChange={handleChange} required className={inputClass} placeholder="What should people call you?" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Majors (Select all that apply)</label>
                <select multiple name="major" value={form.major ? form.major.split(", ") : []} onChange={(e) => {
                    const values = [...e.target.selectedOptions].map(opt => opt.value);
                    setForm(prev => ({ ...prev, major: values.join(", ") }));
                  }}
                  className={`${inputClass} h-32 overflow-y-auto`}
                >
                  {MARIST_MAJORS.map((m) => <option key={m} value={m} className="p-1">{m}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Graduation Year</label>
                <select name="graduation_year" value={form.graduation_year} onChange={handleChange} className={inputClass}>
                  {GRAD_YEARS.map((year) => <option key={year} value={year}>{year}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Height</label>
                <div className="flex gap-2 items-center">
                  <input name="height_ft" type="number" value={form.height_ft || ""} onChange={handleChange} className={`${inputClass} w-24`} placeholder="5" min="3" max="8" />
                  <span className="text-gray-500 font-medium">ft</span>
                  <input name="height_in" type="number" value={form.height_in || ""} onChange={handleChange} className={`${inputClass} w-24`} placeholder="10" min="0" max="11" />
                  <span className="text-gray-500 font-medium">in</span>
                </div>
              </div>
              <div>
                <label className={labelClass}>Gender</label>
                <select name="gender" value={form.gender} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  {GENDER_OPTIONS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label className={labelClass}>Bio</label>
              <textarea name="bio" value={form.bio} onChange={handleChange} rows={3} className={`${inputClass} resize-none`} placeholder="A little about yourself..." />
            </div>

            {/* --- LIFESTYLE & INTERESTS --- */}
            <h2 className={sectionHeaderClass}>Lifestyle & Interests</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className={labelClass}>Likes going out</label>
                <select name="likes_going_out" value={form.likes_going_out} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option><option value="true">Yes</option><option value="false">No</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Smokes</label>
                <select name="smokes" value={form.smokes} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option><option value="true">Yes</option><option value="false">No</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Nicotine lover</label>
                <select name="nicotine_lover" value={form.nicotine_lover} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option><option value="true">Yes</option><option value="false">No</option>
                </select>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className={labelClass}>Favorite bar</label>
                <input name="favorite_bar" value={form.favorite_bar} onChange={handleChange} className={inputClass} placeholder="Mahoney's, River Station, etc." />
              </div>
              <div>
                <label className={labelClass}>Clubs (comma separated)</label>
                <input name="clubs" value={form.clubs} onChange={handleChange} className={inputClass} placeholder="e.g. Chess Club, Debate Team" />
              </div>
              <div>
                <label className={labelClass}>Interests (comma separated)</label>
                <input name="interests" value={form.interests} onChange={handleChange} className={inputClass} placeholder="e.g. Hiking, Music, Gaming" />
              </div>
            </div>

            {/* --- MATCHING GOALS --- */}
            <h2 className={sectionHeaderClass}>Matching Goals</h2>
            
            <div className="bg-blue-50 p-6 rounded-2xl border border-blue-100">
              <label className="block text-base font-extrabold text-blue-900 mb-3">What are you looking for on Foxi?</label>
              <div className="flex gap-6">
                {LOOKING_FOR_OPTIONS.map((opt) => (
                  <label key={opt} className="flex items-center gap-2 cursor-pointer bg-white px-4 py-2 rounded-lg shadow-sm border border-blue-200">
                    <input type="checkbox" checked={form.looking_for.includes(opt)} onChange={() => toggleArray("looking_for", opt)} className="w-5 h-5 text-blue-600 rounded" />
                    <span className="font-bold text-gray-800 capitalize">{opt}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* --- ROMANTIC PREFS (Conditional) --- */}
            {form.looking_for.includes("romantic") && (
              <div className="bg-pink-50 p-6 rounded-2xl border border-pink-100 space-y-5 animate-fade-in">
                <h3 className="font-extrabold text-pink-900 text-lg">Romantic Preferences</h3>
                
                <div>
                  <label className={labelClass}>Interested in (Select all that apply)</label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {PREF_GENDER_OPTIONS.map((opt) => (
                      <label key={opt} className="flex items-center gap-2">
                        <input type="checkbox" checked={form.interested_in_genders.includes(opt)} onChange={() => toggleArray("interested_in_genders", opt)} className="w-4 h-4 text-pink-600 rounded" />
                        <span className="text-sm font-medium text-gray-800 capitalize">{opt}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className={labelClass}>Relationship style</label>
                  <select name="romantically_searching_for" value={form.romantically_searching_for} onChange={handleChange} className={inputClass}>
                    <option value="">Select...</option>
                    {SEARCHING_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Min Grad Year</label>
                    <input name="min_grad_yr" type="number" value={form.min_grad_yr} onChange={handleChange} className={inputClass} placeholder="2024" />
                  </div>
                  <div>
                    <label className={labelClass}>Max Grad Year</label>
                    <input name="max_grad_yr" type="number" value={form.max_grad_yr} onChange={handleChange} className={inputClass} placeholder="2028" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Min Height (in)</label>
                    <input name="min_preferred_height" type="number" value={form.min_preferred_height} onChange={handleChange} className={inputClass} placeholder="60" />
                  </div>
                  <div>
                    <label className={labelClass}>Max Height (in)</label>
                    <input name="max_preferred_height" type="number" value={form.max_preferred_height} onChange={handleChange} className={inputClass} placeholder="78" />
                  </div>
                </div>
              </div>
            )}

            {/* --- ROOMMATE PREFS (Conditional) --- */}
            {form.looking_for.includes("roommate") && (
              <div className="bg-emerald-50 p-6 rounded-2xl border border-emerald-100 space-y-5 animate-fade-in">
                <h3 className="font-extrabold text-emerald-900 text-lg">Roommate Preferences</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Preferred Roommate Gender</label>
                    <select name="roommate_gender_preference" value={form.roommate_gender_preference} onChange={handleChange} className={inputClass}>
                      <option value="">Select...</option>
                      {PREF_GENDER_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Sleep Schedule</label>
                    <select name="sleep_schedule" value={form.sleep_schedule} onChange={handleChange} className={inputClass}>
                      <option value="">Select...</option>
                      {SLEEP_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Cleanliness (1-Messy, 5-Neat)</label>
                    <input type="range" min="1" max="5" name="cleanliness" value={form.cleanliness} onChange={handleChange} className="w-full mt-2 accent-emerald-600" />
                    <div className="text-center font-bold text-emerald-800">{form.cleanliness}</div>
                  </div>
                  <div>
                    <label className={labelClass}>Noise Tolerance (1-Quiet, 5-Loud)</label>
                    <input type="range" min="1" max="5" name="noise_tolerance" value={form.noise_tolerance} onChange={handleChange} className="w-full mt-2 accent-emerald-600" />
                    <div className="text-center font-bold text-emerald-800">{form.noise_tolerance}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className={labelClass}>Ok with pets?</label>
                    <select name="ok_with_pets" value={form.ok_with_pets} onChange={handleChange} className={inputClass}>
                      <option value="">Select...</option><option value="true">Yes</option><option value="false">No</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Guests Frequency</label>
                    <select name="guests_frequency" value={form.guests_frequency} onChange={handleChange} className={inputClass}>
                      <option value="">Select...</option>
                      {GUEST_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Live on campus?</label>
                    <select name="on_campus" value={form.on_campus} onChange={handleChange} className={inputClass}>
                      <option value="">Select...</option><option value="true">Yes</option><option value="false">No</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <button type="submit" disabled={saving} className="w-full bg-blue-600 text-white font-bold py-4 rounded-xl hover:bg-blue-700 disabled:bg-blue-300 transition-colors shadow-md mt-8 text-lg">
              {saving ? "Saving..." : "Save Profile & Preferences"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}