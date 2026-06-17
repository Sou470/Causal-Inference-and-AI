"""
Step 1 (수집/범위) + Step 2 (정제/정규화)  — 안내문 옵션 A(규칙기반) 기반
-------------------------------------------------------------------
입력 : evening_star/<YYYY-MM>/<YYYY-MM-DD>/*.txt
       (월 폴더 안에 일 단위 폴더, 그 안에 이슈별 OCR 파일들)
출력 : data_clean/articles.jsonl
       각 줄 = {id, period, date, source, text, n_chars, is_boundary_date}

period(pre/post)는 가장 안쪽 폴더명(YYYY-MM-DD)을 BOUNDARY_DATE와 비교해
코드가 자동 판정한다. 폴더 깊이가 evening_star/월/일/파일 2단계임에 주의.

정제 규칙 (모두 보고서 Step2에 기록):
  R1 페이지/발행 마커 라인 제거 (CIRCULATION, PAGES, No. 27,613 등)
  R2 줄 끝 하이픈 복원  ("proporu-\n withjout" → 단어 병합)
  R3 공백/인코딩 정규화 (ftfy)
  R4 기사 분리: 빈 줄 2개 이상 또는 대문자 헤드라인 블록 기준 (휴리스틱)
주의: OCR을 '의미까지' 고치지 않는다. 프레임 키워드 생존이 목표.
"""
import os, re, json, glob
try:
    from ftfy import fix_text
except ImportError:
    def fix_text(s): return s   # ftfy 없으면 패스 (pip install ftfy 권장)

RAW = "evening_star"   # 최상위 데이터 폴더명. 본인 경로에 맞게 수정 가능.
OUT = "data_clean/articles.jsonl"
BOUNDARY_DATE = "1920-01-17"  # 처치 발생일. 이 날짜 포함 이후 = post.

BOILERPLATE = re.compile(
    r"(NET CIRCULATION|SUNDAY MORNING EDITION|THIRTY PAGES|Closing New York Stocks"
    r"|^No\.\s*[\d,]+|^Page \d+|WASH ?1?NGTON, ?D\. ?C\.)", re.I)

def repair_hyphens(text):
    # 줄 끝 하이픈 + 개행 → 단어 결합. OCR은 '-' 누락도 잦아 보수적으로만.
    return re.sub(r"(\w)[-\u00ad]\s*\n\s*(\w)", r"\1\2", text)

def clean(raw):
    raw = fix_text(raw)
    raw = repair_hyphens(raw)
    lines = [ln for ln in raw.splitlines() if not BOILERPLATE.search(ln.strip())]
    txt = "\n".join(lines)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt.strip()

def segment(txt):
    # 휴리스틱: 2+ 빈 줄 또는 4단어 이상 ALL-CAPS 헤드라인에서 분리.
    blocks = re.split(r"\n\s*\n", txt)
    arts, buf = [], ""
    for b in blocks:
        b = b.strip()
        if not b: continue
        lines = b.splitlines()
        head = lines[0]
        # 헤드라인 판정: 첫 줄이 2단어+ ALL-CAPS이고, 직전 버퍼가 이미 80자 이상
        # 쌓여 있을 때만 "새 기사 시작"으로 간주 (짧은 버퍼는 같은 기사의 부제로 봄).
        is_head = head.isupper() and len(head.split()) >= 2
        if is_head and len(buf.strip()) > 80:
            arts.append(buf.strip()); buf = b
        else:
            buf += "\n" + b
    if buf.strip(): arts.append(buf.strip())
    # 너무 짧은 조각(광고 잔해 등)은 버림. 기준 상향(200→260)으로 파편 추가 억제.
    return [a for a in arts if len(a) > 260]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def period_of(date_str):
    # 'YYYY-MM-DD' 문자열 비교만으로 충분 (사전식 순서 = 날짜 순서)
    return "post" if date_str >= BOUNDARY_DATE else "pre"

def find_day_dirs(root):
    """evening_star/YYYY-MM/YYYY-MM-DD 2단계를 내려가 일 단위 폴더만 모은다."""
    day_dirs = []
    for month_dir in sorted(d for d in glob.glob(f"{root}/*") if os.path.isdir(d)):
        for day_dir in sorted(d for d in glob.glob(f"{month_dir}/*") if os.path.isdir(d)):
            if DATE_RE.match(os.path.basename(day_dir)):
                day_dirs.append(day_dir)
    return day_dirs

def main():
    rows, aid = [], 0
    for ddir in find_day_dirs(RAW):
        date = os.path.basename(ddir)               # 가장 안쪽 폴더명 = 날짜 (예: 1920-01-17)
        period = period_of(date)
        for fp in sorted(glob.glob(f"{ddir}/*.txt")):  # 파일명은 ed-1_seq-001_ocr.txt 등 무엇이든 무관
            txt = clean(open(fp, encoding="utf-8", errors="ignore").read())
            for art in segment(txt):
                aid += 1
                rows.append({"id": f"a{aid:04d}", "period": period,
                             "date": date, "source": "Evening Star",
                             "is_boundary_date": (date == BOUNDARY_DATE),
                             "text": art, "n_chars": len(art)})
    os.makedirs("data_clean", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} articles → {OUT}")
    from collections import Counter
    print(Counter(r["period"] for r in rows))

if __name__ == "__main__":
    main()
