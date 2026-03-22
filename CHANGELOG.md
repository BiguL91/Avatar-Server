# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## v0.1.3 (2026-03-22)

### Hinzugefügt
- **App-Logo** — Eigenes Logo auf der Login-Seite und als Favicon im Browser-Tab
- **App-Name konfigurierbar** — `APP_NAME` zur Laufzeit änderbar, wird dynamisch auf Login-Seite und im Browser-Tab angezeigt
- **JWT-Settings** — `JWT_SECRET` (maskiert) und `JWT_EXPIRE_MINUTES` in der Admin-Konsole änderbar
- **Settings-Gruppen** — Admin-Konsole zeigt Einstellungen in aufklappbaren Gruppen (Avatar, Login & Sicherheit, OIDC/SSO, Allgemein)
- **Bool-Toggles** — Boolean-Settings in der Admin-Konsole als klickbare Toggles statt Textfelder
- **Fehleranzeige** — Validierungsfehler werden direkt unter dem betroffenen Setting angezeigt
- **Discovery-URL Prüfung** — `OIDC_DISCOVERY_URL` muss HTTPS sein (beim Start und in der Admin-Konsole)

---

## v0.1.2 (2026-03-22)

### Hinzugefügt
- **Trusted Proxy** — Neuer ENV `TRUSTED_PROXY` (IP oder Subnetz), erlaubt nur Requests vom konfigurierten Reverse-Proxy. Echte Client-IP wird aus `X-Forwarded-For` Header übernommen. Zur Laufzeit über Admin-Konsole änderbar
- **OIDC Security Checks** — Server startet nicht wenn OIDC aktiviert ist ohne HTTPS `BASE_URL`, ohne `TRUSTED_PROXY` oder mit aktivem Dev-Mode. Gleiche Prüfungen auch zur Laufzeit in der Admin-Konsole
- **Dev-Mode zur Laufzeit** — `DEV_MODE` ist jetzt über die Admin-Konsole änderbar. Gegenseitige Sperre mit OIDC
- **BASE_URL zur Laufzeit** — `BASE_URL` ist jetzt über die Admin-Konsole änderbar
- **JWT-Secret Warnung** — Warnung beim Start wenn `JWT_SECRET` auf dem Default-Wert steht

---

## v0.1.1 (2026-03-22)

### Hinzugefügt
- **Legacy-Login Toggle** — Neuer ENV `LEGACY_LOGIN` (default: `true`), deaktiviert den Email+Passwort Login komplett wenn auf `false` gesetzt (Backend blockt mit 403, Frontend versteckt das Formular)
- **Docker Hub Link** — README verweist auf fertigen Build auf Docker Hub

### Behoben
- **Typo** — `OIDC_ENABLED=fals` → `false` in docker-compose.yml

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
