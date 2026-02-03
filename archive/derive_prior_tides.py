import json
from datetime import datetime, timedelta

with open('tides.json','r') as f:
    data = json.load(f)

fr = data.get('fort_ross',{}).get('2026-02-01',[])
bd = data.get('bodega_tides',{}).get('2026-02-01',[])

# Goat Rock from Fort Ross +5 min
if fr:
    gr = []
    for l, t, h in fr:
        dt = datetime.strptime(t, '%I:%M %p') + timedelta(minutes=5)
        gr.append([l, dt.strftime('%I:%M %p').lstrip('0'), h])
    data.setdefault('goat_rock', {})['2026-02-01'] = gr

# Estuary from Bodega: High +90, Low +60
if bd:
    est = []
    for l, t, h in bd:
        offset = 90 if l == 'High' else 60
        dt = datetime.strptime(t, '%I:%M %p') + timedelta(minutes=offset)
        est.append([l, dt.strftime('%I:%M %p').lstrip('0'), h])
    data.setdefault('estuary', {})['2026-02-01'] = est

with open('tides.json','w') as f:
    json.dump(data, f, indent=4)

print('Updated goat_rock and estuary for 2026-02-01')
