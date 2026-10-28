"""사후 탐색(가설 검정 아님): 결과 해석 단계에서 이유 후보를 데이터로 확인한다.
사용법: python explore.py   (analysis.py 실행 후 out/daily_counts.csv 필요)"""
import csv, json
from datetime import date, timedelta
rows=list(csv.DictReader(open('out/daily_counts.csv',encoding='utf-8')))
v={date.fromisoformat(r['date']):int(r['unique_urls']) for r in rows}
g={date.fromisoformat(r['date']):r['group'] for r in rows}
wk={date.fromisoformat(r['date']):r['weekday'] for r in rows}
mean=lambda xs: round(sum(xs)/len(xs),1) if xs else None
res={}
# 1) 연휴 당일에도 탐지가 이어졌는가
H={'설':(date(2024,2,9),date(2024,2,12)),'추석':(date(2024,9,16),date(2024,9,18))}
base=[v[d] for d in v if g[d]=='base']
wkend=[v[d] for d in v if g[d]=='base' and wk[d] in '토일']
for k,(s,e) in H.items():
    days=[s+timedelta(i) for i in range((e-s).days+1)]
    res[f'{k}_연휴당일']={'날짜별':{str(d):v[d] for d in days},'평균':mean([v[d] for d in days])}
res['평소_평균']=mean(base); res['평소_주말_평균']=mean(wkend)
# 2) 계절 흐름: 명절 직전 2주 vs 바로 앞뒤 4주(직전2주·연휴 제외)
for k,(s,e) in H.items():
    pre=[s-timedelta(i) for i in range(1,15)]
    around=[d for d in (s+timedelta(i) for i in range(-42,4+28)) if d in v and g[d]=='base']
    res[f'{k}_직전2주_vs_앞뒤']={'직전2주':mean([v[d] for d in pre]),'앞뒤평소':mean([v[d] for d in around]),'앞뒤_일수':len(around)}
json.dump(res,open('out/explore.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(json.dumps(res,ensure_ascii=False,indent=2))
