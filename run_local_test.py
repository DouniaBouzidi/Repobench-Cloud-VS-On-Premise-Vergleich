"""
Lokales Testskript
Evaluierung von Qwen2.5-Coder 7B (On-Premise) für Code-Vervollständigung
"""

import json, time, csv, os
from datetime import datetime
from openai import OpenAI

# ===================== KONFIGURATION =====================
DATASET = "repobench_200.jsonl"          # Gleicher Benchmark wie Cloud-Test

# Ollama-API auf Intel NUC (lokale Infrastruktur)
BASE_URL = "http://nuc-ai:11434/v1"      # Lokaler Ollama-Server
MODEL = "qwen2.5-coder:7b-instruct-q4_K_M"  # Lokales Code-Modell

# Ausgabedateien für On-Premise-Ergebnisse
OUT_CSV = "local_qwen25coder7b_results.csv"      # Tabellarische Ergebnisse
OUT_JSONL = "local_qwen25coder7b_details.jsonl"  # Detaillierte Protokolle
OUT_META = "local_qwen25coder7b_run_meta.json"   # Aggregierte Metriken

# ===================== HILFSFUNKTIONEN =====================
def now_iso():
    """Gibt aktuellen UTC-Zeitstempel im ISO-Format zurück"""
    return datetime.utcnow().isoformat() + "Z"

def normalize_line(s: str) -> str:
    """Entfernt Zeilenumbrüche am Ende, behält Einrückung bei"""
    return (s or "").rstrip("\r\n")

def norm_for_eval(s: str) -> str:
    """Normalisiert Whitespace für fairen Code-Vergleich (RQ1)"""
    return normalize_line(s).expandtabs(4).strip()

def first_nonempty_line(text: str) -> str:
    """Findet erste nicht-leere Zeile in Modellantwort"""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        if line.strip() != "":
            return line
    return ""

def ensure_header(csv_path: str):
    """Erstellt CSV-Datei mit Kopfzeile für On-Premise-Metriken"""
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "id",                  # Aufgaben-ID
                "exact_correct",       # RQ1: Exakte Zeichen-Übereinstimmung
                "strict_correct",      # RQ1: Exakte Übereinstimmung (normalisiert)
                "contains_correct",    # RQ1: Inhaltliche Übereinstimmung
                "latency_s",           # RQ2: Antwortzeit (kritisch für On-Premise)
                "finish_reason",       # API-Abschlussgrund
                "error"                # Fehlermeldung
            ])

def count_done(csv_path: str) -> int:
    """Zählt bereits verarbeitete Aufgaben für Fortsetzung"""
    if not os.path.exists(csv_path):
        return 0
    with open(csv_path, "r", encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)

def call_with_retry(client, messages, max_tries=5):
    """Retry-Mechanismus für lokale Ollama-API (kürzere Timeouts)"""
    last_err = None
    for attempt in range(1, max_tries + 1):
        try:
            # temperature=0 für deterministische Ergebnisse (On-Premise-Vorteil)
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0 
            )
        except Exception as e:
            last_err = e
            time.sleep(min(5, 1.2 * attempt))  
    raise last_err

