# Meta-Media-Runbook (ein Paket)

Der lokale Media-Origin ist eine kleine, zeitlich begrenzte JPEG-Ausgabe für
den offiziellen Instagram-Adapter. Er liefert nur die drei ausgewählten
Top-Picks eines Content-Pakets, niemals das Dashboard oder den gesamten
Workspace. Der Prozess startet keinen Tunnel und sendet nichts an Meta.

## 1. Vorbereiten

1. Im Dashboard ein freigegebenes SFW/PUBLIC_SFW-Paket auswählen.
2. Für die drei Top-Picks echte JPEG-Dateien als Derivate bereitstellen. Die
   aktuelle Review-Reserve besteht teilweise aus PNGs; diese werden nicht
   stillschweigend umgewandelt.
3. Einen eigenen, öffentlichen HTTPS-Origin bereitstellen. Eine lokale
   `127.0.0.1`- oder LAN-Adresse reicht für Meta nicht. `cloudflared` ist in
   dieser Installation nicht vorhanden und wird vom Projekt nicht automatisch
   installiert oder gestartet.

## 2. Manifest erzeugen

Im Projektordner mit dem gebündelten Python ausführen. Alle Werte bleiben
lokal; keine Tokens oder App-Geheimnisse gehören in die Manifestdatei.

```powershell
$py = "C:\Users\ZiPPo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
Set-Location "C:\Zippoworkz\Workspace\codex_ingest\creator-collab"
& $py -m creator_ops.public_media `
  --content-id <CONTENT_ID> `
  --jpeg-map <PATH_TO_EXPLICIT_JPEG_MAP.json> `
  --base-url "https://<PUBLIC_ORIGIN>" `
  --manifest-output "output/meta-public-media/<CONTENT_ID>/manifest.json" `
  --native-ai-disclosure-confirmed
```

Die Map enthält ausschließlich die ausgewählten Asset-IDs und ihre lokalen
Derivatpfade. Das Kommando meldet `READY` nur nach Byte-/Rechte-/SFW-Prüfung.
Danach `CREATOR_OPS_META_MEDIA_MANIFEST` auf die erzeugte Manifestdatei zeigen
lassen und die Meta-Zugangsdaten über den sicheren Secret-Provider setzen.

## 3. Dashboard prüfen und senden

Auf `/channels` zuerst `Einzelpaket prüfen` klicken. Erst wenn der Preflight
`READY` meldet, darf für genau dieses Paket `Dieses Paket senden` genutzt
werden. Der globale Scheduler bleibt unverändert aus. Nach einem Versand sind
Media-ID, Permalink und Receipt im bestehenden Queue-/Publikationsstatus
maßgeblich.

## Sicherheitsgrenzen

- Nur HTTPS-URLs auf dem erlaubten Host; keine URL mit Token oder Cookie.
- Der Listener läuft ausschließlich auf `127.0.0.1` und endet spätestens nach
  sechs Stunden.
- Kein automatischer Tunnel, keine neuen Accounts, keine Kosten.
- Bei Timeout oder unklarem `media_publish` niemals blind erneut senden; zuerst
  die vorhandene Reconciliation verwenden.
- App-ID und App-Geheimcode ersetzen keinen Instagram-Nutzer-Token. Die im Chat
  offengelegten Zugangswerte sollten im Meta-Developer-Konto rotiert werden.
