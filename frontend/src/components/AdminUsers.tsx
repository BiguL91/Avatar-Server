import { useState, useCallback, useEffect } from "react";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";
import { ConfirmDialog } from "./ConfirmDialog";

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  source: string;
  is_admin: boolean;
  is_active: boolean;
  avatar_count: number;
  created_at: string;
}

interface AdminUsersProps {
  currentUserId: number;
  onSaved: () => void;
}

export function AdminUsers({ currentUserId, onSaved }: AdminUsersProps) {
  const { t } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
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

  const fetchUsers = useCallback(async () => {
    const res = await apiFetch("/api/admin/users");
    if (res.ok) {
      const data = await res.json();
      setUsers(data.users);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

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
      onSaved();
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
      onSaved();
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
    if (res.ok) onSaved();
  };

  // Admin-Toggle
  const handleToggleAdmin = async (userId: number, currentAdmin: boolean) => {
    const res = await apiFetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_admin: !currentAdmin }),
    });
    fetchUsers();
    if (res.ok) onSaved();
  };

  return (
    <>
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
                      {user.is_admin ? "\u2713" : "\u2013"}
                    </button>
                  </td>
                  <td>
                    <button
                      className={`admin-toggle ${user.is_active ? "admin-toggle--on" : "admin-toggle--off"}`}
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                      disabled={user.id === currentUserId}
                      title={user.id === currentUserId ? t("admin.users.deactivate.self") : ""}
                    >
                      {user.is_active ? "\u2713" : "\u2013"}
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

      {/* Loesch-Bestaetigung */}
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
    </>
  );
}
