# Sitzungsjournal

- Datum/Zeit: 14.09.2026, 18:48 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: genau einen Milo-Testpost auf TikTok veröffentlichen und
  den öffentlichen Zustand belegen.

## Ausgangslage

Das referenzgebundene 9:16-PNG war PUBLIC_SFW und lokal review-ready. Die
TikTok API war nicht autorisiert; im Browser bestand jedoch eine eingeloggte
offizielle Sitzung des richtigen Kontos `@miloderzug`. Der Owner erteilte
direkt vor dem finalen Publish eine ausdrückliche Bestätigung.

## Durchgeführt

- Offizielle TikTok-Studio-Fotouploadseite des Kontos `@miloderzug` verwendet.
- Genau das freigegebene Milo-9:16-PNG hochgeladen.
- Titel, Caption und Hashtags aus dem Posting-Kit eingesetzt.
- TikToks native Kennzeichnung für KI-generierten Inhalt aktiviert und den
  dazugehörigen Hinweis bestätigt.
- Sichtbarkeit `Alle` und Zeitpunkt `Jetzt` vor dem Publish geprüft.
- Nach Owner-Bestätigung genau einmal `Veröffentlichen` ausgeführt.
- Den von TikTok erzeugten Permalink separat geöffnet und den Post verifiziert.
- Lokalen Channel-State und aktuelle Handoff-Dokumente aktualisiert.

## Verifiziert

- Öffentlicher Link:
  <https://www.tiktok.com/@miloderzug/photo/7685433578976709911>.
- TikTok-Medien-ID: `7685433578976709911`.
- Richtige Creator-Identität sichtbar: `Milo der Zug` / `miloderzug`.
- Titel/Caption/Hashtags sichtbar.
- Native Kennzeichnung sichtbar:
  `Von Creator*in als KI-generiert gekennzeichnet`.
- Startwerte beim ersten Aufruf: 0 Likes, 0 Kommentare; dies sind echte
  unmittelbare Plattformwerte und keine 24h-Analytics.
- Keine zweite Sendung und kein Retry.

## Entscheidungen

- Native Web-Veröffentlichung wurde genutzt; dies ist kein TikTok-API-Proof.
- Ein Clientschlüssel/Kundengeheimnis allein genügt nicht für User-Publishing.
- Das im Chat offengelegte Geheimnis wurde nicht gespeichert oder verwendet.
- Analytics werden erst zum fälligen Fenster als echte Messung erfasst.

## Offen oder blockiert

- TikTok-Kundengeheimnis im Developer Portal rotieren und den neuen Wert nur
  im sicheren Secret-Provider hinterlegen.
- Nutzer-OAuth/Access-Token sowie Posting-Scope fehlen für einen API-Pfad.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| T-015 | ACTIVE | DONE | öffentlicher Post + Medien-ID + KI-Label | none |
| M-16 | LOCAL_CONTENT_READY | TIKTOK_NATIVE_PROVEN | genau ein sichtbarer Milo-Post | 24h analytics |

## Nächster Agent

1. Keinen weiteren Testpost senden.
2. Nach 24 Stunden echte TikTok-Werte erfassen.
3. API-OAuth nur nach Secret-Rotation in einem separaten sicheren Run angehen.
