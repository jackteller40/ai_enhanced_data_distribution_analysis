import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Profile from "./pages/Profile";
import Queue from "./pages/Queue";
import Matches from "./pages/Matches";
import Chat from "./pages/Chat";

function ProtectedRoute({ token, children }) {
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("jwt_token") || null);

  function handleLogin(newToken) {
    localStorage.setItem("jwt_token", newToken);
    setToken(newToken);
  }

  function handleLogout() {
    localStorage.removeItem("jwt_token");
    setToken(null);
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login onLogin={handleLogin} />} />
        <Route path="/signup" element={<Signup onLogin={handleLogin} />} />

        <Route
          path="/profile"
          element={
            <ProtectedRoute token={token}>
              <Profile onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/queue"
          element={
            <ProtectedRoute token={token}>
              <Queue onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/matches"
          element={
            <ProtectedRoute token={token}>
              <Matches onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat/:conversationId"
          element={
            <ProtectedRoute token={token}>
              <Chat onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />

        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}