"""
Emit ColorPostProcessing/shaders/fragment.sc for the BadShader port.

The silhouette is stored as a traced polygon (SVG-path style). Arrays do not
compile through the bundled shaderc, so every polygon edge is emitted as one
unrolled crossing test instead: the even-odd rule just counts crossings.

isInBlack() keeps its original name and meaning from final.fsh.
"""
from PIL import Image, ImageDraw
import sys, math

SRC = sys.argv[1]
OUT = sys.argv[2]
PREVIEW = sys.argv[3]
EPSILON = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0012
WORK_W = 1100

# ---------------------------------------------------------------- binarise
src = Image.open(SRC).convert('RGBA')
W0, H0 = src.size
bin_img = src.convert('L').point(lambda v: 255 if v < 128 else 0)
scale = WORK_W / W0
W, H = WORK_W, max(1, int(H0 * scale))
small = bin_img.resize((W, H), Image.NEAREST)
pix = small.load()
inside = [[pix[x, y] > 128 for x in range(W)] for y in range(H)]

start = None
for y in range(H):
    for x in range(W):
        if inside[y][x]:
            start = (x, y)
            break
    if start:
        break
if start is None:
    raise SystemExit('no foreground pixels')

# ---------------------------------------------------------------- trace boundary
NB = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]

def inside_at(x, y):
    return 0 <= x < W and 0 <= y < H and inside[y][x]

contour = []
cur, prev_dir, guard = start, 7, 0
while guard < W * H * 4:
    guard += 1
    contour.append(cur)
    moved = False
    for i in range(8):
        d = (prev_dir + 1 + i) % 8
        nx, ny = cur[0] + NB[d][0], cur[1] + NB[d][1]
        if inside_at(nx, ny):
            cur = (nx, ny)
            prev_dir = (d + 4) % 8
            moved = True
            break
    if not moved:
        break
    if cur == start and len(contour) > 8:
        break

# ---------------------------------------------------------------- simplify
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
        d = math.hypot(px - ax, py - ay) if norm == 0 else abs(dy * (px - ax) - dx * (py - ay)) / norm
        if d > best_d:
            best_d, best_i = d, i
    if best_d > eps:
        return rdp(points[:best_i + 1], eps)[:-1] + rdp(points[best_i:], eps)
    return [points[0], points[-1]]

far_i = max(range(len(contour)),
            key=lambda i: (contour[i][0] - contour[0][0]) ** 2 + (contour[i][1] - contour[0][1]) ** 2)
simp = rdp(contour[:far_i + 1], EPSILON * W) + rdp(contour[far_i:] + [contour[0]], EPSILON * W)[1:]
if len(simp) > 1 and simp[0] == simp[-1]:
    simp = simp[:-1]
pts = [(x / (W - 1), y / (H - 1)) for x, y in simp]

# ---------------------------------------------------------------- preview
PW, PH = 620, 408
prev = Image.new('L', (PW, PH), 0)
dr = ImageDraw.Draw(prev)
dr.polygon([(x * (PW - 1), y * (PH - 1)) for x, y in pts], fill=255)
prev.save(PREVIEW)

# ---------------------------------------------------------------- emit shader
L = []
L.append('$input v_texcoord0')
L.append('')
L.append('#include "bgfx_shader.sh"')
L.append('')
L.append('SAMPLER2D(s_ColorTexture, 1);')
L.append('')
L.append('#define TRUE  1')
L.append('#define FALSE 0')
L.append('')
L.append('// ColorPostProcessing normally tonemaps + grades; replacing it without a')
L.append('// gamma step makes the whole scene very dark, so do it here.')
L.append('#define EXPOSURE_BASE 1.12')
L.append('#define EXPOSURE_LIFT 0.45')
L.append('')
L.append('// ---------------------------------------------------------------------------')
L.append('// The mask is stored as a traced polygon instead of a texture: the 26.50')
L.append('// material system cannot load custom PNGs (texture_path is empty on every')
L.append('// vanilla material and a bound PNG reads back as the magenta placeholder).')
L.append('// %d vertices, normalised image space, y DOWN (same as this pass uv).' % len(pts))
L.append('// ---------------------------------------------------------------------------')
L.append('')
L.append('// even-odd crossing test for a single polygon edge (ray towards +x)')
L.append('float edge(vec2 uv, vec2 a, vec2 b) {')
L.append('    if ((a.y > uv.y) == (b.y > uv.y)) return 0.0;')
L.append('    float xCross = a.x + (uv.y - a.y) / (b.y - a.y) * (b.x - a.x);')
L.append('    return (uv.x < xCross) ? 1.0 : 0.0;')
L.append('}')
L.append('')
L.append('// final.fsh:isInBlack()')
L.append('// TRUE when uv falls inside the silhouette (the black region of the artwork).')
L.append('int isInBlack(vec2 uv) {')
L.append('    float crossings = 0.0;')
n = len(pts)
for i in range(n):
    ax, ay = pts[i]
    bx, by = pts[(i + 1) % n]
    L.append('    crossings += edge(uv, vec2(%.5f, %.5f), vec2(%.5f, %.5f));' % (ax, ay, bx, by))
L.append('    return (fract(crossings * 0.5) > 0.25) ? TRUE : FALSE;')
L.append('}')
L.append('')
L.append('vec3 tonemap(vec3 c) {')
L.append('    vec3 s = sqrt(max(c, vec3(0.0, 0.0, 0.0)));')
L.append('    vec3 lift = vec3(EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.x),')
L.append('                     EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.y),')
L.append('                     EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.z));')
L.append('    return clamp(s * lift, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));')
L.append('}')
L.append('')
L.append('void main() {')
L.append('    vec2 texcoord = v_texcoord0.xy;')
L.append('')
L.append('    vec4 sceneColor = texture2D(s_ColorTexture, texcoord);')
L.append('    sceneColor.rgb = tonemap(sceneColor.rgb);')
L.append('')
L.append('    vec4 color = sceneColor;')
L.append('')
L.append('    if (isInBlack(texcoord) == TRUE) {')
L.append('        color.x = 1.0 - color.x;')
L.append('        color.y = 1.0 - color.y;')
L.append('        color.z = 1.0 - color.z;')
L.append('    }')
L.append('')
L.append('    color.a = 1.0;')
L.append('    gl_FragColor = color;')
L.append('}')
L.append('')

with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(L))

print('traced points   :', len(contour))
print('polygon vertices:', n)
print('preview         :', PREVIEW)
print('fragment.sc     :', OUT, '(lines:', len(L), ')')
