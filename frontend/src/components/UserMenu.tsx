import { useState, useEffect, useRef } from "react";
import { useTranslation } from "../i18n/i18n";
import "./UserMenu.css";

interface UserData {
  name: string;
  email: string;
  is_admin: boolean;
  avatarUrl: string | null;
}

interface UserMenuProps {
  user: UserData;
  onLogout: () => void;
  onSettings: () => void;
  onAdmin: () => void;
}

export function UserMenu({ user, onLogout, onSettings, onAdmin }: UserMenuProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Klick ausserhalb schliesst Dropdown
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Escape schliesst Dropdown
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  // Initialen aus dem Namen
  const initials = user.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="user-menu" ref={menuRef}>
      <button className="user-menu__trigger" onClick={() => setOpen(!open)}>
        {user.avatarUrl ? (
          <img key={user.avatarUrl} src={user.avatarUrl} alt="" className="user-menu__avatar" />
        ) : (
          <div className="user-menu__avatar-placeholder">{initials}</div>
        )}
        <span className="user-menu__name">{user.name}</span>
      </button>

      {open && (
        <div className="user-menu__dropdown">
          <button className="user-menu__item" onClick={() => { setOpen(false); onSettings(); }}>
            {t("usermenu.settings")}
          </button>
          {user.is_admin && (
            <button className="user-menu__item" onClick={() => { setOpen(false); onAdmin(); }}>
              {t("usermenu.admin")}
            </button>
          )}
          <div className="user-menu__divider" />
          <button
            className="user-menu__item user-menu__item--danger"
            onClick={() => { setOpen(false); onLogout(); }}
          >
            {t("usermenu.logout")}
          </button>
        </div>
      )}
    </div>
  );
}
