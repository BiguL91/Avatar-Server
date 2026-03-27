import { useState, useEffect, useCallback, useRef } from "react";
import { type Crop } from "react-image-crop";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";
import { CropEditor } from "./CropEditor";
import { ConfirmDialog } from "./ConfirmDialog";
import "./AvatarHistory.css";

interface UploadEntry {
  id: number;
  created_at: string;
  is_active: boolean;
  is_locked: boolean;
  thumbnail: string;
}

interface HistoryData {
  uploads: UploadEntry[];
  hashes: { md5: string; sha256: string };
  max_uploads: number;
}

interface AvatarHistoryProps {
  refreshTrigger: number;
  onLimitInfo?: (isFull: boolean) => void;
  onAvatarChange?: () => void;
  avatarSizes?: number[];
  avatarAccess?: string;
  avatarUserCanPublish?: boolean;
}

const PREVIEW_SIZES = [64, 128, 256];

export function AvatarHistory({ refreshTrigger, onLimitInfo, onAvatarChange, avatarSizes, avatarAccess, avatarUserCanPublish }: AvatarHistoryProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [cacheKey, setCacheKey] = useState(0);
  const [copied, setCopied] = useState(false);
  const [previewSize, setPreviewSize] = useState<number | null>(null);
  const [avatarPublic, setAvatarPublic] = useState(false);
  const urlInputRef = useRef<HTMLInputElement>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const response = await apiFetch("/api/history");
      if (!response.ok) return;
      const result: HistoryData = await response.json();
      setData(result);
      onLimitInfo?.(result.uploads.length >= result.max_uploads);

      // avatar_public Status laden
      const meResponse = await apiFetch("/api/upload/me");
      if (meResponse.ok) {
        const meData = await meResponse.json();
        setAvatarPublic(meData.avatar_public ?? false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, refreshTrigger]);

  const handleActivate = async (uploadId: number) => {
    const response = await apiFetch(`/api/activate/${uploadId}`, { method: "POST" });
    if (response.ok) {
      setCacheKey((n) => n + 1);
      fetchHistory();
      onAvatarChange?.();
    }
  };

  const handleDelete = async (uploadId: number) => {
    const response = await apiFetch(`/api/uploads/${uploadId}`, { method: "DELETE" });
    if (response.ok) {
      fetchHistory();
      onAvatarChange?.();
    }
    setDeleteId(null);
  };

  const handleRecrop = async (crop: Crop) => {
    if (!editId) return;
    setIsSaving(true);

    try {
      const formData = new FormData();
      formData.append("crop_x", String(crop.x));
      formData.append("crop_y", String(crop.y));
      formData.append("crop_width", String(crop.width));
      formData.append("crop_height", String(crop.height));

      const response = await apiFetch(`/api/recrop/${editId}`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        setEditId(null);
        setCacheKey((n) => n + 1);
        fetchHistory();
        onAvatarChange?.();
      }
    } finally {
      setIsSaving(false);
    }
  };

  // URL-Input Breite an Inhalt anpassen (Fallback fuer Browser ohne field-sizing: content)
  useEffect(() => {
    const input = urlInputRef.current;
    if (!input) return;
    input.style.width = "0";
    input.style.width = `${input.scrollWidth + 4}px`;
  }, [previewSize]);

  if (loading) return null;
  if (!data || data.uploads.length === 0) return null;

  const activeUpload = data.uploads.find((u) => u.is_active);
  const userHash = data.hashes.sha256;
  const publicUrl = activeUpload
    ? `${window.location.origin}/avatar/${data.hashes.md5}${previewSize ? `?s=${previewSize}` : ""}`
    : null;

  const handleTogglePublish = async () => {
    const response = await apiFetch("/api/avatar/publish", { method: "POST" });
    if (response.ok) {
      const result = await response.json();
      setAvatarPublic(result.avatar_public);
    }
  };

  const handleCopy = async () => {
    if (!publicUrl) return;
    await navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="history">
      {/* Aktive Vorschau - immer sichtbar */}
      {activeUpload && (
        <div className="active-preview" key={`active-${activeUpload.id}-${cacheKey}`}>
          <h2 className="history__title">{t("preview.title")}</h2>
          <div className="active-preview__grid">
            {PREVIEW_SIZES.map((size, i) => (
              <div
                key={size}
                className={`active-preview__item ${previewSize === size ? "active-preview__item--selected" : ""}`}
                style={{ animationDelay: `${i * 0.15}s`, cursor: "pointer" }}
                onClick={() => setPreviewSize(previewSize === size ? null : size)}
              >
                <img
                  src={`/api/uploads/${userHash}/${activeUpload.id}/${size}.webp?v=${cacheKey}`}
                  alt={`Avatar ${size}px`}
                  className="active-preview__avatar"
                  width={size}
                  height={size}
                />
                <span className="active-preview__label">{size}px</span>
              </div>
            ))}
          </div>
          {/* Publish-Toggle: nur bei subnet-Modus und wenn erlaubt */}
          {avatarAccess === "subnet" && avatarUserCanPublish && (
            <div className="active-preview__publish">
              <button
                className={`btn btn--sm ${avatarPublic ? "btn--primary" : "btn--secondary"}`}
                onClick={handleTogglePublish}
              >
                {avatarPublic ? t("preview.publish.on") : t("preview.publish.off")}
              </button>
            </div>
          )}
          {/* URL: anzeigen wenn public-Modus ODER (subnet + avatar_public) */}
          {publicUrl && (avatarAccess !== "subnet" || avatarPublic) && (
            <div className="active-preview__url">
              <label className="active-preview__url-label">{t("preview.url.label")}</label>
              <div className="active-preview__url-row">
                <input
                  ref={urlInputRef}
                  type="text"
                  className="active-preview__url-input"
                  value={publicUrl}
                  readOnly
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                />
                <button className="btn btn--secondary btn--sm" onClick={handleCopy}>
                  {copied ? t("preview.url.copied") : "Copy"}
                </button>
              </div>
              <p className="active-preview__url-hint">{t("preview.url.hint")}</p>
              {avatarSizes && (
                <p className="active-preview__url-hint">
                  {t("preview.url.sizes")} {avatarSizes.join(", ")}px
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Lösch-Bestätigung */}
      {deleteId !== null && (
        <ConfirmDialog
          message={t("history.delete.confirm")}
          confirmLabel={t("dialog.delete.confirm")}
          cancelLabel={t("dialog.cancel")}
          onConfirm={() => handleDelete(deleteId)}
          onCancel={() => setDeleteId(null)}
          danger
        />
      )}

      {/* Editor Popup */}
      {editId !== null && (
        <div className="editor-overlay">
          <div className="editor-modal">
            <CropEditor
              src={`/api/uploads/${userHash}/${editId}/original.webp`}
              onSave={handleRecrop}
              onCancel={() => setEditId(null)}
              saveLabel={t("history.recrop.save")}
              isSaving={isSaving}
            />
          </div>
        </div>
      )}

      {/* Historie Grid */}
      <h2 className="history__title">{t("history.title")}</h2>
      <div className="history__grid">
        {data.uploads.map((upload) => (
          <div
            key={upload.id}
            className={`history__item ${upload.is_active ? "history__item--active" : ""} ${upload.is_locked ? "history__item--locked" : ""}`}
          >
            <img
              src={`${upload.thumbnail}?v=${cacheKey}`}
              alt={`Avatar #${upload.id}`}
              className="history__thumbnail"
            />

            {upload.is_locked ? (
              <div className="history__locked-row">
                <span className="history__badge history__badge--locked">{t("history.locked")}</span>
                <button
                  className="btn btn--danger btn--sm"
                  onClick={() => setDeleteId(upload.id)}
                >
                  {t("history.delete")}
                </button>
              </div>
            ) : upload.is_active ? (
              <div className="history__active-row">
                <span className="history__badge">{t("history.active")}</span>
                <button
                  className="btn btn--secondary btn--sm"
                  onClick={() => setEditId(upload.id)}
                >
                  {t("history.edit")}
                </button>
              </div>
            ) : (
              <div className="history__actions">
                <button
                  className="btn btn--primary btn--sm"
                  onClick={() => handleActivate(upload.id)}
                >
                  {t("history.activate")}
                </button>
                <button
                  className="btn btn--secondary btn--sm"
                  onClick={() => setEditId(upload.id)}
                >
                  {t("history.edit")}
                </button>
                <button
                  className="btn btn--danger btn--sm"
                  onClick={() => setDeleteId(upload.id)}
                >
                  {t("history.delete")}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
