import { useState, useRef, useEffect, useCallback } from "react";
import { type Crop } from "react-image-crop";
import { useTranslation } from "../i18n/i18n";
import "./CropEditor.css";

// Kreisdurchmesser = 85% der Viewport-Groesse
const CIRCLE_RATIO = 0.85;

interface CropEditorProps {
  src: string;
  onSave: (crop: Crop) => void;
  onCancel: () => void;
  saveLabel: string;
  isSaving?: boolean;
}

export function CropEditor({ src, onSave, onCancel, saveLabel, isSaving = false }: CropEditorProps) {
  const { t } = useTranslation();
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const [vpSize, setVpSize] = useState(0);
  const vpRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  // Viewport-Groesse beobachten
  useEffect(() => {
    const el = vpRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setVpSize(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    setImgSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight });
  };

  // Pan begrenzen damit Bild den Kreis immer abdeckt
  const clampPan = useCallback((px: number, py: number, z: number) => {
    if (!vpSize || !imgSize.w) return { x: px, y: py };
    const circleD = vpSize * CIRCLE_RATIO;
    const scale = (circleD / Math.min(imgSize.w, imgSize.h)) * z;
    const maxX = Math.max(0, (imgSize.w * scale - circleD) / 2);
    const maxY = Math.max(0, (imgSize.h * scale - circleD) / 2);
    return {
      x: Math.max(-maxX, Math.min(maxX, px)),
      y: Math.max(-maxY, Math.min(maxY, py)),
    };
  }, [vpSize, imgSize]);

  // Drag-Start (linke Maustaste)
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    isDragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan.x, pan.y]);

  // Drag-Move und Drag-End
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const newPan = clampPan(
        dragStart.current.panX + (e.clientX - dragStart.current.x),
        dragStart.current.panY + (e.clientY - dragStart.current.y),
        zoom,
      );
      setPan(newPan);
    };
    const handleMouseUp = () => { isDragging.current = false; };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [clampPan, zoom]);

  // Zoom aendern + Pan anpassen
  const handleZoomChange = useCallback((newZoom: number) => {
    const clamped = Math.max(1, Math.min(3, newZoom));
    setZoom(clamped);
    setPan((prev) => clampPan(prev.x, prev.y, clamped));
  }, [clampPan]);

  // Mausrad zum Zoomen
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const step = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((prev) => {
      const newZoom = Math.max(1, Math.min(3, prev + step));
      setPan((p) => clampPan(p.x, p.y, newZoom));
      return newZoom;
    });
  }, [clampPan]);

  // Crop-Koordinaten berechnen (Prozent vom Originalbild)
  const calculateCrop = useCallback((): Crop => {
    if (!vpSize || !imgSize.w) {
      return { unit: "%", x: 0, y: 0, width: 100, height: 100 };
    }
    const circleD = vpSize * CIRCLE_RATIO;
    const scale = (circleD / Math.min(imgSize.w, imgSize.h)) * zoom;

    // Bild-Position (top-left) im Viewport
    const imgLeft = vpSize / 2 - (imgSize.w * scale) / 2 + pan.x;
    const imgTop = vpSize / 2 - (imgSize.h * scale) / 2 + pan.y;

    // Kreis-Position (top-left) im Viewport
    const circleLeft = (vpSize - circleD) / 2;
    const circleTop = (vpSize - circleD) / 2;

    // Crop in Original-Pixeln, dann in Prozent
    const cropX = (circleLeft - imgLeft) / scale;
    const cropY = (circleTop - imgTop) / scale;
    const cropSize = circleD / scale;

    return {
      unit: "%",
      x: (cropX / imgSize.w) * 100,
      y: (cropY / imgSize.h) * 100,
      width: (cropSize / imgSize.w) * 100,
      height: (cropSize / imgSize.h) * 100,
    };
  }, [vpSize, imgSize, zoom, pan]);

  // Bild-Style: Groesse + Position
  const getImageStyle = (): React.CSSProperties => {
    if (!vpSize || !imgSize.w) return { opacity: 0 };
    const circleD = vpSize * CIRCLE_RATIO;
    const scale = (circleD / Math.min(imgSize.w, imgSize.h)) * zoom;
    return {
      width: imgSize.w * scale,
      height: imgSize.h * scale,
      transform: `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px))`,
    };
  };

  return (
    <div className="crop-editor">
      <div
        ref={vpRef}
        className="crop-editor__viewport"
        onMouseDown={handleMouseDown}
        onWheel={handleWheel}
        onContextMenu={(e) => e.preventDefault()}
      >
        <img
          src={src}
          alt="Crop"
          onLoad={handleImageLoad}
          className="crop-editor__image"
          style={getImageStyle()}
          draggable={false}
        />
        <div className="crop-editor__circle" />
      </div>

      <div className="crop-editor__zoom">
        <span className="crop-editor__zoom-label">-</span>
        <input
          type="range"
          min="1"
          max="3"
          step="0.05"
          value={zoom}
          onChange={(e) => handleZoomChange(Number(e.target.value))}
          className="crop-editor__zoom-input"
        />
        <span className="crop-editor__zoom-label">+</span>
      </div>

      <div className="crop-editor__actions">
        <button className="btn btn--secondary" onClick={onCancel}>
          {t("crop.cancel")}
        </button>
        <button
          className={`btn btn--primary ${isSaving ? "btn--loading" : ""}`}
          onClick={() => onSave(calculateCrop())}
          disabled={isSaving}
        >
          {isSaving && <span className="spinner" />}
          {saveLabel}
        </button>
      </div>
    </div>
  );
}
