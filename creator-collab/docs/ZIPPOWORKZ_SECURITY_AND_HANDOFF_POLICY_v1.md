# ZippoWorkz Security & Handoff Policy v1

- Stand: 2026-09-14
- Root: `C:\Zippoworkz`

## Betriebsmodus

`DO → TEST → VERIFY → LOG → CONTINUE`

Nur echte Owner-Gates halten eine betroffene Aktion an. Sichere lokale Arbeit läuft weiter.

## Owner-Gates

- jede kostenpflichtige Aktion, jeder Kauf und jedes Abonnement
- Aktionen auf privaten Accounts
- neue Verträge oder verbindliche finanzielle/rechtliche Zusagen
- sensible oder unklare Kommunikation
- Publishing von noch nicht `OWNER_APPROVED`em Inhalt
- destruktive Löschaktionen ohne vorheriges Backup
- normale Passwortänderungen
- finale Account-/2FA-/Identitätsbestätigung

## Secrets

1. Echte Werte stehen nie in Git, Markdown, Logs, Handoffs, Dashboard, Tests oder Chat.
2. Anwendungscode verwendet ausschließlich `secret://...`-Aliase.
3. Zugriff erfolgt über den austauschbaren `SecretProvider` und `SecretBroker`.
4. Die Runtime-Umgebung ist nur Fallback, nicht langfristige Source of Truth.
5. Vor jedem Push läuft der lokale Secret-Leak-Check.
6. Das Audit enthält Alias, Zeitpunkt, Agent und Ergebnis – niemals den Wert.
7. Recovery-Codes liegen getrennt und verschlüsselt.

## Einheitliche Übergabe

Jede Rolle dokumentiert Run-ID, Agent, Zeit, Ziel, Inputs, Änderungen, Tests, externe Aktionen, verwendete Secret-Aliase, Blocker, Owner-Aktionen, nächsten Agenten, nächsten Schritt und Status.

Zulässige Statuswerte: `DONE`, `PAUSED`, `NEEDS_OWNER_ACTION`, `FAILED_SAFE`.

`Current` wird atomar geschrieben; frühere Übergaben werden datiert archiviert. Secret-Werte machen eine Übergabe ungültig.

## Safe Mode

Bei Unsicherheit: keine externen Writes, Käufe, Publishes oder Accountänderungen. Lokale Analyse, Tests, Reparatur, Dokumentation und Handoff bleiben erlaubt.

## Harte Grenzen

Keine Käufe ohne Owner, keine privaten Accounts, keine Secret-Werte in Projektartefakten, kein Repository-Löschen, keine Fake-Erfolge, keine Umgehung von Owner-/Security-Gates und keine wichtigen Löschungen ohne Backup.
