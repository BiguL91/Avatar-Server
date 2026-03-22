import { useState } from "react";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import "./SettingsPage.css";

interface UserData {
  name: string;
  email: string;
}

interface SettingsPageProps {
  user: UserData;
  onBack: () => void;
  onDataDeleted: () => void;
}

// Anzeigenamen der Sprachen (unabhängig von der aktuellen Sprache)
const LANGUAGE_LABELS: Record<string, string> = {
  de: "Deutsch",
  en: "English",
  fr: "Français",
  es: "Español",
  it: "Italiano",
  nl: "Nederlands",
  pl: "Polski",
  pt: "Português",
};

export function SettingsPage({ user, onBack, onDataDeleted }: SettingsPageProps) {
  const { t, lang, setLang, availableLanguages } = useTranslation();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      const response = await apiFetch("/api/account", { method: "DELETE" });
      if (response.ok) {
        onDataDeleted();
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <button className="settings-header__back" onClick={onBack}>
          &larr; {t("settings.back")}
        </button>
        <h1 className="settings-title">{t("settings.title")}</h1>
      </div>

      {/* Profil */}
      <div className="settings-section">
        <h2 className="settings-section__title">{t("settings.profile.title")}</h2>
        <div className="settings-field">
          <span className="settings-field__label">{t("settings.profile.name")}</span>
          <span className="settings-field__value">{user.name}</span>
        </div>
        <div className="settings-field">
          <span className="settings-field__label">{t("settings.profile.email")}</span>
          <span className="settings-field__value">{user.email}</span>
        </div>
      </div>

      {/* Sprache */}
      <div className="settings-section">
        <h2 className="settings-section__title">{t("settings.language.title")}</h2>
        <div className="settings-language">
          {availableLanguages.map((code) => (
            <button
              key={code}
              className={`settings-language__btn ${lang === code ? "settings-language__btn--active" : ""}`}
              onClick={() => setLang(code)}
            >
              {LANGUAGE_LABELS[code] ?? code.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Gefahrenzone */}
      <div className="settings-section settings-section--danger">
        <h2 className="settings-section__title">{t("settings.danger.title")}</h2>
        <p className="settings-danger__description">{t("settings.danger.description")}</p>
        <button
          className="btn btn--danger"
          onClick={() => setShowDeleteConfirm(true)}
          disabled={isDeleting}
        >
          {t("settings.danger.button")}
        </button>
      </div>

      {/* Bestätigungsdialog */}
      {showDeleteConfirm && (
        <ConfirmDialog
          message={t("settings.danger.confirm")}
          confirmLabel={t("settings.danger.confirm.button")}
          cancelLabel={t("dialog.cancel")}
          onConfirm={handleDeleteAll}
          onCancel={() => setShowDeleteConfirm(false)}
          danger
        />
      )}
    </div>
  );
}
