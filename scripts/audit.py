import subprocess
import sys
import json
import ollama

AUDIT_PYTHON = "/home/skilipi/ai_rag_project/audit_venv/bin/python3"
CODER_MODEL = "qwen2.5-coder:3b-instruct-q4_K_M"

def run_bandit(path):
    try:
        result = subprocess.run(
            [AUDIT_PYTHON, "-m", "bandit", "-r", path, "-f", "json"],
            capture_output=True, text=True, timeout=120
        )
        return json.loads(result.stdout) if result.stdout else {"results": []}
    except Exception as e:
        return {"results": [], "error": str(e)}

def run_ruff(path):
    try:
        result = subprocess.run(
            [AUDIT_PYTHON, "-m", "ruff", "check", path, "--output-format=json"],
            capture_output=True, text=True, timeout=60
        )
        return json.loads(result.stdout) if result.stdout else []
    except Exception:
        return []

def group_by_severity(bandit_findings, ruff_findings):
    groups = {"HIGH": [], "MEDIUM": [], "LOW": []}
    seen = set()

    for f in bandit_findings.get("results", []):
        key = (f.get("filename"), f.get("line_number"), f.get("test_id"))
        if key in seen:
            continue
        seen.add(key)
        sev = f.get("issue_severity", "LOW").upper()
        if sev not in groups:
            sev = "LOW"
        groups[sev].append({
            "tool": "bandit",
            "file": f.get("filename"),
            "line": f.get("line_number"),
            "text": f.get("issue_text"),
            "id": f.get("test_id"),
        })

    for f in ruff_findings:
        key = (f.get("filename"), f.get("location", {}).get("row"), f.get("code"))
        if key in seen:
            continue
        seen.add(key)
        groups["LOW"].append({
            "tool": "ruff",
            "file": f.get("filename"),
            "line": f.get("location", {}).get("row"),
            "text": f.get("message"),
            "id": f.get("code"),
        })

    return groups

def summarize_with_llm(path, groups):
    total = sum(len(v) for v in groups.values())
    if total == 0:
        print("No issues found by static analysis tools.")
        return

    findings_text = ""
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        for item in groups[sev]:
            findings_text += f"- [{sev}] [{item['tool']}:{item['id']}] {item['text']} (file: {item['file']}, line {item['line']})\n"

    prompt = f"""You are a security code reviewer. Below are static analysis findings for: {path}
Each line already has its correct severity in brackets — DO NOT reassign or guess severity, use exactly what's given.

{findings_text}

Write a summary with these exact sections in this exact order: "## HIGH", "## MEDIUM", "## LOW".
Only include a section if it has findings. For each finding, write:
- One line explaining the issue in plain language
- One line with a concrete fix suggestion
Do not duplicate any finding. Do not invent issues not listed above."""

    print("\n--- AI Audit Summary ---\n")
    stream = ollama.chat(model=CODER_MODEL, messages=[{"role": "user", "content": prompt}], stream=True)
    for chunk in stream:
        print(chunk["message"]["content"], end="", flush=True)
    print("\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python audit.py <file_or_directory>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Running bandit + ruff on: {path}")
    bandit_findings = run_bandit(path)
    ruff_findings = run_ruff(path)
    groups = group_by_severity(bandit_findings, ruff_findings)

    total = sum(len(v) for v in groups.values())
    print(f"Findings — HIGH: {len(groups['HIGH'])}, MEDIUM: {len(groups['MEDIUM'])}, LOW: {len(groups['LOW'])}")

    files_affected = set()
    for sev in groups.values():
        for item in sev:
            files_affected.add(item["file"])
    print(f"Files with findings: {len(files_affected)}")

    summarize_with_llm(path, groups)

if __name__ == "__main__":
    main()
