"""
Step 3 준비 — 추출 대상 16건 선별 및 출력 (매칭 지점 중심 발췌)
-------------------------------------------------------------
tagged.jsonl에서 pre 8건 + post 8건을 뽑는다.
이전 버전은 본문 앞 1500자를 그대로 보여줘 분리 오류(여러 기사 혼입) 때문에
실제 매칭과 무관한 부분이 나오는 문제가 있었음(spot-check로 확인됨).
이번 버전은 TOPIC/FRAME 키워드가 실제로 매칭된 지점 주변(앞뒤 ~900자)만
잘라 보여준다 — 그 지점이 바로 추출해야 할 인과 주장이 있을 가능성이 높은 곳.

실행: python select_for_extraction.py
출력: 화면에 16개 기사(id, period, date, frames, 매칭 중심 발췌)를 번호 붙여 출력.
      이 출력을 그대로 복사해서 Claude 채팅창에 붙여넣으면 Step 3 추출 진행.
"""
import json, random, re

random.seed(42)  # 재현성: 매번 같은 16건이 뽑히도록 고정

# 02_tag_frames.py와 동일한 패턴 (매칭 위치를 다시 찾기 위해 필요)
TOPIC = [
    "liquor","alcohol","whisky","whiskey","saloon",
    "prohibition","volstead","intoxicat","bootleg",
    "near.?beer","moonshine","speakeasy",
]
FRAMES = {
    "crime":   [r"\barrest\w*\b", r"(?<!af )(?<!af-)\braid\w*\b", r"\bcrime\w*\b",
                r"\bcriminal\w*\b", r"\bsmuggl\w*\b", r"\bseiz\w*\b",
                r"\bjail\w*\b", r"\bconvict\w*\b"],
    "corruption":[r"\bbribe\w*\b", r"\bcorrupt\w*\b",
                r"(?<!\w)graft(?!ed.{0,15}vine)\w*\b",
                r"\bpayoff\w*\b", r"\bconspir\w*\b", r"\bcollusion\w*\b", r"\bfraud\w*\b"],
    "illicit_market":[r"\bbootleg\w*\b", r"\bmoonshine\b(?!.{0,30}(comedy|play|theater|cast))",
                r"\bspeakeasy\b", r"\bblack.?market\w*\b", r"\bcontraband\w*\b", r"\bsmuggl\w*\b"],
}
ALL_PATTERNS = [r"\b" + k + r"\b" for k in TOPIC] + [p for ks in FRAMES.values() for p in ks]

def load():
    return [json.loads(l) for l in open("data_clean/tagged.jsonl", encoding="utf-8")]

def best_window(text, width=900):
    """TOPIC/FRAME 매칭 지점 중 가장 이른 위치를 찾아 그 주변을 잘라 반환.
    매칭이 여러 개면 첫 번째 위치를 기준으로 — 보통 기사 본론이 시작되는 곳."""
    t = text.lower()
    positions = []
    for pat in ALL_PATTERNS:
        m = re.search(pat, t)
        if m: positions.append(m.start())
    if not positions:
        return None
    center = min(positions)
    lo, hi = max(0, center - width // 2), min(len(text), center + width // 2)
    return text[lo:hi]

def select(rows, period, k=8):
    pool = [r for r in rows if r["period"] == period
            and r["topic_alcohol"] and r["any_frame"]
            and len(r["text"].strip()) > 50]            # 빈/거의 빈 본문 제외
    buckets = {}
    for r in pool:
        key = tuple(sorted(f for f, v in r["frames"].items() if v))
        buckets.setdefault(key, []).append(r)
    keys = list(buckets.keys())
    random.shuffle(keys)
    picked = []
    i = 0
    while len(picked) < k and any(buckets.values()):
        key = keys[i % len(keys)]
        if buckets[key]:
            picked.append(buckets[key].pop(random.randrange(len(buckets[key]))))
        i += 1
        if i > 500: break
    return picked[:k]

def main():
    rows = load()
    chosen = select(rows, "pre", 8) + select(rows, "post", 8)
    print(f"총 {len(chosen)}건 선별 (pre {sum(1 for c in chosen if c['period']=='pre')} / "
          f"post {sum(1 for c in chosen if c['period']=='post')})\n")
    print("=" * 90)
    for n, r in enumerate(chosen, 1):
        frames = [f for f, v in r["frames"].items() if v]
        print(f"[기사 {n}] id={r['id']}  period={r['period']}  date={r['date']}  frames={frames}")
        print("-" * 90)
        window = best_window(r["text"])
        print(window if window else "(매칭 지점을 못 찾음 — 스킵 권장)")
        print("=" * 90)

if __name__ == "__main__":
    main()
