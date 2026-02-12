# RepoBench-Evaluierungsskripte

Dieses Projekt enthält zwei Python-Skripte, um die Qualität der Code-Vervollständigung auf einem gemeinsamen Datensatz (`repobench_200.jsonl`) zu evaluieren:

- `run_cloud_test.py`: führt den Benchmark gegen OpenAI `gpt-5-mini` aus
- `run_local_test.py`: führt den Benchmark gegen einen lokalen Ollama-Endpunkt (`qwen2.5-coder:7b-instruct-q4_K_M`) aus

## Dateien

- `run_cloud_test.py` - Cloud-Benchmark inkl. Token-/Kosten-Tracking
- `run_local_test.py` - Lokaler Benchmark inkl. Latenz-/Accuracy-Tracking
- `requirements.txt` - Python-Abhängigkeiten
- `repobench_200.jsonl` - Benchmark-Datensatz (muss im Projektverzeichnis liegen)

## Voraussetzungen

- Python 3.9+
- Abhängigkeiten aus `requirements.txt`

Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

## Konfiguration

### Cloud-Skript (`run_cloud_test.py`)

- Das Modell ist auf `gpt-5-mini` gesetzt.
- Aktuell enthält das Skript einen hartkodierten API-Key.
- Empfehlung: API-Key über die Umgebungsvariable `OPENAI_API_KEY` einlesen.

### Lokales Skript (`run_local_test.py`)

- Erwartet einen OpenAI-kompatiblen lokalen Endpunkt:
  - `BASE_URL = "http://nuc-ai:11434/v1"`
- Verwendet das Modell:
  - `qwen2.5-coder:7b-instruct-q4_K_M`
- Stelle sicher, dass der Ollama-/OpenAI-kompatible Server von diesem Rechner erreichbar ist.

## Nutzung

Cloud-Evaluierung starten:

```bash
python run_cloud_test.py
```

Lokale Evaluierung starten:

```bash
python run_local_test.py
```

Beide Skripte unterstützen das Fortsetzen unterbrochener Läufe, indem bereits geschriebene CSV-Zeilen gezählt werden.

## Ausgaben

### Cloud-Ausgaben

- `cloud_gpt5mini_results.csv`
- `cloud_gpt5mini_details.jsonl`
- `cloud_gpt5mini_run_meta.json`

### Lokale Ausgaben

- `local_qwen25coder7b_results.csv`
- `local_qwen25coder7b_details.jsonl`
- `local_qwen25coder7b_run_meta.json`

Jeder Lauf erzeugt:

- CSV: Metriken pro Aufgabe
- JSONL: Detaillierte Logs pro Aufgabe
- Meta-JSON: Aggregierte Accuracy-/Latenzwerte (und Kosten im Cloud-Fall)

## Hinweise

- Lege `repobench_200.jsonl` in dasselbe Verzeichnis wie die Skripte.
- Falls ein Lauf unterbrochen wird, setzt ein erneuter Start beim nächsten noch nicht verarbeiteten Datensatz fort (basierend auf der CSV-Zeilenanzahl).
