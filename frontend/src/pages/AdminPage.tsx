import { useState, useRef, useCallback } from "react";
import { useTranslation } from "../i18n/i18n";
import { AdminUsers } from "../components/AdminUsers";
import { AdminAvatars } from "../components/AdminAvatars";
import { AdminSettings } from "../components/AdminSettings";
import "./AdminPage.css";

interface AdminPageProps {
  onBack: () => void;
  currentUserId: number;
}

type AdminTab = "users" | "avatars" | "settings";

export function AdminPage({ onBack, currentUserId }: AdminPageProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<AdminTab>("users");

  // Toast
  const [toastVisible, setToastVisible] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const showToast = useCallback(() => {
    setToastVisible(true);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastVisible(false), 2000);
  }, []);

  return (
    <div className="admin-page">
      <div className="admin-header">
        <button className="settings-header__back" onClick={onBack}>
          &larr; {t("admin.back")}
        </button>
        <h1 className="admin-title">{t("admin.title")}</h1>
      </div>

      {/* Tab-Navigation */}
      <div className="admin-tabs">
        <button
          className={`admin-tabs__btn ${activeTab === "users" ? "admin-tabs__btn--active" : ""}`}
          onClick={() => setActiveTab("users")}
        >
          {t("admin.users.title")}
        </button>
        <button
          className={`admin-tabs__btn ${activeTab === "avatars" ? "admin-tabs__btn--active" : ""}`}
          onClick={() => setActiveTab("avatars")}
        >
          {t("admin.avatars.title")}
        </button>
        <button
          className={`admin-tabs__btn ${activeTab === "settings" ? "admin-tabs__btn--active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          {t("admin.settings.title")}
        </button>
      </div>

      {/* Tab-Inhalt */}
      {activeTab === "users" && (
        <AdminUsers currentUserId={currentUserId} onSaved={showToast} />
      )}
      {activeTab === "avatars" && (
        <AdminAvatars onSaved={showToast} />
      )}
      {activeTab === "settings" && (
        <AdminSettings onSaved={showToast} />
      )}

      {/* Toast */}
      <div className={`admin-toast ${toastVisible ? "admin-toast--visible" : ""}`}>
        {t("toast.saved")}
      </div>
    </div>
  );
}
