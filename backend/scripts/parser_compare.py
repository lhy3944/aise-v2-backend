"""PDF 파서 비교 PoC — PyMuPDF vs opendataloader-pdf.

본 스크립트는 코드 베이스를 변경하지 않는 격리된 비교 도구다. backend 메인 venv가
아닌 별도 venv에서 실행할 것을 권장한다 (plan §3.3 참조).

실행 절차:
    cd backend/scripts
    python -m venv .venv-poc
    source .venv-poc/Scripts/activate    # Windows Git Bash
    pip install opendataloader-pdf pymupdf tiktoken
    cp /path/to/*.pdf sample_pdfs/
    python parser_compare.py

출력:
    parser_compare_out/<pdf_basename>/
        pymupdf.txt
        opendataloader/<...>            (라이브러리가 생성한 markdown 등)
        summary.json
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = SCRIPT_DIR / "sample_pdfs"
OUT_DIR = SCRIPT_DIR / "parser_compare_out"

TABLE_ROW_RE = re.compile(r"^\s*\|")


def _check_java() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_text = result.stderr or result.stdout
        return True, version_text.strip().splitlines()[0] if version_text else "java OK"
    except FileNotFoundError:
        return False, "java 명령어를 찾을 수 없습니다. JRE 11+ 설치 필요."
    except subprocess.TimeoutExpired:
        return False, "java -version 타임아웃."


def _import_pymupdf():
    try:
        import pymupdf  # type: ignore
        return pymupdf
    except ImportError:
        sys.exit("pymupdf 미설치. `pip install pymupdf` 실행 후 재시도하세요.")


def _import_opendataloader():
    try:
        import opendataloader_pdf  # type: ignore
        return opendataloader_pdf
    except ImportError:
        sys.exit("opendataloader-pdf 미설치. `pip install opendataloader-pdf` 실행 후 재시도하세요.")


def _import_tiktoken():
    try:
        import tiktoken  # type: ignore
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        sys.exit("tiktoken 미설치. `pip install tiktoken` 실행 후 재시도하세요.")


def parse_pymupdf(pymupdf, pdf_path: Path) -> str:
    """document_processor._parse_pdf()와 동일 로직."""
    text_parts: list[str] = []
    with pymupdf.open(str(pdf_path), filetype="pdf") as doc:
        page_count = doc.page_count
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts), page_count


def parse_opendataloader(opendataloader_pdf, pdf_path: Path, out_subdir: Path) -> str:
    """opendataloader-pdf로 markdown 추출 후, 생성된 .md 파일을 합쳐 반환."""
    out_subdir.mkdir(parents=True, exist_ok=True)
    opendataloader_pdf.convert(
        input_path=[str(pdf_path)],
        output_dir=str(out_subdir),
        format="markdown",
    )
    md_files = sorted(out_subdir.rglob("*.md"))
    if not md_files:
        # markdown 미지원 버전 대비 — json/html 폴백 스캔
        candidates = sorted(out_subdir.rglob("*.json")) + sorted(out_subdir.rglob("*.html"))
        if not candidates:
            return ""
        return "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in candidates)
    return "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in md_files)


def count_table_rows(text: str) -> int:
    return sum(1 for line in text.splitlines() if TABLE_ROW_RE.match(line))


def token_count(encoding, text: str) -> int:
    if not text:
        return 0
    return len(encoding.encode(text))


def main() -> int:
    print("=" * 70)
    print("PDF 파서 비교 PoC — PyMuPDF vs opendataloader-pdf")
    print("=" * 70)

    java_ok, java_msg = _check_java()
    print(f"[java] {java_msg}")
    if not java_ok:
        print("→ opendataloader-pdf 실행 불가. JRE 설치 후 재시도하세요.")
        return 2

    if not SAMPLE_DIR.exists():
        sys.exit(f"샘플 디렉토리 없음: {SAMPLE_DIR}")
    pdfs = sorted(SAMPLE_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"{SAMPLE_DIR}에 .pdf 파일이 없습니다. 샘플을 채운 뒤 재시도하세요.")

    pymupdf = _import_pymupdf()
    opendataloader_pdf = _import_opendataloader()
    encoding = _import_tiktoken()

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    rows: list[dict] = []
    for pdf in pdfs:
        name = pdf.stem
        case_dir = OUT_DIR / name
        case_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n--- {pdf.name} ---")

        try:
            pymu_text, page_count = parse_pymupdf(pymupdf, pdf)
        except Exception as e:
            print(f"  PyMuPDF 실패: {e}")
            pymu_text, page_count = "", 0
        (case_dir / "pymupdf.txt").write_text(pymu_text, encoding="utf-8")

        odl_subdir = case_dir / "opendataloader"
        try:
            odl_text = parse_opendataloader(opendataloader_pdf, pdf, odl_subdir)
        except Exception as e:
            print(f"  opendataloader 실패: {e}")
            odl_text = ""

        pymu_tokens = token_count(encoding, pymu_text)
        odl_tokens = token_count(encoding, odl_text)
        pymu_table = count_table_rows(pymu_text)
        odl_table = count_table_rows(odl_text)

        summary = {
            "pdf": pdf.name,
            "pages": page_count,
            "pymupdf": {
                "chars": len(pymu_text),
                "tokens_cl100k": pymu_tokens,
                "table_lines": pymu_table,
            },
            "opendataloader": {
                "chars": len(odl_text),
                "tokens_cl100k": odl_tokens,
                "table_lines": odl_table,
            },
            "delta": {
                "tokens_pct": _pct(pymu_tokens, odl_tokens),
                "table_lines_pct": _pct(pymu_table, odl_table),
            },
        }
        (case_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows.append(summary)
        print(
            f"  pages={page_count}  "
            f"PyMuPDF[tok={pymu_tokens}, tbl={pymu_table}]  "
            f"OpenDL[tok={odl_tokens}, tbl={odl_table}]"
        )

    print("\n" + "=" * 70)
    print(f"{'PDF':<35} {'pages':>6} {'pyTok':>8} {'odlTok':>8} {'pyTbl':>6} {'odlTbl':>6}")
    print("-" * 70)
    for r in rows:
        print(
            f"{r['pdf'][:34]:<35} "
            f"{r['pages']:>6} "
            f"{r['pymupdf']['tokens_cl100k']:>8} "
            f"{r['opendataloader']['tokens_cl100k']:>8} "
            f"{r['pymupdf']['table_lines']:>6} "
            f"{r['opendataloader']['table_lines']:>6}"
        )
    print("=" * 70)
    print(f"\n결과 디렉토리: {OUT_DIR}")
    return 0


def _pct(base: int, new: int) -> float | None:
    if base == 0:
        return None
    return round((new - base) / base * 100, 1)


if __name__ == "__main__":
    sys.exit(main())
