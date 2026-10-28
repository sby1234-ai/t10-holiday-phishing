"""그림 1 생성: 2024년 하루 탐지 건수(서로 다른 URL)와 명절 직전 2주·연휴 표시.
사용법: python make_figure.py  (analysis.py 실행 후)  → out/figure1.png"""
import csv
from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
rows = list(csv.DictReader(open("out/daily_counts.csv", encoding="utf-8")))
d = [date.fromisoformat(r["date"]) for r in rows]; v = [int(r["unique_urls"]) for r in rows]
g = [r["group"] for r in rows]
# 7일 이동평균
ma = [sum(v[max(0, i-3):i+4]) / len(v[max(0, i-3):i+4]) for i in range(len(v))]
fig, ax = plt.subplots(figsize=(10, 3.8), dpi=160)
ax.plot(d, v, color="#9aa4b2", lw=0.7, label="하루 탐지 건수")
ax.plot(d, ma, color="#1f3a5f", lw=1.6, label="7일 이동평균")
def span(name, color, label):
    xs = [x for x, gg in zip(d, g) if gg == name]
    if xs: ax.axvspan(xs[0], xs[-1], color=color, alpha=0.25, label=label)
span("pre_seol", "#e07a1f", "명절 직전 2주"); span("pre_chuseok", "#e07a1f", None)
hol = [x for x, gg in zip(d, g) if gg == "holiday"]
ax.scatter(hol, [v[d.index(x)] for x in hol], color="#c0392b", s=14, zorder=3, label="연휴 당일")
base = [x for x, gg in zip(v, g) if gg == "base"]
ax.axhline(sum(base)/len(base), color="#2e7d32", ls="--", lw=1, label=f"평소 평균 {sum(base)/len(base):.1f}건")
ax.set_ylabel("서로 다른 URL 수 (건/일)"); ax.set_xlim(d[0], d[-1]); ax.set_ylim(0, None)
# 제목은 논문 본문의 그림 설명으로 붙임
ax.legend(fontsize=7.5, ncol=3, loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig("out/figure1.png"); print("ok")
