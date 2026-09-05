# Style Reference Policy — mz.poke

`mz.poke` ist ausschließlich eine interne, gelegentliche Format- und
Tonalitätsreferenz. Es wird keine Identität, Pose, Caption, Bildkomposition oder
Sequenz kopiert und keine Kooperation behauptet.

- Zielanteil: ungefähr 10–15 % im rollierenden Mix, niemals als Pflichtquote.
- Leona: Fashion, geschmackvolle SFW-Teaser, Humor oder Personality.
- Mara: nur persona-passend; deutscher Hof-/Werkstattkontext bleibt dominant.
- Öffentliche Inhalte bleiben SFW und `PUBLIC_SFW`.
- Bestehende Inhalte werden nicht rückwirkend markiert.
- Markierung liegt intern in `experiments` mit `variable=style_reference` und
  `variant=mz_poke`.
- Vergleich erfolgt später ausschließlich gegen echte Analytics derselben
  Persona, niemals gegen fremde Accounts oder Mock-Daten.
- Ohne ausreichende echte Daten bleibt das Ergebnis `unknown`.

CLI-Beispiel für einen zukünftigen, ausdrücklich als Experiment geplanten Post:

```powershell
python -m creator_ops.cli --db data/review_dashboard.db style-reference-set `
  --content-id <ID> --strength light --format fashion
```
