import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const GENDER_OPTIONS = ["woman", "man", "nonbinary", "queer/other"];
const LOOKING_FOR_OPTIONS = ["romantic", "roommate"];
const SEARCHING_OPTIONS = ["something serious", "open for anything", "short-term fun"];

export default function Profile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    display_name: "", major: "", graduation_year: "", bio: "",
    favorite_bar: "", likes_going_out: "", smokes: "", nicotine_lover: "",
    height: "", gender: "", looking_for: [], romantically_searching_for: "",
    clubs: "", varsity_sports: "", interests: "",
  });

  useEffect(() => {
    api.getProfile()
      .then((data) => {
        if (data) {
          setForm({
            display_name: data.display_name || "", major: data.major || "",
            graduation_year: data.graduation_year || "", bio: data.bio || "",
            favorite_bar: data.favorite_bar || "",
            likes_going_out: data.likes_going_out === null ? "" : String(data.likes_going_out),
            smokes: data.smokes === null ? "" : String(data.smokes),
            nicotine_lover: data.nicotine_lover === null ? "" : String(data.nicotine_lover),
            height: data.height || "", gender: data.gender || "",
            looking_for: data.looking_for || [],
            romantically_searching_for: data.romantically_searching_for || "",
            clubs: (data.clubs || []).join(", "),
            varsity_sports: (data.varsity_sports || []).join(", "),
            interests: (data.interests || []).join(", "),
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function toggleLookingFor(value) {
    setForm((prev) => {
      const current = prev.looking_for;
      return current.includes(value)
        ? { ...prev, looking_for: current.filter((v) => v !== value) }
        : { ...prev, looking_for: [...current, value] };
    });
  }

  function parseArray(str) {
    return str.split(",").map((s) => s.trim()).filter(Boolean);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null); setSuccess(false); setSaving(true);
    try {
      const payload = {
        display_name: form.display_name,
        major: form.major || null,
        graduation_year: form.graduation_year ? parseInt(form.graduation_year) : null,
        bio: form.bio || null,
        favorite_bar: form.favorite_bar || null,
        likes_going_out: form.likes_going_out === "" ? null : form.likes_going_out === "true",
        smokes: form.smokes === "" ? null : form.smokes === "true",
        nicotine_lover: form.nicotine_lover === "" ? null : form.nicotine_lover === "true",
        height: form.height ? parseInt(form.height) : null,
        gender: form.gender || null,
        looking_for: form.looking_for,
        romantically_searching_for: form.romantically_searching_for || null,
        clubs: parseArray(form.clubs),
        varsity_sports: parseArray(form.varsity_sports),
        interests: parseArray(form.interests),
      };
      await api.updateProfile(payload);
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
  const MARIST_MAJORS = [
  "Accounting", "American Studies", "Applied Mathematics", "Athletic Training", 
  "Biochemistry", "Biology", "Biomedical Sciences", "Business Administration", 
  "Chemistry", "Communication", "Computer Science", "Conservation Studies", 
  "Crime and Justice Studies", "Cybersecurity", "Data Science and Analytics", 
  "Digital Media", "Economics", "English", "Environmental Earth Science", 
  "Environmental Science", "Environmental Studies", "Fashion Design", 
  "Fashion Merchandising", "Finance", "Fine Arts", "French", 
  "Games and Emerging Media", "Global Marketing Communication", "Global Studies", 
  "History", "Information Technology and Systems", "Interior Design", "Italian", 
  "Mathematics", "Media Studies and Production", "Medical Laboratory Science", 
  "Philosophy", "Political Science", "Professional Studies", "Psychology", 
  "Religious Studies", "Social Work", "Spanish", "Studio Art"
  ];

// 2. Generate the year range
  const GRAD_YEARS = Array.from({ length: 2035 - 1960 + 1 }, (_, i) => 1960 + i).reverse();
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h1 className="text-xl font-bold text-gray-900">Your Profile</h1>
          <button onClick={() => navigate('/queue')} className="text-sm font-semibold text-gray-500 hover:text-gray-900">
            Cancel
          </button>
        </div>

        <div className="p-6 md:p-8">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-6 text-sm font-medium">{error}</div>}
          {success && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-6 text-sm font-medium">Saved! Redirecting...</div>}

          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Display Name */}
            <div>
              <label className={labelClass}>Display name *</label>
              <input name="display_name" value={form.display_name} onChange={handleChange} required className={inputClass} placeholder="What should people call you?" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  
            {/* Multi-Select Major */}
            <div>
              <label className={labelClass}>Majors (Select all that apply)</label>
              <select
                multiple
                name="major"
                value={form.major ? form.major.split(", ") : []}
                onChange={(e) => {
                  const options = [...e.target.selectedOptions];
                  const values = options.map(opt => opt.value);
                  setForm(prev => ({ ...prev, major: values.join(", ") }));
                }}
                className={`${inputClass} h-40 overflow-y-auto`}
              >
                {MARIST_MAJORS.map((m) => (
                  <option key={m} value={m} className="p-1">{m}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">Hold Ctrl (Cmd) to select multiple</p>
            </div>

            {/* Scrollable Grad Year */}
            <div>
              <label className={labelClass}>Graduation Year</label>
              <select 
                name="graduation_year" 
                value={form.graduation_year || "2026"} 
                onChange={handleChange}
                className={inputClass}
              >
                {GRAD_YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
              </div>
            </div>

            {/* Bio */}
            <div>
              <label className={labelClass}>Bio</label>
              <textarea name="bio" value={form.bio} onChange={handleChange} rows={3} className={`${inputClass} resize-none`} placeholder="A little about yourself..." />
            </div>

            {/* Height & Gender Side-by-Side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Height (inches)</label>
                <input name="height" type="number" value={form.height} onChange={handleChange} className={inputClass} placeholder="68" />
              </div>
              <div>
                <label className={labelClass}>Gender</label>
                <select name="gender" value={form.gender} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  {GENDER_OPTIONS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
            </div>

            {/* Lifestyle Dropdowns */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-gray-100 pt-6">
              <div>
                <label className={labelClass}>Likes going out</label>
                <select name="likes_going_out" value={form.likes_going_out} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Smokes</label>
                <select name="smokes" value={form.smokes} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Nicotine lover</label>
                <select name="nicotine_lover" value={form.nicotine_lover} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
            </div>

            <div className="border-t border-gray-100 pt-6">
              <label className={labelClass}>Favorite bar</label>
              <input name="favorite_bar" value={form.favorite_bar} onChange={handleChange} className={inputClass} placeholder="Mahoney's, River Station, etc." />
            </div>

            {/* Arrays (Comma Separated) */}
            <div className="space-y-4">
              <div>
                <label className={labelClass}>Clubs (comma separated)</label>
                <input name="clubs" value={form.clubs} onChange={handleChange} placeholder="e.g. Chess Club, Coding Club" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Varsity sports (comma separated)</label>
                <input name="varsity_sports" value={form.varsity_sports} onChange={handleChange} placeholder="e.g. Soccer, Basketball" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Interests (comma separated)</label>
                <input name="interests" value={form.interests} onChange={handleChange} placeholder="e.g. Hiking, Music, Gaming" className={inputClass} />
              </div>
            </div>

            {/* Preferences */}
            <div className="bg-blue-50/50 p-6 rounded-2xl border border-blue-100 space-y-4 mt-6">
              <h3 className="font-bold text-blue-900 mb-2">Matching Preferences</h3>
              <div>
                <label className={labelClass}>Looking for</label>
                <div className="flex gap-6 mt-2">
                  {LOOKING_FOR_OPTIONS.map((opt) => (
                    <label key={opt} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={form.looking_for.includes(opt)} onChange={() => toggleLookingFor(opt)} className="w-4 h-4 text-blue-600 rounded" />
                      <span className="text-sm font-medium text-gray-700 capitalize">{opt}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className={labelClass}>Romantically searching for</label>
                <select name="romantically_searching_for" value={form.romantically_searching_for} onChange={handleChange} className={inputClass}>
                  <option value="">Select...</option>
                  {SEARCHING_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <button type="submit" disabled={saving} className="w-full bg-blue-600 text-white font-bold py-4 rounded-xl hover:bg-blue-700 disabled:bg-blue-300 transition-colors shadow-sm mt-8">
              {saving ? "Saving..." : "Save Profile"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}