import { useEffect, useState } from "react";
import { useTranslation } from "../i18n/i18n";
import { setToken } from "../utils/api";
import "./LoginPage.css";

interface OidcCallbackPageProps {
  onLogin: () => void;
}

export function OidcCallbackPage({ onLogin }: OidcCallbackPageProps) {
  const { t } = useTranslation();
  const [error, setError] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const state = params.get("state");

      if (!code || !state) {
        setError(t("login.sso.error"));
        return;
      }

      // State gegen sessionStorage pruefen (CSRF-Schutz)
      const savedState = sessionStorage.getItem("oidc_state");
      if (state !== savedState) {
        setError(t("login.sso.error"));
        return;
      }
      sessionStorage.removeItem("oidc_state");

      try {
        const res = await fetch("/api/auth/oidc/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, state }),
        });

        if (!res.ok) {
          setError(t("login.sso.error"));
          return;
        }

        const data = await res.json();
        setToken(data.token);

        // ID-Token fuer Logout speichern
        if (data.id_token) {
          sessionStorage.setItem("oidc_id_token", data.id_token);
        }

        // URL bereinigen und zur App weiterleiten
        window.history.replaceState({}, "", "/");
        onLogin();
      } catch {
        setError(t("login.sso.error"));
      }
    };

    handleCallback();
  }, []);

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo__placeholder">A</div>
        </div>
        {error ? (
          <>
            <p className="login-error">{error}</p>
            <a href="/" className="btn btn--primary login-btn">
              {t("settings.back")}
            </a>
          </>
        ) : (
          <p className="login-loading">{t("login.sso.loading")}</p>
        )}
      </div>
    </div>
  );
}
