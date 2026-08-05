import { KeyRound, Lock, LogIn, User } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import logo from "@/assets/logo.jpg";
import {
  MfaInvalidError,
  MfaRequiredError,
  useAuth,
} from "@/auth/AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [mfaStep, setMfaStep] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return (
      <Navigate
        to={user.must_change_password ? "/changer-mot-de-passe" : "/"}
        replace
      />
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(
        username,
        password,
        mfaStep ? otp : undefined,
      );
      navigate(
        result.mustChangePassword ? "/changer-mot-de-passe" : "/",
        { replace: true },
      );
    } catch (err) {
      if (err instanceof MfaRequiredError) {
        setMfaStep(true);
        setError(null);
      } else if (err instanceof MfaInvalidError) {
        setError("Code MFA invalide.");
      } else {
        setError("Identifiants invalides.");
        setMfaStep(false);
        setOtp("");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <img src={logo} alt="Thuin Tech" />
          <h1>FIN_FLOW</h1>
          <p>Gestion des dossiers de crédit — Thuin Tech</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          {!mfaStep ? (
            <>
              <label className="field">
                <span>Identifiant</span>
                <div className="input-icon">
                  <User />
                  <input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="votre identifiant"
                    autoFocus
                    required
                  />
                </div>
              </label>
              <label className="field">
                <span>Mot de passe</span>
                <div className="input-icon">
                  <Lock />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>
              </label>
            </>
          ) : (
            <label className="field">
              <span>Code MFA (application d’authentification)</span>
              <div className="input-icon">
                <KeyRound />
                <input
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="123456"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                />
              </div>
            </label>
          )}
          {error && <div className="form-error">{error}</div>}
          <button className="btn btn-primary btn-block" disabled={submitting}>
            <LogIn />
            {submitting
              ? "Connexion…"
              : mfaStep
                ? "Valider le code"
                : "Se connecter"}
          </button>
          {mfaStep && (
            <button
              type="button"
              className="btn btn-ghost btn-block"
              onClick={() => {
                setMfaStep(false);
                setOtp("");
                setError(null);
              }}
            >
              Retour
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
