# AI Ops — lokale Aktivierung

Deploy-Ziel: C:/Zippoworkz. Projekt bleibt Workspace/codex_ingest/creator-collab.
START_LOCAL_AI.ps1 ist die gewartete Einstiegsschicht; die kompatiblen ZIPPOWORKZ_*.ps1/Python-Dateien werden nach _system kopiert, START_ZIPPOWORKZ.cmd in den Root. PERMISSIONS_POLICY.json muss im _system-Verzeichnis liegen.

Der Worker verwendet die bestehende Datenbank, keine neue Architektur. Er setzt eine allowlist-basierte, begrenzte lokale Queue um. Start/Pause/Resume/Stop sind im gemeinsamen Dashboard unter /ai-ops erreichbar. Sobald alle Schritte DONE/BLOCKED sind: STOP. VPS ist noch nicht verbunden.

**Keine offenen Shell-/Dateibefehle aus Modellantworten.** Rollenmodelle sind nicht Voraussetzung; vorhandenes qwen3:8b ist der verifizierte Fallback. Keine Downloads. Git-Fetch maximal 12s pro Unterbefehl, nicht interaktiv; keine Worktree-Mutation. Neue Remote-Stände werden für separate Codex-Prüfung gemeldet.

Die Betriebshistorie war im GitHub-Archiv nicht enthalten. Das Dashboard initialisiert regulär Schema 5, aber erfindet keine alten Assets, Post-IDs oder Analytics. Das Owner-Backup fehlt noch.

Tests: `python -m unittest tests.test_ai_ops tests.test_control_plane tests.test_remote_auth tests.test_background_runtime tests.test_dashboard tests.test_standalone_runtime`.
Diese Quellprüfung ist lokal; nichts veröffentlichen. Produktionsstatus nicht mit Testdaten ersetzen.
