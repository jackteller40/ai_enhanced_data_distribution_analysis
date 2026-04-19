import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api";

export default function Signup({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.signup({ email, password });
      onLogin(data.access_token);
      navigate("/profile");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", padding: "0 24px" }}>
      <h1 style={{ marginBottom: 24 }}>Create account</h1>

      {error && (
        <p style={{ color: "red", marginBottom: 16 }}>{error}</p>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6 }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: "100%", padding: "8px 12px", fontSize: 16, boxSizing: "border-box" }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", marginBottom: 6 }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: "100%", padding: "8px 12px", fontSize: 16, boxSizing: "border-box" }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{ width: "100%", padding: "10px", fontSize: 16, cursor: "pointer" }}
        >
          {loading ? "Creating account..." : "Sign up"}
        </button>
      </form>

      <p style={{ marginTop: 16, textAlign: "center" }}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}