import { useState, useCallback, useEffect, useMemo } from "react";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";

interface AdminAvatar {
  id: number;
  user_id: number;
  user_name: string;
  user_email: string;
  is_active: boolean;
  is_locked: boolean;
  created_at: string;
  thumbnail: string;
}

interface UserGroup {
  user_id: number;
  user_name: string;
  user_email: string;
  avatars: AdminAvatar[];
}

interface AdminAvatarsProps {
  onSaved: () => void;
}

export function AdminAvatars({ onSaved }: AdminAvatarsProps) {
  const { t } = useTranslation();
  const [avatars, setAvatars] = useState<AdminAvatar[]>([]);
  const [loading, setLoading] = useState(true);
  const [openUsers, setOpenUsers] = useState<Record<number, boolean>>({});

  const fetchAvatars = useCallback(async () => {
    const res = await apiFetch("/api/admin/avatars");
    if (res.ok) {
      const data = await res.json();
      setAvatars(data.avatars);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAvatars();
  }, [fetchAvatars]);

  // Avatare nach User gruppieren
  const userGroups = useMemo<UserGroup[]>(() => {
    const map = new Map<number, UserGroup>();
    for (const avatar of avatars) {
      let group = map.get(avatar.user_id);
      if (!group) {
        group = {
          user_id: avatar.user_id,
          user_name: avatar.user_name,
          user_email: avatar.user_email,
          avatars: [],
        };
        map.set(avatar.user_id, group);
      }
      group.avatars.push(avatar);
    }
    return Array.from(map.values());
  }, [avatars]);

  const toggleUser = (userId: number) => {
    setOpenUsers((prev) => ({ ...prev, [userId]: !prev[userId] }));
  };

  const handleToggleLock = async (avatarId: number) => {
    const res = await apiFetch(`/api/admin/avatars/${avatarId}/lock`, {
      method: "PATCH",
    });
    if (res.ok) {
      fetchAvatars();
      onSaved();
    }
  };

  if (loading) return null;

  return (
    <div className="admin-section">
      <h2 className="admin-section__title">{t("admin.avatars.title")}</h2>

      {userGroups.length === 0 ? (
        <p className="admin-avatars__empty">{t("admin.avatars.empty")}</p>
      ) : (
        <div className="admin-avatars__users">
          {userGroups.map((group) => {
            const isOpen = openUsers[group.user_id] ?? false;
            const lockedCount = group.avatars.filter((a) => a.is_locked).length;

            return (
              <div key={group.user_id} className="admin-avatars__user-group">
                <button
                  className="admin-avatars__user-toggle"
                  onClick={() => toggleUser(group.user_id)}
                >
                  <span className="admin-settings-group__arrow">
                    {isOpen ? "\u25BC" : "\u25B6"}
                  </span>
                  <span className="admin-avatars__user-name">{group.user_name}</span>
                  <span className="admin-avatars__user-email">{group.user_email}</span>
                  <span className="admin-avatars__user-count">
                    {group.avatars.length} {t("admin.users.avatars")}
                    {lockedCount > 0 && (
                      <span className="admin-badge admin-badge--locked" style={{ marginLeft: "6px" }}>
                        {lockedCount} {t("admin.avatars.locked")}
                      </span>
                    )}
                  </span>
                </button>

                {isOpen && (
                  <div className="admin-avatars__grid">
                    {group.avatars.map((avatar) => (
                      <div
                        key={avatar.id}
                        className={`admin-avatars__card ${avatar.is_locked ? "admin-avatars__card--locked" : ""}`}
                      >
                        <img
                          src={avatar.thumbnail}
                          alt={`Avatar #${avatar.id}`}
                          className="admin-avatars__thumb"
                        />
                        <div className="admin-avatars__info">
                          <div className="admin-avatars__badges">
                            {avatar.is_active && (
                              <span className="admin-badge admin-badge--db">{t("history.active")}</span>
                            )}
                            {avatar.is_locked && (
                              <span className="admin-badge admin-badge--locked">{t("admin.avatars.locked")}</span>
                            )}
                          </div>
                        </div>
                        <button
                          className={`btn btn--sm ${avatar.is_locked ? "btn--primary" : "btn--danger"}`}
                          onClick={() => handleToggleLock(avatar.id)}
                        >
                          {avatar.is_locked ? t("admin.avatars.unlock") : t("admin.avatars.lock")}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
