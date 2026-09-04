# Kostenloser Remote-Zugriff für Creator Ops

## Ziel

Creator Ops kann vorübergehend von einem anderen PC oder Smartphone im Browser
erreicht werden, ohne Hosting-Abo, Domainkauf oder Router-Portfreigabe.

## Lösung

- Das lokale Creator-Ops-Dashboard und dieselbe SQLite-Datenbank bleiben die
  Source of Truth.
- Passwort-Login läuft direkt im bestehenden Python-Server.
- Session-Cookie, CSRF-Schutz, Sicherheitsheader und einfache
  Login-Rate-Limitierung schützen den Review-Zugang.
- Cloudflare Quick Tunnel stellt nur den verschlüsselten Transport und eine
  temporäre `*.trycloudflare.com`-Adresse bereit.
- Ohne `CREATOR_OPS_PASSWORD` funktioniert der lokale Modus unverändert offen.

## Kosten und Grenzen

Die vorgesehene Übergangslösung verursacht keine Projektkosten. Quick Tunnels
sind jedoch nur für Test/Entwicklung gedacht: keine feste URL, keine SLA und
kein dauerhaftes 24/7-Hosting. Der Heim-PC und beide Prozesse müssen laufen.

## Installation und Start

1. `cloudflared` aus der offiziellen Cloudflare-Dokumentation installieren oder
   die ausführbare Datei lokal unter `creator-collab/tools/cloudflared.exe`
   ablegen. `tools/` wird nicht in Git übernommen.
2. Prüfen, dass Port 4180 nicht bereits von einem alten Dashboardprozess belegt
   ist.
3. Im Ordner `creator-collab` starten:

```powershell
.\run_remote_free.ps1
```

4. Ein neues Passwort mit mindestens 12 Zeichen eingeben. Es wird nur für
   diesen Prozess gesetzt und nicht in GitHub oder SQLite gespeichert.
5. Die ausgegebene `https://…trycloudflare.com`-Adresse öffnen und anmelden.

## Sicherheitsverhalten

Wenn `CREATOR_OPS_PASSWORD` gesetzt ist:

- Dashboard, Bilder und Review-API sind loginpflichtig.
- Das Session-Cookie ist `HttpOnly` und `SameSite=Strict`.
- Über den HTTPS-Tunnel erhält es zusätzlich `Secure`.
- Freigabe und Logout verlangen einen gültigen, servergebundenen CSRF-Token.
- Sechs falsche Loginversuche innerhalb von fünf Minuten sperren weitere
  Versuche für diesen Client vorübergehend.
- Sicherheitsheader blockieren Framing und begrenzen geladene Ressourcen.
- `/api/health` bleibt als minimale Statusantwort öffentlich.

## Beenden

Im Terminal `Strg+C` drücken. Das Startskript beendet anschließend auch den
lokalen passwortgeschützten Dashboardprozess und entfernt das Passwort aus der
Prozessumgebung.

## Später

Erst wenn der Workflow dauerhaft genutzt wird, einen Named Tunnel mit stabiler
Domain/Access oder ein separates Hosting bewerten. Vorher keine Kosten auslösen.
