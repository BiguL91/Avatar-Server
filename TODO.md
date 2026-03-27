# TODO - Geplante Features

Diese Datei enthält geplante Features und Verbesserungen
---

## 🎯 Priorität 1 (Next)

OIDC Session Sync — Bidirektionale Session-Synchronisierung mit Keycloak:
- **Refresh Token Flow:** `refresh_token` von Keycloak speichern (DB, nicht Frontend). Frontend pollt alle X Minuten → Backend fragt Keycloak ob Session noch gültig. Wenn ja → neuen App-JWT ausstellen + Keycloak-Session verlängern. Wenn nein → automatisch ausloggen.
- **Backchannel Logout:** Neuer Endpoint `POST /api/auth/oidc/backchannel-logout`. Keycloak sendet signierten `logout_token` wenn User sich dort abmeldet → Avatar Server invalidiert Session sofort. Muss in Keycloak als Backchannel Logout URL konfiguriert werden.
- Betrifft: OIDC Callback (Refresh Token speichern), neues DB-Feld, 2 neue Endpoints, Frontend-Polling, Keycloak-Config.

## 🔮 Priorität 2 (Later)

Audit Log — Neuer Admin-Tab mit Aktions-Historie (Login, Upload, Admin-Aktionen). Filter nach User/Aktion/Zeitraum, Auto-Cleanup nach X Tagen.

Rate Limiting — Login-Brute-Force und API-Missbrauch begrenzen (z.B. slowapi)

## 💭 Ideen (Backlog) - Komplex / Needs Design

Responsive Design für Mobile

Admin: "Resize All" — alle existierenden Avatare mit den aktuellen avatar_sizes neu generieren (Originale sind vorhanden). Nützlich falls Sizes nachträglich geändert werden.

Default-Avatar-Generator — Automatisch generierte Avatare aus dem Email-Hash wenn kein Avatar gesetzt ist. Kein Standard-Initialen-Look, sondern was Ausgefallenes (z.B. Pixel-Art Faces, Geometric Patterns, Blob Creatures, Gradient Meshes). Deterministisch, serverseitig mit Pillow.
