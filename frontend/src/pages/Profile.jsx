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
    display_name: "",
    major: "",
    graduation_year: "",
    bio: "",
    favorite_bar: "",
    likes_going_out: "",
    smokes: "",
    nicotine_lover: "",
    height: "",
    gender: "",
    looking_for: [],
    romantically_searching_for: "",
    clubs: "",
    varsity_sports: "",
    interests: "",
  });

  useEffect(() => {
    api.getProfile()
      .then((data) => {
        if (data) {
          setForm({
            display_name: data.display_name || "",
            major: data.major || "",
            graduation_year: data.graduation_year || "",
            bio: data.bio || "",
            favorite_bar: data.favorite_bar || "",
            likes_going_out: data.likes_going_out === null ? "" : String(data.likes_going_out),
            smokes: data.smokes === null ? "" : String(data.smokes),
            nicotine_lover: data.nicotine_lover === null ? "" : String(data.nicotine_lover),
            height: data.height || "",
            gender: data.gender || "",
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
      if (current.includes(value)) {
        return { ...prev, looking_for: current.filter((v) => v !== value) };
      } else {
        return { ...prev, looking_for: [...current, value] };
      }
    });
  }

  function parseArray(str) {
    return str.split(",").map((s) => s.trim()).filter(Boolean);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);
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

  if (loading) return <p style={{ padding: 24 }}>Loading...</p>;

  const inputStyle = { width: "100%", padding: "8px 12px", fontSize: 16, boxSizing: "border-box" };
  const labelStyle = { display: "block", marginBottom: 6, fontWeight: 500 };
  const fieldStyle = { marginBottom: 20 };

  return (
    <div style={{ maxWidth: 520, margin: "40px auto", padding: "0 24px" }}>
      <h1 style={{ marginBottom: 24 }}>Your profile</h1>

      {error && <p style={{ color: "red", marginBottom: 16 }}>{error}</p>}
      {success && <p style={{ color: "green", marginBottom: 16 }}>Saved! Redirecting...</p>}

      <form onSubmit={handleSubmit}>

        <div style={fieldStyle}>
          <label style={labelStyle}>Display name *</label>
          <input name="display_name" value={form.display_name} onChange={handleChange} required style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Major</label>
          <input name="major" value={form.major} onChange={handleChange} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Graduation year</label>
          <input name="graduation_year" type="number" value={form.graduation_year} onChange={handleChange} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Bio</label>
          <textarea name="bio" value={form.bio} onChange={handleChange} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Favorite bar</label>
          <input name="favorite_bar" value={form.favorite_bar} onChange={handleChange} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Height (inches)</label>
          <input name="height" type="number" value={form.height} onChange={handleChange} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Gender</label>
          <select name="gender" value={form.gender} onChange={handleChange} style={inputStyle}>
            <option value="">Select...</option>
            {GENDER_OPTIONS.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Likes going out</label>
          <select name="likes_going_out" value={form.likes_going_out} onChange={handleChange} style={inputStyle}>
            <option value="">Select...</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Smokes</label>
          <select name="smokes" value={form.smokes} onChange={handleChange} style={inputStyle}>
            <option value="">Select...</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Nicotine lover</label>
          <select name="nicotine_lover" value={form.nicotine_lover} onChange={handleChange} style={inputStyle}>
            <option value="">Select...</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Looking for</label>
          <div style={{ display: "flex", gap: 16 }}>
            {LOOKING_FOR_OPTIONS.map((opt) => (
              <label key={opt} style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 400 }}>
                <input
                  type="checkbox"
                  checked={form.looking_for.includes(opt)}
                  onChange={() => toggleLookingFor(opt)}
                />
                {opt}
              </label>
            ))}
          </div>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Romantically searching for</label>
          <select name="romantically_searching_for" value={form.romantically_searching_for} onChange={handleChange} style={inputStyle}>
            <option value="">Select...</option>
            {SEARCHING_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Clubs (comma separated)</label>
          <input name="clubs" value={form.clubs} onChange={handleChange} placeholder="e.g. Chess Club, Coding Club" style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Varsity sports (comma separated)</label>
          <input name="varsity_sports" value={form.varsity_sports} onChange={handleChange} placeholder="e.g. Soccer, Basketball" style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Interests (comma separated)</label>
          <input name="interests" value={form.interests} onChange={handleChange} placeholder="e.g. Hiking, Music, Gaming" style={inputStyle} />
        </div>

        <button
          type="submit"
          disabled={saving}
          style={{ width: "100%", padding: "10px", fontSize: 16, cursor: "pointer", marginBottom: 40 }}
        >
          {saving ? "Saving..." : "Save profile"}
        </button>

      </form>
    </div>
  );
}