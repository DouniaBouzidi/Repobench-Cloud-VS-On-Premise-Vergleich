"""
Cloud-Testskript
Evaluierung von OpenAI GPT-5-Mini für Code-Vervollständigung (RepoBench Java v1.1)
"""

import json, time, csv, os
from datetime import datetime
from openai import OpenAI

# ===================== KONFIGURATION =====================
# Benchmark-Datensatz mit 200 Java/Spring Boot Aufgaben
DATASET = "repobench_200.jsonl"

# Zu testendes KI-Modell (Cloud-Variante)
MODEL = "gpt-5-mini"

# OpenAI Preisstruktur für Kostenberechnung
IN_PRICE_PER_1M = 0.25  # $ pro 1 Million Input-Tokens
OUT_PRICE_PER_1M = 2.00  # $ pro 1 Million Output-Tokens

# Ausgabedateien für Ergebnisse
OUT_CSV = "cloud_gpt5mini_results.csv"  # Tabellarische Ergebnisse
OUT_JSONL = "cloud_gpt5mini_details.jsonl"  # Detaillierte Protokolle
OUT_META = "cloud_gpt5mini_run_meta.json"  # Aggregierte Metriken


# ===================== HILFSFUNKTIONEN =====================
def call_with_retry(client, messages, max_tries=5):
    """Retry-Mechanismus mit exponentiellem Backoff bei API-Fehlern"""
    last_err = None
    for attempt in range(1, max_tries + 1):
        try:
            return client.chat.completions.create(model=MODEL, messages=messages)
        except Exception as e:
            last_err = e
            time.sleep(min(10, 1.5 * attempt))  # Exponentielles Backoff
    raise last_err


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
    """Erstellt CSV-Datei mit Kopfzeile für Metriken"""
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "id",  # Aufgaben-ID
                    "strict_correct",  # RQ1: Exakte Übereinstimmung
                    "contains_correct",  # RQ1: Inhaltliche Übereinstimmung
                    "latency_s",  # RQ2: Antwortzeit
                    "input_tokens",  # RQ3: Input-Tokens
                    "output_tokens",  # RQ3: Output-Tokens
                    "total_tokens",  # RQ3: Gesamt-Tokens
                    "est_cost_usd",  # RQ3: Geschätzte Kosten
                    "finish_reason",  # API-Abschlussgrund
                    "error",  # Fehlermeldung
                ]
            )


