# TODO - Geplante Features

Diese Datei enthält geplante Features und Verbesserungen
---

## ✅ Erledigte Features

Avatar Access Control — ✅ Erledigt (Subnet-Modus, Publish-Toggle, Auth-basierter Zugriff)

## 🎯 Priorität 1 (Next)

Avatar sperren — Admin kann einzelne Avatare sperren. Gesperrter Avatar wird durch Default ersetzt, User sieht Hinweis.

## 🔮 Priorität 2 (Later)

Audit Log — Neuer Admin-Tab mit Aktions-Historie (Login, Upload, Admin-Aktionen). Filter nach User/Aktion/Zeitraum, Auto-Cleanup nach X Tagen.

Rate Limiting — Login-Brute-Force und API-Missbrauch begrenzen (z.B. slowapi)

## 💭 Ideen (Backlog) - Komplex / Needs Design

Responsive Design für Mobile

Admin: "Resize All" — alle existierenden Avatare mit den aktuellen avatar_sizes neu generieren (Originale sind vorhanden). Nützlich falls Sizes nachträglich geändert werden.

Default-Avatar-Generator — Automatisch generierte Avatare aus dem Email-Hash wenn kein Avatar gesetzt ist. Kein Standard-Initialen-Look, sondern was Ausgefallenes (z.B. Pixel-Art Faces, Geometric Patterns, Blob Creatures, Gradient Meshes). Deterministisch, serverseitig mit Pillow.
