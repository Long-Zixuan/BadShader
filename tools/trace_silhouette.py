"""
Extract the silhouette outline from the mask artwork and emit it as a
polygon point list suitable for embedding in a GLSL shader.

Approach (SVG-like): trace the outer boundary of the thresholded image,
simplify it with Douglas-Peucker, then render the simplified polygon back
for visual verification before it ever reaches the game.

Coordinates are normalised image space with y pointing DOWN, which matches
the uv handed to the Bedrock ColorPostProcessing pass (uv.y = 0 is the top
of the screen).
"""
from PIL import Image, ImageDraw
import sys, json, math

SRC = sys.argv[1]
OUT_GLSL = sys.argv[2]
OUT_PREVIEW = sys.argv[3]

EPSILON = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0016   # simplification tolerance
WORK_W = 900                                                    # tracing resolution

# ---------------------------------------------------------------- load + binarise
src = Image.open(SRC).convert('RGBA')
W0, H0 = src.size
glyph = src.convert('L')
bin_img = glyph.point(lambda v: 255 if v < 128 else 0)

scale = WORK_W / W0
work_h = max(1, int(H0 * scale))
bin_small = bin_img.resize((WORK_W, work_h), Image.NEAREST)
W, H = bin_small.size
pix = bin_small.load()
inside = [[pix[x, y] > 128 for x in range(W)] for y in range(H)]

# ---------------------------------------------------------------- find a start pixel
start = None
for y in range(H):
    for x in range(W):
        if inside[y][x]:
            start = (x, y)
            break
    if start:
        break
if start is None:
    raise SystemExit('no foreground pixels found')

# ---------------------------------------------------------------- Moore neighbour tracing
# 8-connected boundary following
NB = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]

def inside_at(x, y):
    if x < 0 or y < 0 or x >= W or y >= H:
        return False
    return inside[y][x]

contour = []
cur = start
prev_dir = 7            # came from the west
guard = 0
max_steps = W * H * 4
while guard < max_steps:
    guard += 1
    contour.append(cur)
    found = False
    for i in range(8):
        d = (prev_dir + 1 + i) % 8
        nx, ny = cur[0] + NB[d][0], cur[1] + NB[d][1]
        if inside_at(nx, ny):
            cur = (nx, ny)
            prev_dir = (d + 4) % 8     # direction back towards the previous pixel
            found = True
            break
    if not found:
        break
    if cur == start and len(contour) > 8:
        break

if len(contour) < 16:
    raise SystemExit(f'contour too short ({len(contour)} points)')

# ---------------------------------------------------------------- Douglas-Peucker
def rdp(points, eps):
    if len(points) < 3:
        return points
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy)
    best_i, best_d = -1, -1.0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if norm == 0:
            d = math.hypot(px - ax, py - ay)
        else:
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
        if d > best_d:
            best_d, best_i = d, i
    if best_d > eps:
        left = rdp(points[:best_i + 1], eps)
        right = rdp(points[best_i:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]

# close the loop: split at the point farthest from the start to avoid
# degenerate RDP behaviour on a closed ring
far_i = max(range(len(contour)),
            key=lambda i: (contour[i][0] - contour[0][0]) ** 2 + (contour[i][1] - contour[0][1]) ** 2)
ring = contour[:far_i + 1]
ring2 = contour[far_i:] + [contour[0]]
simp = rdp(ring, EPSILON * W) + rdp(ring2, EPSILON * W)[1:]

# drop the duplicated closing vertex
if len(simp) > 1 and simp[0] == simp[-1]:
    simp = simp[:-1]

pts = [(x / (W - 1), y / (H - 1)) for x, y in simp]

# ---------------------------------------------------------------- preview render
PW, PH = 620, 408
prev = Image.new('L', (PW, PH), 0)
dr = ImageDraw.Draw(prev)
poly = [(x * (PW - 1), y * (PH - 1)) for x, y in pts]
if len(poly) >= 3:
    dr.polygon(poly, fill=255)
prev.save(OUT_PREVIEW)

# ---------------------------------------------------------------- emit GLSL
lines = []
lines.append('// silhouette outline ({} vertices, traced from the source artwork)'.format(len(pts)))
lines.append('// normalised image space, y DOWN (matches the screen uv handed to this pass)')
lines.append('#define SILHOUETTE_COUNT {}'.format(len(pts)))
lines.append('const vec2 SILHOUETTE[{}] = vec2[{}]('.format(len(pts), len(pts)))
chunk = []
for i, (x, y) in enumerate(pts):
    chunk.append('vec2({:.5f}, {:.5f})'.format(x, y))
    if len(chunk) == 4 or i == len(pts) - 1:
        tail = ',' if i < len(pts) - 1 else ''
        lines.append('    ' + ', '.join(chunk) + tail)
        chunk = []
lines.append(');')
with open(OUT_GLSL, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print('contour points traced :', len(contour))
print('after simplification  :', len(pts))
print('preview               :', OUT_PREVIEW)
print('glsl                  :', OUT_GLSL)
