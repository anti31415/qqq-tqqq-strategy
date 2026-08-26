from __future__ import annotations

import re
from pathlib import Path


def main() -> None:
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    history_jsonl = logs_dir / "autotrade_history.jsonl"
    history_txt = logs_dir / "autotrade_history.txt"

    jsonl_files = sorted(
        path for path in logs_dir.glob("autotrade_*.jsonl") if path.name != history_jsonl.name
    )
    txt_files = sorted(
        path for path in logs_dir.glob("autotrade_*.txt") if path.name != history_txt.name
    )

    seen_jsonl_lines: set[str] = set()
    if history_jsonl.exists():
        seen_jsonl_lines = {line.rstrip("\n") for line in history_jsonl.read_text(encoding="utf-8").splitlines()}

    with history_jsonl.open("a", encoding="utf-8") as handle:
        for path in jsonl_files:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line or line in seen_jsonl_lines:
                    continue
                handle.write(line)
                handle.write("\n")
                seen_jsonl_lines.add(line)

    existing_txt = history_txt.read_text(encoding="utf-8") if history_txt.exists() else ""
    blocks_seen = set(re.split(r"\n(?=={80}\n)", existing_txt)) if existing_txt else set()
    with history_txt.open("a", encoding="utf-8") as handle:
        for path in txt_files:
            content = path.read_text(encoding="utf-8")
            blocks = [block for block in re.split(r"\n(?=={80}\n)", content) if block.strip()]
            for block in blocks:
                normalized = block if block.endswith("\n") else f"{block}\n"
                if normalized in blocks_seen:
                    continue
                if history_txt.exists() and history_txt.stat().st_size > 0:
                    if not normalized.startswith("=" * 80):
                        handle.write("\n")
                handle.write(normalized)
                blocks_seen.add(normalized)

    print(f"Merged {len(jsonl_files)} daily jsonl files and {len(txt_files)} daily txt files into history files in {logs_dir}")


if __name__ == "__main__":
    main()