# ===================== HAUPTFUNKTION =====================
def main():
    """Hauptfunktion für On-Premise-KI-Evaluation"""
    
    # Ollama-Client initialisieren (kein echter API-Key benötigt)
    client = OpenAI(base_url=BASE_URL, api_key="ollama")
    
    # Vorbereitung: CSV-Header und Fortsetzungslogik
    ensure_header(OUT_CSV)
    done = count_done(OUT_CSV)
    print(f"Lokaler Test: {MODEL} @ {BASE_URL}")
    print(f"Fortsetzen bei Aufgabe {done+1} (bereits: {done})")

    # Datensatz laden (200 Aufgaben)
    with open(DATASET, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    start_epoch = int(time.time())
    start_total = time.time()
    
    # Metriken-Initialisierung für On-Premise
    exact_ok = 0          # RQ1: Exakte Zeichen-Übereinstimmung (zusätzliche Metrik)
    strict_ok = 0         # RQ1: Exakte Übereinstimmungen (normalisiert)
    contains_ok = 0       # RQ1: Inhaltliche Übereinstimmungen
    sum_latency = 0.0     # RQ2: Latenz-Summe (besonders relevant für On-Premise)

    # Hauptschleife: Verarbeitung aller Aufgaben
    for i in range(done, total):
        rec = json.loads(lines[i])
        item_id = i + 1

        # Prompt vorbereiten
        inp = rec.get("input")
        if isinstance(inp, list):
            messages = inp
        else:
            messages = [{"role": "user", "content": str(inp)}]

        # Ground Truth extrahieren und normalisieren
        ideal_raw = normalize_line(rec.get("ideal", ""))
        ideal_eval = norm_for_eval(ideal_raw)

        # Lokaler API-Aufruf mit Zeitmessung (RQ2)
        t0 = time.time()
        output_text = ""
        finish_reason = ""
        error_msg = ""

        try:
            resp = call_with_retry(client, messages)
            output_text = (resp.choices[0].message.content or "")
            finish_reason = getattr(resp.choices[0], "finish_reason", "") or ""
        except Exception as e:
            error_msg = str(e)

        # Latenz berechnen (RQ2: kritisch für On-Premise-Performance)
        latency = round(time.time() - t0, 2)
        sum_latency += latency

        # ========== EVALUIERUNG (RQ1: QUALITÄT) ==========
        # Erste nicht-leere Zeile extrahieren
        out_first_raw = normalize_line(first_nonempty_line(output_text))
        out_first_eval = norm_for_eval(out_first_raw)

        # Drei Accuracy-Metriken für tiefgehende On-Premise-Analyse:
        exact_correct = (out_first_raw == ideal_raw)      # Exakte Zeichen-Übereinstimmung
        strict_correct = (out_first_eval == ideal_eval)   # Normalisierte Übereinstimmung
        
        out_lines = (output_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        contains_correct = any(
            norm_for_eval(line) == ideal_eval
            for line in out_lines
            if line.strip() != ""
        )

        # Metriken aktualisieren
        if exact_correct:
            exact_ok += 1
        if strict_correct:
            strict_ok += 1
        if contains_correct:
            contains_ok += 1

        # ========== ERGEBNISSPEICHERUNG ==========
        # 1. CSV: Tabellarische Metriken pro Aufgabe
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fcsv:
            w = csv.writer(fcsv)
            w.writerow([
                item_id,
                exact_correct,
                strict_correct,
                contains_correct,
                latency,
                finish_reason,
                error_msg
            ])

        # 2. JSONL: Detaillierte Protokolle für On-Premise-Analyse
        with open(OUT_JSONL, "a", encoding="utf-8") as flog:
            flog.write(json.dumps({
                "id": item_id,
                "ts_utc": now_iso(),
                "model": MODEL,
                "base_url": BASE_URL,           # Wichtig: Lokale Infrastruktur
                "messages": messages,
                "ideal": ideal_raw,
                "ideal_norm": ideal_eval,
                "output_full": output_text,
                "output_first_line": out_first_raw,
                "output_first_line_norm": out_first_eval,
                "exact_correct": exact_correct,      # Zusätzliche On-Premise-Metrik
                "strict_correct": strict_correct,
                "contains_correct": contains_correct,
                "latency_s": latency,                # Besonders wichtig für On-Premise
                "finish_reason": finish_reason,
                "error": error_msg
            }, ensure_ascii=False) + "\n")

        # Fortschrittsausgabe mit allen drei Accuracy-Metriken
        print(f"{item_id}/{total} exact={exact_correct} strict={strict_correct} contains={contains_correct} time={latency}s")

    end_epoch = int(time.time())
    total_time = round(time.time() - start_total, 2)

    meta = {
        "model": MODEL,
        "base_url": BASE_URL,
        "dataset": DATASET,
        "items": total,
        "start_epoch": start_epoch,
        "end_epoch": end_epoch,
        "total_time_s": total_time,
        "exact_accuracy": exact_ok / total if total else 0.0,
        "strict_accuracy": strict_ok / total if total else 0.0,
        "contains_accuracy": contains_ok / total if total else 0.0,
        "avg_latency_s": (sum_latency / total) if total else 0.0
    }

    with open(OUT_META, "w", encoding="utf-8") as fmeta:
        json.dump(meta, fmeta, ensure_ascii=False, indent=2)

    print("\n✅ LOCAL FINISHED")
    print("Saved:")
    print(" -", OUT_CSV)
    print(" -", OUT_JSONL)
    print(" -", OUT_META)

if __name__ == "__main__":
    main()