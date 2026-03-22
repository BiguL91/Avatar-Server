import { useState, useEffect, useCallback } from "react";
import { I18nProvider } from "./i18n/i18n";
import { LoginPage } from "./pages/LoginPage";
import { OidcCallbackPage } from "./pages/OidcCallbackPage";
import { UploadPage } from "./pages/UploadPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AdminPage } from "./pages/AdminPage";
import { Footer } from "./components/Footer";
import { UserMenu } from "./components/UserMenu";
import { ThemeToggle } from "./components/ThemeToggle";
import { apiFetch, clearToken } from "./utils/api";

type Page = "upload" | "settings" | "admin";

interface AppConfig {
  defaultLanguage: string;
  devMode: boolean;
  oidcEnabled: boolean;
  avatarSizes: number[];
}

interface UserData {
  id: number;
  name: string;
  email: string;
  is_admin: boolean;
  avatarUrl: string | null;
}

export function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<UserData | null>(null);
  const [page, setPage] = useState<Page>("upload");
  const [config, setConfig] = useState<AppConfig | null>(null);

  // OIDC-Callback Route erkennen
  const isOidcCallback = window.location.pathname === "/oidc/callback";

  // App-Konfiguration laden (Sprache, Dev-Modus, OIDC) — neu laden bei Login/Logout
  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data) => setConfig(data))
      .catch(() => {});
  }, [isLoggedIn]);

  // User-Daten vom Backend laden (inkl. Avatar-Status)
  const refreshUser = useCallback(async () => {
    try {
      const res = await apiFetch("/api/upload/me");
      if (!res.ok) return;
      const data = await res.json();
      setUser({
        id: data.id,
        name: data.name,
        email: data.email,
        is_admin: data.is_admin ?? false,
        avatarUrl: data.has_avatar
          ? `/avatar/${data.md5}?s=64&v=${Date.now()}`
          : null,
      });
    } catch {
      // Fehler ignorieren
    }
  }, []);

  // Nach Login User-Daten laden
  useEffect(() => {
    if (isLoggedIn) refreshUser();
  }, [isLoggedIn, refreshUser]);

  const handleLogout = async () => {
    // OIDC-Logout: Beim IdP abmelden falls ID-Token vorhanden
    const idToken = sessionStorage.getItem("oidc_id_token");
    if (idToken && config?.oidcEnabled) {
      try {
        const res = await fetch("/api/auth/oidc/logout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token_hint: idToken }),
        });

        if (res.ok) {
          const data = await res.json();
          sessionStorage.removeItem("oidc_id_token");
          clearToken();
          // Redirect zum IdP-Logout
          window.location.href = data.logout_url;
          return;
        }
      } catch {
        // Fallback: Nur lokal ausloggen
      }
    }

    sessionStorage.removeItem("oidc_id_token");
    clearToken();
    setIsLoggedIn(false);
    setUser(null);
    setPage("upload");
  };

  // Nach Datenlöschung: User-Daten neu laden, zur Upload-Seite
  const handleDataDeleted = () => {
    refreshUser();
    setPage("upload");
  };

  return (
    <I18nProvider defaultLang={config?.defaultLanguage || "de"}>
      {/* OIDC-Callback Route */}
      {isOidcCallback ? (
        <>
          <div className="top-bar">
            <ThemeToggle />
          </div>
          <OidcCallbackPage onLogin={() => setIsLoggedIn(true)} />
        </>
      ) : !isLoggedIn ? (
        <>
          <div className="top-bar">
            <ThemeToggle />
          </div>
          <LoginPage onLogin={() => setIsLoggedIn(true)} />
        </>
      ) : (
        <>
          <div className="top-bar">
            <ThemeToggle />
            {user && (
              <UserMenu
                user={user}
                onLogout={handleLogout}
                onSettings={() => setPage("settings")}
                onAdmin={() => setPage("admin")}
              />
            )}
          </div>
          {page === "upload" && (
            <UploadPage onAvatarChange={refreshUser} avatarSizes={config?.avatarSizes} />
          )}
          {page === "settings" && user && (
            <SettingsPage
              user={user}
              onBack={() => setPage("upload")}
              onDataDeleted={handleDataDeleted}
            />
          )}
          {page === "admin" && user && (
            <AdminPage
              onBack={() => setPage("upload")}
              currentUserId={user.id}
            />
          )}
        </>
      )}
      <Footer />
    </I18nProvider>
  );
}
