"""
Step 1.5 — 주제 필터 + 프레임 태깅 (Query의 분자/분모 정의)
-----------------------------------------------------------
'알코올·금주법 관련 기사'(분모)를 키워드로 추리고,
그 안에서 범죄·부패·불법시장 프레임(분자)을 태깅한다.
=> 사전/사후 프레임 비중(=Rung 1 연관 측정)의 입력이 된다.
"""
import json, re

TOPIC = [  # 분모: 알코올/금주법 관련성. 일반어(dry/wet/still)는 제외 — 오탐 다수 확인(spot-check).
    "liquor","alcohol","whisky","whiskey","saloon",
    "prohibition","volstead","intoxicat","bootleg",
    "near.?beer","moonshine","speakeasy",
]
FRAMES = {  # 분자: 세 프레임. \b...\b로 양쪽 단어 경계 강제.
    "crime":   [r"\barrest\w*\b", r"(?<!af )(?<!af-)\braid\w*\b", r"\bcrime\w*\b",
                r"\bcriminal\w*\b", r"\bsmuggl\w*\b", r"\bseiz\w*\b",
                r"\bjail\w*\b", r"\bconvict\w*\b"],
    "corruption":[r"\bbribe\w*\b", r"\bcorrupt\w*\b",
                r"(?<!\w)graft(?!ed.{0,15}vine)\w*\b",  # 'graft AMERICAN VINES'(원예) 배제
                r"\bpayoff\w*\b", r"\bconspir\w*\b", r"\bcollusion\w*\b", r"\bfraud\w*\b"],
    "illicit_market":[r"\bbootleg\w*\b", r"\bmoonshine\b(?!.{0,30}(comedy|play|theater|cast))",
                r"\bspeakeasy\b", r"\bblack.?market\w*\b", r"\bcontraband\w*\b", r"\bsmuggl\w*\b"],
}

NON_ARTICLE_SIGNAL = re.compile(
    r"(advertisement|\bcomedy\b|\bplay\b|theater|theatre|\bcast\b|starring|"
    r"box office|admission|matinee|orchestra seats)", re.I)

def is_non_article_context(text, span, window=80):
    """매칭 지점 주변에 광고/공연 신호어가 있으면 비기사로 간주."""
    s, e = span
    lo, hi = max(0, s - window), min(len(text), e + window)
    return bool(NON_ARTICLE_SIGNAL.search(text[lo:hi]))

def tag(text):
    t = text.lower()
    topic = False
    for k in TOPIC:
        pat = r"\b" + k + r"\b" if not k.startswith(r"\b") else k
        m = re.search(pat, t)
        if m and not is_non_article_context(t, m.span()):
            topic = True
            break
    frames = {}
    for f, ks in FRAMES.items():
        hit = False
        for k in ks:
            m = re.search(k, t)
            if m and not is_non_article_context(t, m.span()):
                hit = True
                break
        frames[f] = hit
    return topic, frames

def main():
    rows = [json.loads(l) for l in open("data_clean/articles.jsonl", encoding="utf-8")]
    out = []
    for r in rows:
        topic, frames = tag(r["text"])
        r["topic_alcohol"] = topic
        r["frames"] = frames
        r["any_frame"] = any(frames.values())
        out.append(r)
    with open("data_clean/tagged.jsonl","w",encoding="utf-8") as f:
        for r in out: f.write(json.dumps(r,ensure_ascii=False)+"\n")

    # 즉석 집계(보고서 Step6 표의 원천)
    from collections import Counter
    for period in ("pre","post"):
        sub=[r for r in out if r["period"]==period and r["topic_alcohol"]]
        n=len(sub); fr=sum(r["any_frame"] for r in sub)
        print(f"[{period}] 주제기사={n}  프레임포함={fr}  비중={fr/n:.1%}" if n else f"[{period}] 0")
        for fkey in FRAMES:
            c=sum(r["frames"][fkey] for r in sub)
            print(f"    {fkey:15s}: {c} ({c/n:.0%})" if n else "")

if __name__=="__main__":
    main()
