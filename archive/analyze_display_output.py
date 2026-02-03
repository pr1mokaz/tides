from PIL import Image

img = Image.open('display_outputs/display_latest.png').convert('1')
width, height = img.size
pix = img.load()  # 0 black, 255 white

# Graph bounds from draw_tide_waveform
x0, y0, w, h = 10, 275, 280, 120
margin_left, margin_right, margin_top, margin_bottom = 12, 3, 3, 12
x1 = x0 + margin_left
x2 = x0 + w - margin_right
ya = y0 + margin_top
yb = y0 + h - margin_bottom

print('Graph bounds:', x1, x2, ya, yb)

# Consider black pixels within graph
graph_width = x2 - x1
graph_height = yb - ya

# Per-column median y of black pixels
heights = []
counts = []
for x in range(x1, x2):
    ys = []
    for y in range(ya, yb):
        if pix[x, y] == 0:
            ys.append(y - ya)
    if not ys:
        heights.append(None)
        counts.append(0)
    else:
        ys.sort()
        mid = len(ys) // 2
        heights.append(ys[mid])
        counts.append(len(ys))

# Map x to minutes
def x_to_minute(x):
    return int(round(x / graph_width * 1440))

# Analyze 0:00-6:00 region
mins = []
ys = []
for idx, x in enumerate(range(x1, x2)):
    m = x_to_minute(idx)
    if 0 <= m <= 360 and heights[idx] is not None:
        mins.append(m)
        ys.append(heights[idx])

if ys:
    mean = sum(ys) / len(ys)
    variance = sum((y - mean) ** 2 for y in ys) / len(ys)
    y_std = variance ** 0.5
    y_range = (min(ys), max(ys))
    print('0:00-6:00 median black y stats:', 'std=', round(y_std,2), 'range=', y_range, 'count=', len(ys))
else:
    print('0:00-6:00: no black pixels detected')

# Identify rows with high black density (flat lines)
row_counts = [0] * graph_height
for y in range(ya, yb):
    count = 0
    for x in range(x1, x2):
        if pix[x, y] == 0:
            count += 1
    row_counts[y - ya] = count

threshold = int(graph_width * 0.35)
rows = [i for i, c in enumerate(row_counts) if c > threshold]
print('Rows with >35% black coverage:', rows[:10], '... total', len(rows))

for r in rows[:10]:
    print('Row', r, 'count', int(row_counts[r]))

# Show top rows by black pixel count (to detect dotted flat lines)
top_rows = sorted(enumerate(row_counts), key=lambda t: t[1], reverse=True)[:10]
print('Top 10 rows by black pixel count:')
for r, c in top_rows:
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    approx_h = h_min + ((graph_height - r) / graph_height) * h_range
    print('Row', r, 'count', int(c), 'approx_h', round(approx_h, 2))
