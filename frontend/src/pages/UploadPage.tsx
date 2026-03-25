import { useState, useRef, useCallback } from "react";
import { type Crop } from "react-image-crop";
import { useTranslation } from "../i18n/i18n";
import { apiFetch } from "../utils/api";
import { AvatarHistory } from "../components/AvatarHistory";
import { CropEditor } from "../components/CropEditor";
import "./UploadPage.css";

interface UploadResult {
  success: boolean;
  upload_id: number;
  hashes: { md5: string; sha256: string };
  is_active: boolean;
}

interface UploadPageProps {
  onAvatarChange?: () => void;
  avatarSizes?: number[];
  avatarAccess?: string;
  avatarUserCanPublish?: boolean;
}

export function UploadPage({ onAvatarChange, avatarSizes, avatarAccess, avatarUserCanPublish }: UploadPageProps) {
  const { t } = useTranslation();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [isLoadingUrl, setIsLoadingUrl] = useState(false);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [limitReached, setLimitReached] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return;
    setSelectedFile(file);
    setUploadResult(null);
    setError(null);

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleUrlLoad = async () => {
    if (!imageUrl.trim()) return;

    setIsLoadingUrl(true);
    setError(null);

    try {
      const response = await apiFetch(`/api/fetch-image?url=${encodeURIComponent(imageUrl.trim())}`);
      if (!response.ok) throw new Error(t("upload.url.error"));

      const blob = await response.blob();
      const file = new File([blob], "url-image", { type: blob.type });
      handleFileSelect(file);
      setImageUrl("");
    } catch {
      setError(t("upload.url.error"));
    } finally {
      setIsLoadingUrl(false);
    }
  };

  const handleUrlKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleUrlLoad();
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadResult(null);
    setError(null);
    setImageUrl("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (crop: Crop) => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("crop_x", String(crop.x));
      formData.append("crop_y", String(crop.y));
      formData.append("crop_width", String(crop.width));
      formData.append("crop_height", String(crop.height));

      const response = await apiFetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(t("upload.error"));
      }

      const result: UploadResult = await response.json();
      setUploadResult(result);
      setHistoryRefresh((n) => n + 1);
      onAvatarChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("upload.error"));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <h1 className="upload-title">{t("upload.title")}</h1>

      {error && <div className="upload-error">{error}</div>}

      {limitReached && !previewUrl && !uploadResult ? (
        <p className="upload-limit-hint">{t("upload.limit")}</p>
      ) : uploadResult ? (
        <div className="upload-success">
          <div className="upload-success__icon">&#10003;</div>
          <p>{t("preview.title")}</p>
          <button className="btn btn--secondary" onClick={handleReset}>
            {t("upload.btn.new")}
          </button>
        </div>
      ) : !previewUrl ? (
        <>
        <div
          className={`dropzone ${isDragging ? "dropzone--active" : ""}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="dropzone__content">
            <div className="dropzone__icon">+</div>
            <p>{t("upload.dropzone")}</p>
            <p className="dropzone__hint">{t("upload.dropzone.hint")}</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            hidden
          />
        </div>

          <div className="url-divider">
            <span>{t("upload.url.divider")}</span>
          </div>

          <div className="url-input-row">
            <input
              type="url"
              className="url-input"
              placeholder={t("upload.url.placeholder")}
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              onKeyDown={handleUrlKeyDown}
              disabled={isLoadingUrl}
            />
            <button
              className={`btn btn--primary ${isLoadingUrl ? "btn--loading" : ""}`}
              onClick={handleUrlLoad}
              disabled={isLoadingUrl || !imageUrl.trim()}
            >
              {isLoadingUrl && <span className="spinner" />}
              {t("upload.url.load")}
            </button>
          </div>
        </>
      ) : (
        <CropEditor
          src={previewUrl}
          onSave={handleUpload}
          onCancel={handleReset}
          saveLabel={isUploading ? t("upload.btn.uploading") : t("upload.btn.upload")}
          isSaving={isUploading}
        />
      )}

      <AvatarHistory
        refreshTrigger={historyRefresh}
        onLimitInfo={setLimitReached}
        onAvatarChange={onAvatarChange}
        avatarSizes={avatarSizes}
        avatarAccess={avatarAccess}
        avatarUserCanPublish={avatarUserCanPublish}
      />
    </div>
  );
}
