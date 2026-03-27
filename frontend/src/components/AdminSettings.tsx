import { useState, useCallback, useEffect } from "react";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";

interface AdminSetting {
  key: string;
  value: string;
  source: string;
  type: string;
  updated_at: string | null;
}

interface AdminSettingsProps {
  onSaved: () => void;
}

// Settings nach Gruppen sortieren
const SETTING_GROUPS: Record<string, string[]> = {
  avatar: [
    "avatar_max_uploads", "avatar_cache_max_age", "avatar_upload_max_bytes",
    "avatar_original_max_px", "avatar_default_size", "avatar_max_size", "avatar_sizes",
  ],
  login: [
    "legacy_login", "dev_mode", "trusted_proxy", "allowed_hosts",
    "avatar_access", "avatar_allowed_subnets", "avatar_user_can_publish",
    "base_url", "jwt_secret", "jwt_expire_minutes",
  ],
  oidc: [
    "oidc_enabled", "oidc_discovery_url", "oidc_client_id", "oidc_client_secret",
    "oidc_claim_email", "oidc_claim_name", "oidc_claim_picture", "oidc_claim_picture_png",
    "oidc_claim_groups", "oidc_admin_group", "oidc_sync_picture", "oidc_picture_size",
  ],
  general: ["app_name", "default_language"],
};

export function AdminSettings({ onSaved }: AdminSettingsProps) {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<AdminSetting[]>([]);
  const [editedSettings, setEditedSettings] = useState<Record<string, string>>({});
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [settingsError, setSettingsError] = useState<Record<string, string>>({});

  // OIDC-Gruppe automatisch oeffnen wenn oidc_enabled=true
  const oidcEnabled = settings.find((s) => s.key === "oidc_enabled")?.value?.toLowerCase() === "true";

  const getGroupSettings = (keys: string[]) =>
    keys.map((key) => settings.find((s) => s.key === key)).filter(Boolean) as AdminSetting[];

  const toggleGroup = (group: string) => {
    setOpenGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  const fetchSettings = useCallback(async () => {
    const res = await apiFetch("/api/admin/settings");
    if (res.ok) {
      const data = await res.json();
      setSettings(data.settings);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Setting speichern
  const handleSaveSetting = async (key: string) => {
    const value = editedSettings[key];
    if (value === undefined) return;
    setSettingsError((prev) => ({ ...prev, [key]: "" }));

    const res = await apiFetch(`/api/admin/settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });

    if (res.ok) {
      setEditedSettings((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      fetchSettings();
      onSaved();
    } else {
      const data = await res.json();
      setSettingsError((prev) => ({ ...prev, [key]: data.detail || "Fehler" }));
    }
  };

  // Setting zuruecksetzen
  const handleResetSetting = async (key: string) => {
    setSettingsError((prev) => ({ ...prev, [key]: "" }));
    const res = await apiFetch(`/api/admin/settings/${key}`, { method: "DELETE" });
    if (res.ok) {
      setEditedSettings((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      fetchSettings();
      onSaved();
    } else {
      const data = await res.json();
      setSettingsError((prev) => ({ ...prev, [key]: data.detail || "Fehler" }));
    }
  };

  return (
    <div className="admin-section">
      <h2 className="admin-section__title">{t("admin.settings.title")}</h2>

      {Object.entries(SETTING_GROUPS).map(([group, keys]) => {
        const groupSettings = getGroupSettings(keys);
        if (groupSettings.length === 0) return null;

        // OIDC-Gruppe: automatisch offen wenn aktiviert
        const isOpen = group === "oidc"
          ? (openGroups[group] ?? oidcEnabled)
          : (openGroups[group] ?? false);

        return (
          <div key={group} className="admin-settings-group">
            <button
              className={`admin-settings-group__toggle ${isOpen ? "admin-settings-group__toggle--open" : ""}`}
              onClick={() => toggleGroup(group)}
            >
              <span className="admin-settings-group__arrow">{isOpen ? "\u25BC" : "\u25B6"}</span>
              {t(`admin.settings.group.${group}` as any)}
              {group === "oidc" && oidcEnabled && (
                <span className="admin-badge admin-badge--oidc" style={{ marginLeft: "8px" }}>aktiv</span>
              )}
            </button>

            {isOpen && (
              <div className="admin-settings-group__content">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>{t("admin.settings.key")}</th>
                      <th>{t("admin.settings.value")}</th>
                      <th>{t("admin.settings.source")}</th>
                      <th>{t("admin.users.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupSettings.map((setting) => {
                      const isBool = setting.type === "bool";
                      const isAccessToggle = setting.key === "avatar_access";
                      const currentValue = editedSettings[setting.key] ?? setting.value;
                      const boolValue = currentValue.toLowerCase() === "true";

                      return (
                      <tr key={setting.key}>
                        <td className="admin-table__key">{setting.key}</td>
                        <td>
                          {isAccessToggle ? (
                            <button
                              className={`admin-toggle admin-toggle--setting ${currentValue === "subnet" ? "admin-toggle--on" : "admin-toggle--off"}`}
                              onClick={() => {
                                const newVal = currentValue === "subnet" ? "public" : "subnet";
                                setEditedSettings((prev) => ({ ...prev, [setting.key]: newVal }));
                              }}
                            >
                              {currentValue === "subnet" ? "subnet" : "public"}
                            </button>
                          ) : isBool ? (
                            <button
                              className={`admin-toggle admin-toggle--setting ${boolValue ? "admin-toggle--on" : "admin-toggle--off"}`}
                              onClick={() => {
                                const newVal = boolValue ? "false" : "true";
                                setEditedSettings((prev) => ({ ...prev, [setting.key]: newVal }));
                              }}
                            >
                              {boolValue ? "true" : "false"}
                            </button>
                          ) : (
                            <input
                              className={`admin-input admin-input--table ${settingsError[setting.key] ? "admin-input--error" : ""}`}
                              value={currentValue}
                              onChange={(e) =>
                                setEditedSettings((prev) => ({ ...prev, [setting.key]: e.target.value }))
                              }
                            />
                          )}
                          {settingsError[setting.key] && (
                            <p className="admin-error admin-error--inline">{settingsError[setting.key]}</p>
                          )}
                        </td>
                        <td>
                          <span className={`admin-badge admin-badge--${setting.source}`}>
                            {setting.source}
                          </span>
                        </td>
                        <td className="admin-table__actions">
                          {editedSettings[setting.key] !== undefined && (
                            <button
                              className="btn btn--primary btn--sm"
                              onClick={() => handleSaveSetting(setting.key)}
                            >
                              {t("admin.settings.save")}
                            </button>
                          )}
                          {setting.source === "db" && (
                            <button
                              className="btn btn--secondary btn--sm"
                              onClick={() => handleResetSetting(setting.key)}
                              title={t("admin.settings.reset.tooltip")}
                            >
                              {t("admin.settings.reset")}
                            </button>
                          )}
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
