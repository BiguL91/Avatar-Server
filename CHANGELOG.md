# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## v0.1.0 (2026-03-21) — Initial Release

Erster öffentlicher Release des Avatar Servers.

### 🎨 Features

#### Avatar-Verwaltung
- **Upload-UI** — Drag & Drop, Datei-Auswahl und URL-Import für Bilder
- **Crop-Editor** — Fester Kreis-Overlay mit verschiebbarem Bild, Zoom-Slider und Scroll-Zoom (wie GitHub/Discord)
- **Bildverarbeitung** — EXIF-Korrektur, Crop, Resize in 6 Größen (32–512px) als WebP, Transparenz wird beibehalten
- **Upload-Historie** — Alle Uploads werden gespeichert, Original bleibt erhalten, Recrop jederzeit möglich
- **Upload-Limit** — Max 6 Avatare pro User, max 10MB Dateigröße, Original auf FullHD (1920px) begrenzt
- **Avatar-Verwaltung** — Aktiven Avatar wählen, alte Avatare löschen, Bilder nachbearbeiten
- **Vorschau** — Aktiver Avatar in 3 Größen (64/128/256px) mit Pop-Animation, öffentliche URL zum Kopieren
- **Vorschau-Größenwahl** — Klick auf Vorschau-Avatar aktualisiert die öffentliche URL mit `?s=`-Parameter

#### Öffentliche API
- **Avatar-API** — `GET /avatar/{hash}?s=64` öffentlich, erkennt MD5/SHA256 automatisch
- **PNG-Endpoint** — `GET /avatar/{hash}.png?s=256` liefert PNG on-the-fly (WebP→PNG Konvertierung via Pillow)
- **Cache-Headers** — `Cache-Control` Header konfigurierbar (Standard: 1 Stunde)

#### Authentifizierung
- **OIDC/SSO** — Generischer Authorization Code Flow, funktioniert mit jedem OIDC-Provider (Keycloak, Authentik, Authelia, etc.) über Discovery-URL
- **Lokaler Login** — Email + Passwort, SSO als Standard wenn aktiviert, lokaler Login als "Legacy Login"
- **OIDC Claim-Mapping** — Alle Claim-Namen frei konfigurierbar (email, nickname, picture, groups)
- **OIDC Admin-Gruppen** — Admin-Rechte über konfigurierbaren Gruppen-Claim aus dem IdP
- **OIDC Logout** — Vollständiger Logout über `end_session_endpoint` des IdP
- **OIDC Picture-Sync** — Avatar-URL (WebP + PNG) wird automatisch als Attribut an den IdP zurückgeschrieben (via Keycloak Admin API mit Service Account), Trigger nur bei Zustandsänderung
- **JWT** — Bearer-Token mit konfigurierbarer Ablaufzeit
- **Dev-Modus** — OIDC umgehen mit Fake-User für lokale Entwicklung

#### Administration
- **Admin-Konsole** — Benutzerverwaltung (Liste, Anlegen, Bearbeiten, Löschen, Admin-Toggle, Aktivieren/Deaktivieren)
- **Settings-Editor** — Alle Einstellungen zur Laufzeit änderbar (ENV als Defaults, DB-Overrides)
- **Admin-User aus ENV** — `ADMIN_EMAIL` + `ADMIN_PASSWORD`, wird beim ersten Start automatisch angelegt
- **Admin-Berechtigung** — Admin-Konsole nur für Admins sichtbar, API-Endpunkte mit 403 geschützt

#### UI & UX
- **i18n** — Mehrsprachigkeit (DE/EN), Standardsprache per ENV konfigurierbar, erweiterbar
- **Dark/Light Mode** — Manueller Toggle, System-Preference als Default, Wahl in localStorage
- **UI-Animationen** — Dropzone-Pulsieren, Upload-Spinner, Shake bei Fehler, Avatar-Pop-In
- **CSS-Variablen** — Komplett variablenbasiert, Dark Mode via `prefers-color-scheme`
- **Bestätigungsdialog** — Eigene ConfirmDialog-Komponente mit Animation und Escape-Taste
- **User-Menü** — Avatar + Username oben rechts, Dropdown mit Einstellungen/Admin/Abmelden
- **Kontoeinstellungen** — Profilanzeige, Sprachwechsel, Account komplett löschen
- **Erfolgs-Toast** — Slide-in Benachrichtigung bei erfolgreichen Admin-Änderungen

#### Infrastruktur
- **Docker** — Multi-Stage Dockerfile (Node + Python), docker-compose.yml, SPA-Fallback
- **SQLite** — Metadaten über SQLAlchemy + aiosqlite, Auto-Migration für neue Spalten
- **Settings-System** — ENV als Defaults, DB-Overrides zur Laufzeit über Admin-Konsole

### 🔒 Security

- **SSRF-Schutz** — `/fetch-image` Endpoint validiert URLs (nur HTTP/S, blockiert private/loopback/link-local IPs, keine Redirects), erfordert Authentifizierung
- **Path-Traversal-Schutz** — Alle Datei-Endpoints validieren Eingaben (Regex für Hash/Filename, `resolve()` + `is_relative_to()`)
- **Hash-Validierung** — Avatar-API akzeptiert nur Hex-Zeichen in Hashes
- **SPA-Fallback abgesichert** — Path-Traversal-Schutz im statischen File-Serving
- **CORS** — Dynamische Origins aus `BASE_URL`, spezifische Methods/Headers
- **Secret-Maskierung** — `oidc_client_secret` in Admin-API-Responses maskiert
- **Sichere Defaults** — `dev_mode` und `debug` standardmäßig deaktiviert
- **CSRF-Schutz** — OIDC State-Token als signiertes JWT (kein Server-Side Storage nötig)