def count_done(csv_path: str) -> int:
    """Zählt bereits verarbeitete Aufgaben für Fortsetzung"""
    if not os.path.exists(csv_path):
        return 0
    with open(csv_path, "r", encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Berechnet API-Kosten basierend auf Token-Verbrauch (RQ3)"""
    return (input_tokens / 1_000_000) * IN_PRICE_PER_1M + (
        output_tokens / 1_000_000
    ) * OUT_PRICE_PER_1M


def call_with_retry(client, messages, max_tries=5):
    """Retry-Mechanismus mit exponentiellem Backoff bei API-Fehlern"""
    last_err = None
    for attempt in range(1, max_tries + 1):
        try:
            return client.chat.completions.create(model=MODEL, messages=messages)
        except Exception as e:
            last_err = e
            time.sleep(min(10, 1.5 * attempt))  # Exponentielles Backoff
    raise last_err


# ===================== HAUPTFUNKTION =====================
def main():
    """Hauptfunktion für Cloud-KI-Evaluation"""

    # API-Key für OpenAI (SICHERHEIT: In Produktion aus Umgebungsvariable!)
    api_key = "sk-proj-xx"
    if not api_key:
        print("❌ OPENAI_API_KEY nicht gesetzt")
        return

    client = OpenAI(api_key=api_key)

    # Vorbereitung: CSV-Header und Fortsetzungslogik
    ensure_header(OUT_CSV)
    done = count_done(OUT_CSV)
    print(f"Cloud-Test: {MODEL}")
    print(f"Fortsetzen bei Aufgabe {done+1} (bereits: {done})")

    # Datensatz laden (200 Aufgaben)
    with open(DATASET, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    start_epoch = int(time.time())
    start_total = time.time()

    # Metriken-Initialisierung
    strict_ok = 0  # RQ1: Exakte Übereinstimmungen
    contains_ok = 0  # RQ1: Inhaltliche Übereinstimmungen
    sum_latency = 0.0  # RQ2: Latenz-Summe
    sum_in_tok = 0  # RQ3: Input-Tokens gesamt
    sum_out_tok = 0  # RQ3: Output-Tokens gesamt
    sum_cost = 0.0  # RQ3: Kosten gesamt

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

        # API-Aufruf mit Zeitmessung (RQ2)
        t0 = time.time()
        output_text = ""
        finish_reason = ""
        error_msg = ""
        in_tok = out_tok = tot_tok = 0
        est_cost = 0.0

        try:
            resp = call_with_retry(client, messages)
            output_text = resp.choices[0].message.content or ""
            finish_reason = getattr(resp.choices[0], "finish_reason", "") or ""

            # Token-Verbrauch für Kostenberechnung (RQ3)
            usage = getattr(resp, "usage", None)
            if usage:
                in_tok = int(
                    getattr(usage, "prompt_tokens", 0)
                    or getattr(usage, "input_tokens", 0)
                    or 0
                )
                out_tok = int(
                    getattr(usage, "completion_tokens", 0)
                    or getattr(usage, "output_tokens", 0)
                    or 0
                )
                tot_tok = int(getattr(usage, "total_tokens", 0) or (in_tok + out_tok))
                est_cost = estimate_cost(in_tok, out_tok)
        except Exception as e:
            error_msg = str(e)

        # Latenz berechnen (RQ2)
        latency = round(time.time() - t0, 2)
        sum_latency += latency

        # ========== EVALUIERUNG (RQ1: QUALITÄT) ==========
        # Erste nicht-leere Zeile extrahieren
        out_first_raw = normalize_line(first_nonempty_line(output_text))
        out_first_eval = norm_for_eval(out_first_raw)

        # Strict Accuracy: Exakte Übereinstimmung nach Normalisierung
        strict_correct = out_first_eval == ideal_eval

        # Contains Accuracy: Ground Truth in irgendeiner Zeile enthalten?
        out_lines = (
            (output_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        )
        contains_correct = any(
            norm_for_eval(line) == ideal_eval
            for line in out_lines
            if line.strip() != ""
        )

        # Metriken aktualisieren
        if strict_correct:
            strict_ok += 1
        if contains_correct:
            contains_ok += 1

        sum_in_tok += in_tok
        sum_out_tok += out_tok
        sum_cost += est_cost

        # ========== ERGEBNISSPEICHERUNG ==========
        # 1. CSV: Tabellarische Metriken pro Aufgabe
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fcsv:
            w = csv.writer(fcsv)
            w.writerow(
                [
                    item_id,
                    strict_correct,
                    contains_correct,
                    latency,
                    in_tok,
                    out_tok,
                    tot_tok,
                    round(est_cost, 8),
                    finish_reason,
                    error_msg,
                ]
            )

        # 2. JSONL: Detaillierte Protokolle für tiefgehende Analyse
        with open(OUT_JSONL, "a", encoding="utf-8") as flog:
            flog.write(
                json.dumps(
                    {
                        "id": item_id,
                        "ts_utc": now_iso(),
                        "model": MODEL,
                        "messages": messages,
                        "ideal": ideal_raw,
                        "ideal_norm": ideal_eval,
                        "output_full": output_text,
                        "output_first_line": out_first_raw,
                        "output_first_line_norm": out_first_eval,
                        "strict_correct": strict_correct,
                        "contains_correct": contains_correct,
                        "latency_s": latency,
                        "usage": {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_tokens": tot_tok,
                        },
                        "est_cost_usd": est_cost,
                        "finish_reason": finish_reason,
                        "error": error_msg,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        # Fortschrittsausgabe
        print(
            f"{item_id}/{total} strict={strict_correct} contains={contains_correct} time={latency}s"
        )

    # ========== ABSCHLUSS UND METADATEN ==========
    end_epoch = int(time.time())
    total_time = round(time.time() - start_total, 2)

    # Aggregierte Metriken für Meta-Datei
    meta = {
        "model": MODEL,
        "dataset": DATASET,
        "items": total,
        "start_epoch": start_epoch,
        "end_epoch": end_epoch,
        "total_time_s": total_time,  # RQ2: Gesamtlaufzeit
        "strict_accuracy": strict_ok / total if total else 0.0,  # RQ1
        "contains_accuracy": contains_ok / total if total else 0.0,  # RQ1
        "avg_latency_s": (sum_latency / total) if total else 0.0,  # RQ2
        "sum_input_tokens": sum_in_tok,  # RQ3
        "sum_output_tokens": sum_out_tok,  # RQ3
        "est_total_cost_usd": sum_cost,  # RQ3
    }

    with open(OUT_META, "w", encoding="utf-8") as fmeta:
        json.dump(meta, fmeta, ensure_ascii=False, indent=2)

    print("\n✅ CLOUD FINISHED")
    print("Saved:")
    print(" -", OUT_CSV)
    print(" -", OUT_JSONL)
    print(" -", OUT_META)


if __name__ == "__main__":
    main()
