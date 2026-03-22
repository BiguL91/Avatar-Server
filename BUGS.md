# Bug Tracker

Offene Probleme und bekannte Bugs

---

## 🚨 Priorität: Hoch

_(Keine offenen)_




## ⚠️ Priorität: Mittel


## 📋 Priorität: Niedrig


## 🐛 Weitere Bugs

## 👀 Weitere Beobachtung

## ✅ Gelöste Bugs

- ✅ **Settings-Änderungen ohne Funktion** - `get_setting()` wurde nirgends aufgerufen, Code las direkt von ENV-Variablen statt aus DB. Alle Stellen (upload.py, image.py, avatar.py) auf `await get_setting(db, key)` umgestellt.
- ✅ **Avatare Bearbeiten/Recrop funktioniert nicht** - `handleRecrop()` in AvatarHistory.tsx nutzte `fetch()` statt `apiFetch()` → kein JWT-Header → 401. Auf `apiFetch()` umgestellt.
- ✅ **Avatar auswählen/aktivieren ohne Funktion** - `handleActivate()` und `handleDelete()` in AvatarHistory.tsx nutzten ebenfalls `fetch()` statt `apiFetch()`. Auf `apiFetch()` umgestellt.
- ✅ **Crop-Editor: Runder Bildausschnitt passt sich nicht beim Zoomen an** - Komplett neuer CropEditor: Fester Kreis mit verschiebbarem Bild dahinter (wie GitHub/Discord)
- ✅ **Crop-Editor: Zu viel Scrollen beim Zoomen nötig** - Durch neuen Editor-Ansatz kein Scrollen mehr nötig, Recrop-Modal auf 80vw vergrößert

## 📝 Hinweise

- Neue Bugs bitte hier dokumentieren mit Status 🔍 Offen
- Gelöste Bugs in "Gelöste Bugs" Sektion verschieben mit Versionsnummer
- Veröfentlichte Bugs können hier gelöscht werden
- Prioritäten nach Nutzer-Impact setzen
- Bei Fix: Status aktualisieren und Commit-Hash angeben
