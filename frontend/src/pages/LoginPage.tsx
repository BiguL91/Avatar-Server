import { useState, useEffect } from "react";
import { useTranslation } from "../i18n/i18n";
import { setToken } from "../utils/api";
import logoUrl from "../assets/logo.png";
import "./LoginPage.css";

interface LoginPageProps {
  onLogin: () => void;
}

interface AppConfig {
  appName: string;
  defaultLanguage: string;
  devMode: boolean;
  oidcEnabled: boolean;
  legacyLogin: boolean;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [showLegacy, setShowLegacy] = useState(false);

  // App-Konfiguration laden (Dev-Modus, OIDC erkennen)
  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data) => {
        setConfig(data);
        if (data.appName) document.title = data.appName;
      })
      .catch(() => {});
  }, []);

  // SSO-Login: Redirect zum OIDC-Provider
  const handleSsoLogin = async () => {
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/oidc/authorize");
      if (!res.ok) {
        setError(t("login.sso.error"));
        return;
      }

      const data = await res.json();
      // State in sessionStorage speichern fuer CSRF-Verifizierung
      sessionStorage.setItem("oidc_state", data.state);
      // Redirect zum IdP
      window.location.href = data.auth_url;
    } catch {
      setError(t("login.sso.error"));
    } finally {
      setLoading(false);
    }
  };

  // Dev-Modus: Direkt einloggen ohne Passwort
  const handleDevLogin = () => {
    onLogin();
  };

  // Normaler Login mit Email + Passwort
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        setError(t("login.error"));
        return;
      }

      const data = await res.json();
      setToken(data.token);
      onLogin();
    } catch {
      setError(t("login.error"));
    } finally {
      setLoading(false);
    }
  };

  // OIDC aktiv: SSO-Button prominent, Legacy-Login aufklappbar
  const oidcEnabled = config?.oidcEnabled ?? false;
  const legacyLogin = config?.legacyLogin ?? true;

  // Config noch nicht geladen: nur Logo + Titel zeigen (verhindert Flash)
  if (!config) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-logo">
            <img src={logoUrl} alt="Avatar Server" className="login-logo__img" />
          </div>
          <h1 className="login-title">{t("login.title")}</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <img src={logoUrl} alt="Avatar Server" className="login-logo__img" />
        </div>
        <h1 className="login-title">{config.appName || t("login.title")}</h1>

        {/* SSO-Login (wenn OIDC aktiv) */}
        {oidcEnabled && (
          <>
            <button
              className="btn btn--primary login-btn login-btn--sso"
              onClick={handleSsoLogin}
              disabled={loading}
            >
              {t("login.sso")}
            </button>

            {error && !showLegacy && <p className="login-error">{error}</p>}

            {/* Legacy-Login aufklappen (nur wenn Legacy aktiviert) */}
            {legacyLogin && (
              <>
                <div className="login-divider">
                  <span>{t("login.legacy.divider")}</span>
                </div>
                <button
                  className="btn login-btn login-btn--legacy"
                  onClick={() => setShowLegacy(!showLegacy)}
                >
                  {t("login.legacy")}
                </button>
              </>
            )}
          </>
        )}

        {/* Login-Formular (immer sichtbar wenn kein OIDC, sonst aufklappbar) */}
        {legacyLogin && (!oidcEnabled || showLegacy) && (
          <form className="login-form" onSubmit={handleSubmit}>
            <input
              className="login-input"
              type="email"
              placeholder={t("login.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              className="login-input"
              type="password"
              placeholder={t("login.password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && (showLegacy || !oidcEnabled) && <p className="login-error">{error}</p>}
            <button className="btn btn--primary login-btn" type="submit" disabled={loading}>
              {t("login.submit")}
            </button>
          </form>
        )}

        {/* Dev-Modus Button */}
        {config?.devMode && (
          <>
            <div className="login-divider">
              <span>{t("login.dev")}</span>
            </div>
            <button className="btn login-btn login-btn--dev" onClick={handleDevLogin}>
              Dev Login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
