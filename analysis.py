"""T10 재작성 분석 스크립트 — 사전 확정 설계(01_가설과_설계_사전확정.md)를 그대로 실행한다.

사용법:  python analysis.py data/kisa_phishing_20241231.csv
표준 라이브러리만 사용 (Python 3.9+). 결과는 out/ 폴더에 CSV·JSON 으로 저장한다.
"""
import csv, json, sys, math, os, random
from datetime import date, timedelta
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/kisa_phishing_20241231.csv"
OUT = "out"
os.makedirs(OUT, exist_ok=True)

YEAR_START, YEAR_END = date(2024, 1, 1), date(2024, 12, 31)
HOLIDAYS = {
    "설": (date(2024, 2, 9), date(2024, 2, 12)),
    "추석": (date(2024, 9, 16), date(2024, 9, 18)),
}
WIN = 14  # 연휴 직전 일수


def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def norm(u):
    u = u.strip().lower()
    for p in ("https://", "http://"):
        if u.startswith(p):
            u = u[len(p):]
    return u.rstrip("/")


# 1) 원자료 읽기
rows, bad = [], []
with open(SRC, encoding="utf-8-sig", newline="") as f:
    r = csv.reader(f)
    header = next(r)
    for i, row in enumerate(r, start=2):
        if len(row) < 2:
            bad.append((i, row)); continue
        try:
            d = date.fromisoformat(row[0].strip())
        except ValueError:
            bad.append((i, row)); continue
        rows.append((d, row[1]))

raw_per_day = defaultdict(int)
uniq_per_day = defaultdict(set)
for d, u in rows:
    raw_per_day[d] += 1
    uniq_per_day[d].add(norm(u))

days = list(drange(YEAR_START, YEAR_END))
uniq = {d: len(uniq_per_day.get(d, ())) for d in days}
raw = {d: raw_per_day.get(d, 0) for d in days}
out_of_range = sorted({d for d in raw_per_day if d < YEAR_START or d > YEAR_END})

# 2) 구간 정의
holiday_days, pre = set(), {}
for name, (s, e) in HOLIDAYS.items():
    holiday_days |= set(drange(s, e))
    pre[name] = list(drange(s - timedelta(days=WIN), s - timedelta(days=1)))
pre_days = set(pre["설"]) | set(pre["추석"])
base_days = [d for d in days if d not in holiday_days and d not in pre_days]

mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")


def summarize(metric):
    res = {}
    base_mean = mean([metric[d] for d in base_days])
    # 연휴와 겹치지 않는 모든 연속 14일 구간
    windows = []
    for i in range(len(days) - WIN + 1):
        w = days[i:i + WIN]
        if any(d in holiday_days for d in w):
            continue
        windows.append((w[0], mean([metric[d] for d in w])))
    all_means = sorted((m for _, m in windows), reverse=True)
    for name in HOLIDAYS:
        m = mean([metric[d] for d in pre[name]])
        rank = 1 + sum(1 for x in all_means if x > m)  # 1 = 가장 높음
        pct = rank / len(all_means)
        res[name] = {
            "window": f"{pre[name][0]}~{pre[name][-1]}",
            "mean": m, "ratio_vs_base": m / base_mean,
            "rank": rank, "n_windows": len(all_means), "top_pct": pct,
            "pass_top10": pct <= 0.10,
        }
    res["base_mean"] = base_mean
    res["n_base_days"] = len(base_days)
    return res, windows


def mannwhitney_greater(x, y):
    """x 가 y 보다 크다는 한쪽 맨-휘트니 U 검정(정규 근사, 동점 보정)."""
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(allv)
    i, ties = 0, 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        t = j - i + 1
        ties += t ** 3 - t
        i = j + 1
    n1, n2 = len(x), len(y)
    r1 = sum(rk for rk, (_, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    n = n1 + n2
    mu = n1 * n2 / 2
    sd = math.sqrt(n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1))))
    z = (u1 - mu - 0.5) / sd if sd else 0.0
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return {"U": u1, "z": z, "p_one_sided": p, "n_pre": n1, "n_base": n2}


report = {"source_file": os.path.basename(SRC), "rows_read": len(rows),
          "bad_rows": len(bad), "dates_out_of_2024": [str(d) for d in out_of_range],
          "days_with_zero_unique": sum(1 for d in days if uniq[d] == 0)}
for label, metric in (("unique", uniq), ("raw", raw)):
    s, windows = summarize(metric)
    s["mannwhitney"] = mannwhitney_greater([metric[d] for d in sorted(pre_days)],
                                           [metric[d] for d in base_days])
    report[label] = s
    with open(f"{OUT}/windows_{label}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["window_start", "mean_per_day"])
        for st, m in windows:
            w.writerow([st, f"{m:.3f}"])

u = report["unique"]
both = u["설"]["pass_top10"] and u["추석"]["pass_top10"]
one = u["설"]["pass_top10"] or u["추석"]["pass_top10"]
p_ok = u["mannwhitney"]["p_one_sided"] < 0.05
report["verdict"] = ("지지" if both and p_ok else "부분 지지" if one else "기각")

with open(f"{OUT}/daily_counts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "weekday", "unique_urls", "raw_rows", "group"])
    for d in days:
        g = ("holiday" if d in holiday_days else
             "pre_seol" if d in pre["설"] else "pre_chuseok" if d in pre["추석"] else "base")
        w.writerow([d, "월화수목금토일"[d.weekday()], uniq[d], raw[d], g])

with open(f"{OUT}/report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
