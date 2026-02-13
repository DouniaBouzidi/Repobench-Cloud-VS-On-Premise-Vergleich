# RepoBench Evaluierung (Cloud vs. On-Premise)

Dieses Repository enthält Python-Skripte zur Auswertung von Code-Vervollständigung mit dem Datensatz `repobench_200.jsonl`.

- `make_repobench_200.py`: erzeugt `repobench_200.jsonl` aus RepoBench Java v1.1
- `run_cloud_test.py`: Benchmark in der Cloud mit `gpt-5-mini`
- `run_local_test.py`: Benchmark gegen einen On-Premise Ollama-Endpunkt mit `qwen2.5-coder:7b-instruct-q4_K_M`

## Inhalt

- `make_repobench_200.py`: Datensatz-Erstellung (200 Samples)
- `run_cloud_test.py`: Cloud-Ausführung inkl. Token- und Kostenauswertung
- `run_local_test.py`: On-Premise-Ausführung inkl. Latenz- und Qualitätsmetriken
- `requirements.txt`: Python-Abhängigkeiten (`openai`, `datasets`)
- `repobench_200.jsonl`: Eingabedatensatz für die Benchmarks
- `ergebnisse/`: erzeugte Ergebnisdateien früherer Läufe

## Voraussetzungen

- Python 3.9+
- Abhängigkeiten aus `requirements.txt`
  Installation läuft durch:

```bash
pip install -r requirements.txt
```

## Datensatz erzeugen

Wenn `repobench_200.jsonl` noch nicht vorhanden ist, zuerst ausführen:

```bash
python make_repobench_200.py
```

Danach liegt `repobench_200.jsonl` im Projektordner.

## Konfiguration

### Cloud-Skript (`run_cloud_test.py`)

- Modell: `gpt-5-mini`
- API-Key aktuell im Skript gesetzt
- Empfehlung: API-Key über `OPENAI_API_KEY` als Umgebungsvariable nutzen

### On-Premise-Skript (`run_local_test.py`)

- API-Endpunkt: `http://nuc-ai:11434/v1`
- Modell: `qwen2.5-coder:7b-instruct-q4_K_M`
- Voraussetzung: On-Premise-Endpunkt ist vom Rechner erreichbar

## Ausführung

Cloud-Benchmark starten:

```bash
python run_cloud_test.py
```

On-Premise-Benchmark starten:

```bash
python run_local_test.py
```

Hinweis: Beide Skripte können unterbrochene Läufe automatisch fortsetzen (über vorhandene CSV-Zeilen).

## Ergebnisdateien

Cloud:

- `cloud_gpt5mini_results.csv`
- `cloud_gpt5mini_details.jsonl`
- `cloud_gpt5mini_run_meta.json`

On-Premise:

- `local_qwen25coder7b_results.csv`
- `local_qwen25coder7b_details.jsonl`
- `local_qwen25coder7b_run_meta.json`

Erklärung:

- `*.csv`: kurze Tabelle mit einem Ergebnis pro Aufgabe
- `*.jsonl`: Details pro Aufgabe (eine Zeile = eine Aufgabe)
- `*_meta.json`: Zusammenfassung vom ganzen Lauf (z. B. Genauigkeit, Zeit, Kosten)

## Hinweise

- `make_repobench_200.py` und die Benchmark-Skripte sollten im selben Projektordner liegen.
- `repobench_200.jsonl` muss im selben Ordner wie die Benchmark-Skripte liegen.
- Bei erneutem Start wird ab dem nächsten noch nicht verarbeiteten Datensatz fortgesetzt.
