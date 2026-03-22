import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import "./AdminPage.css";

interface AdminUser {
  id: number;
  email: string;
  name: string;
  source: string;
  is_admin: boolean;
  is_active: boolean;
  avatar_count: number;
  created_at: string;
}

interface AdminSetting {
  key: string;
  value: string;
  source: string;
  type: string;
  updated_at: string | null;
}

interface AdminPageProps {
  onBack: () => void;
  currentUserId: number;
}

export function AdminPage({ onBack, currentUserId }: AdminPageProps) {
  const { t } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [settings, setSettings] = useState<AdminSetting[]>([]);
  const [deleteUserId, setDeleteUserId] = useState<number | null>(null);

  // Formular: Neuer User
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [createError, setCreateError] = useState("");

  // Formular: User bearbeiten
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [editName, setEditName] = useState("");
  const [editPassword, setEditPassword] = useState("");
  const [editError, setEditError] = useState("");

  // Toast
  const [toastVisible, setToastVisible] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const showToast = useCallback(() => {
    setToastVisible(true);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastVisible(false), 2000);
  }, []);

  // Settings: Bearbeitungszustand
  const [editedSettings, setEditedSettings] = useState<Record<string, string>>({});
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [settingsError, setSettingsError] = useState<Record<string, string>>({});

  // Settings nach Gruppen sortieren
  const settingGroups: Record<string, string[]> = {
    avatar: [
      "avatar_max_uploads", "avatar_cache_max_age", "avatar_upload_max_bytes",
      "avatar_original_max_px", "avatar_default_size", "avatar_max_size", "avatar_sizes",
    ],
    login: ["legacy_login", "dev_mode", "trusted_proxy", "base_url"],
    oidc: [
      "oidc_enabled", "oidc_discovery_url", "oidc_client_id", "oidc_client_secret",
      "oidc_claim_email", "oidc_claim_name", "oidc_claim_picture", "oidc_claim_picture_png",
      "oidc_claim_groups", "oidc_admin_group", "oidc_sync_picture", "oidc_picture_size",
    ],
    general: ["default_language"],
  };

  const toggleGroup = (group: string) => {
    setOpenGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  // OIDC-Gruppe automatisch oeffnen wenn oidc_enabled=true
  const oidcEnabled = settings.find((s) => s.key === "oidc_enabled")?.value?.toLowerCase() === "true";

  const getGroupSettings = (keys: string[]) =>
    keys.map((key) => settings.find((s) => s.key === key)).filter(Boolean) as AdminSetting[];

  const fetchUsers = useCallback(async () => {
    const res = await apiFetch("/api/admin/users");
    if (res.ok) {
      const data = await res.json();
      setUsers(data.users);
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    const res = await apiFetch("/api/admin/settings");
    if (res.ok) {
      const data = await res.json();
      setSettings(data.settings);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchSettings();
  }, [fetchUsers, fetchSettings]);

  // User anlegen
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");

    const res = await apiFetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: newEmail, name: newName, password: newPassword }),
    });

    if (res.ok) {
      setShowCreateForm(false);
      setNewEmail("");
      setNewName("");
      setNewPassword("");
      fetchUsers();
      showToast();
    } else {
      const data = await res.json();
      setCreateError(data.detail || "Fehler");
    }
  };

  // User loeschen
  const handleDeleteUser = async (userId: number) => {
    const res = await apiFetch(`/api/admin/users/${userId}`, { method: "DELETE" });
    if (res.ok) {
      fetchUsers();
    }
    setDeleteUserId(null);
  };

  // User bearbeiten - Dialog oeffnen
  const openEditDialog = (user: AdminUser) => {
    setEditUser(user);
    setEditName(user.name);
    setEditPassword("");
    setEditError("");
  };

  // User bearbeiten - speichern
  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editUser) return;
    setEditError("");

    const body: Record<string, string | boolean> = {};
    if (editName !== editUser.name) body.name = editName;
    if (editPassword) body.password = editPassword;

    // Nichts geaendert
    if (Object.keys(body).length === 0) {
      setEditUser(null);
      return;
    }

    const res = await apiFetch(`/api/admin/users/${editUser.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (res.ok) {
      setEditUser(null);
      fetchUsers();
      showToast();
    } else {
      const data = await res.json();
      setEditError(data.detail || "Fehler");
    }
  };

  // Active-Toggle
  const handleToggleActive = async (userId: number, currentActive: boolean) => {
    const res = await apiFetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !currentActive }),
    });
    fetchUsers();
    if (res.ok) showToast();
  };

  // Admin-Toggle
  const handleToggleAdmin = async (userId: number, currentAdmin: boolean) => {
    const res = await apiFetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_admin: !currentAdmin }),
    });
    fetchUsers();
    if (res.ok) showToast();
  };

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
      showToast();
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
      showToast();
    } else {
      const data = await res.json();
      setSettingsError((prev) => ({ ...prev, [key]: data.detail || "Fehler" }));
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <button className="settings-header__back" onClick={onBack}>
          &larr; {t("admin.back")}
        </button>
        <h1 className="admin-title">{t("admin.title")}</h1>
      </div>

      {/* === Benutzerverwaltung === */}
      <div className="admin-section">
        <div className="admin-section__header">
          <h2 className="admin-section__title">{t("admin.users.title")}</h2>
          <button
            className="btn btn--primary btn--sm"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {t("admin.users.create")}
          </button>
        </div>

        {/* Neuer User Formular */}
        {showCreateForm && (
          <form className="admin-create-form" onSubmit={handleCreateUser}>
            <h3 className="admin-create-form__title">{t("admin.users.create.title")}</h3>
            <div className="admin-create-form__fields">
              <input
                className="admin-input"
                type="email"
                placeholder={t("admin.users.email")}
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
              />
              <input
                className="admin-input"
                type="text"
                placeholder={t("admin.users.name")}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
              <input
                className="admin-input"
                type="password"
                placeholder={t("admin.users.password")}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            {createError && <p className="admin-error">{createError}</p>}
            <div className="admin-create-form__actions">
              <button className="btn btn--primary btn--sm" type="submit">
                {t("admin.users.create.submit")}
              </button>
              <button
                className="btn btn--secondary btn--sm"
                type="button"
                onClick={() => setShowCreateForm(false)}
              >
                {t("dialog.cancel")}
              </button>
            </div>
          </form>
        )}

        {/* User-Tabelle */}
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("admin.users.email")}</th>
                <th>{t("admin.users.name")}</th>
                <th>{t("admin.users.source")}</th>
                <th>{t("admin.users.admin")}</th>
                <th>{t("admin.users.active")}</th>
                <th>{t("admin.users.avatars")}</th>
                <th>{t("admin.users.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className={!user.is_active ? "admin-row--inactive" : ""}>
                  <td>{user.email}</td>
                  <td>{user.name}</td>
                  <td>
                    <span className={`admin-badge admin-badge--${user.source}`}>
                      {user.source}
                    </span>
                  </td>
                  <td>
                    <button
                      className={`admin-toggle ${user.is_admin ? "admin-toggle--on" : ""}`}
                      onClick={() => handleToggleAdmin(user.id, user.is_admin)}
                      disabled={user.id === currentUserId}
                    >
                      {user.is_admin ? "✓" : "–"}
                    </button>
                  </td>
                  <td>
                    <button
                      className={`admin-toggle ${user.is_active ? "admin-toggle--on" : "admin-toggle--off"}`}
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                      disabled={user.id === currentUserId}
                      title={user.id === currentUserId ? t("admin.users.deactivate.self") : ""}
                    >
                      {user.is_active ? "✓" : "–"}
                    </button>
                  </td>
                  <td>{user.avatar_count}</td>
                  <td className="admin-table__actions">
                    {user.source === "local" && (
                      <button
                        className="btn btn--secondary btn--sm"
                        onClick={() => openEditDialog(user)}
                      >
                        {t("history.edit")}
                      </button>
                    )}
                    {user.id !== currentUserId && (
                      <button
                        className="btn btn--danger btn--sm"
                        onClick={() => setDeleteUserId(user.id)}
                      >
                        {t("history.delete")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* === Settings === */}
      <div className="admin-section">
        <h2 className="admin-section__title">{t("admin.settings.title")}</h2>

        {Object.entries(settingGroups).map(([group, keys]) => {
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
                        const currentValue = editedSettings[setting.key] ?? setting.value;
                        const boolValue = currentValue.toLowerCase() === "true";

                        return (
                        <tr key={setting.key}>
                          <td className="admin-table__key">{setting.key}</td>
                          <td>
                            {isBool ? (
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

      {/* Edit-Dialog */}
      {editUser && (
        <div className="admin-overlay" onClick={() => setEditUser(null)}>
          <div className="admin-edit-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="admin-edit-dialog__title">{t("admin.users.edit.title")}</h3>
            <form onSubmit={handleEditUser}>
              <div className="admin-edit-dialog__fields">
                <label className="admin-edit-dialog__label">
                  {t("admin.users.name")}
                  <input
                    className="admin-input"
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                  />
                </label>
                <label className="admin-edit-dialog__label">
                  {t("admin.users.password")}
                  <input
                    className="admin-input"
                    type="password"
                    value={editPassword}
                    onChange={(e) => setEditPassword(e.target.value)}
                    placeholder={t("admin.users.edit.password.hint")}
                  />
                </label>
              </div>
              {editError && <p className="admin-error">{editError}</p>}
              <div className="admin-edit-dialog__actions">
                <button className="btn btn--primary btn--sm" type="submit">
                  {t("admin.users.edit.save")}
                </button>
                <button
                  className="btn btn--secondary btn--sm"
                  type="button"
                  onClick={() => setEditUser(null)}
                >
                  {t("dialog.cancel")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lösch-Bestätigung */}
      {deleteUserId !== null && (
        <ConfirmDialog
          message={t("admin.users.delete.confirm")}
          confirmLabel={t("dialog.delete.confirm")}
          cancelLabel={t("dialog.cancel")}
          onConfirm={() => handleDeleteUser(deleteUserId)}
          onCancel={() => setDeleteUserId(null)}
          danger
        />
      )}

      {/* Toast */}
      <div className={`admin-toast ${toastVisible ? "admin-toast--visible" : ""}`}>
        {t("toast.saved")}
      </div>
    </div>
  );
}
