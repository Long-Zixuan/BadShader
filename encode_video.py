import glob
import math
import os
import subprocess

import numpy as np
from PIL import Image

# ---------- 参数 ----------
VIDEO = r"C:\Users\Long_\Documents\PCL破解视频\11月15日.mp4"
FRAMES_DIR = r"D:\MC_MOD\Sobel\_encode"
W, H = 192, 108
FPS = 15
CH = 4                  # 每格打包帧数(RGBA 四通道)
DURATION = 217.766667
FINAL_FSH = r"D:\MC_MOD\Sobel\shaders\final.fsh"
PROPS = r"D:\MC_MOD\Sobel\shaders\shaders.properties"
TEXTURE = r"D:\MC_MOD\Sobel\shaders\texture\video.png"

# ---------- 1. 抽帧 ----------
os.makedirs(FRAMES_DIR, exist_ok=True)
for f in glob.glob(os.path.join(FRAMES_DIR, "*.png")):
    os.remove(f)
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", VIDEO,
       "-vf", "fps=%d,scale=%d:%d:flags=lanczos,format=gray" % (FPS, W, H),
       "-vsync", "0", "-f", "image2", os.path.join(FRAMES_DIR, "f_%05d.png")]
subprocess.run(cmd, check=True)

files = sorted(glob.glob(os.path.join(FRAMES_DIR, "f_*.png")))
N = len(files)
print("frames:", N)

frames = []
for fp in files:
    with Image.open(fp) as im:
        frames.append(np.array(im.convert("L")))

# ---------- 2. 每 4 帧打包进一个 RGBA 格子 ----------
cells = math.ceil(N / CH)
cols = math.ceil(math.sqrt(cells))
rows = math.ceil(cells / cols)
atlas_w, atlas_h = cols * W, rows * H
atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))

for c in range(cells):
    base = c * CH
    chans = [np.zeros((H, W), dtype=np.uint8)] * CH
    for ch in range(CH):
        idx = base + ch
        if idx < N:
            chans[ch] = frames[idx]
    rgba = np.dstack((chans[0], chans[1], chans[2], chans[3]))
    cell = Image.fromarray(rgba, "RGBA")
    gx, gy = c % cols, c // cols
    atlas.paste(cell, (gx * W, gy * H))

atlas.save(TEXTURE, optimize=True)
print("cells:", cells, "grid:", cols, "x", rows, "atlas:", atlas_w, "x", atlas_h)

# ---------- 3. 自检 ----------
def check_cell(c):
    with Image.open(TEXTURE) as im:
        gx, gy = c % cols, c // cols
        cell = np.array(im.crop((gx * W, gy * H, (gx + 1) * W, (gy + 1) * H)))
    for ch in range(CH):
        idx = c * CH + ch
        if idx >= N:
            continue
        if not np.array_equal(cell[:, :, ch], frames[idx]):
            raise SystemExit("decode mismatch cell %d channel %d" % (c, ch))

check_cell(0)
check_cell(cells - 1)
print("decode self-check OK")

# ---------- 4. 写回 final.fsh ----------
block = (
    "// ===== 视频播放：帧图集纹理(每格 4 帧 RGBA)，按时间逐帧采样 =====\n"
    "uniform sampler2D colortex1;      // 视频帧图集(由 shaders.properties 绑定 texture/video.png)\n"
    "uniform float frameTimeCounter;   // 游戏运行时间(秒)，由 OptiFine/Iris 提供\n"
    "\n"
    "#define VIDEO_DURATION %.6f // 视频总时长(秒)\n"
    "#define VIDEO_FRAMES  %d        // 总帧数\n"
    "#define VIDEO_CELLS   %d        // 图集格子数(每格 %d 帧)\n"
    "#define VIDEO_GRID_X  %d        // 图集列数\n"
    "#define VIDEO_GRID_Y  %d        // 图集行数\n"
    "#define VIDEO_ATLAS_W %d        // 图集像素宽\n"
    "#define VIDEO_ATLAS_H %d        // 图集像素高\n"
    "\n"
    "float isInBlack(vec2 uv)\n"
    "{\n"
    "\t// 循环播放：当前时间 -> 帧号\n"
    "\tfloat t = mod(frameTimeCounter, VIDEO_DURATION);\n"
    "\tint f = int(floor(t / VIDEO_DURATION * float(VIDEO_FRAMES)));\n"
    "\n"
    "\t// 帧 -> 格子(每格 %d 帧)与通道(R/G/B/A)\n"
    "\tint c = f / %d;\n"
    "\tint ch = f - c * %d;\n"
    "\tint gx = c %% VIDEO_GRID_X;\n"
    "\tint gy = c / VIDEO_GRID_X;\n"
    "\n"
    "\tvec2 cell = 1.0 / vec2(float(VIDEO_GRID_X), float(VIDEO_GRID_Y));\n"
    "\tvec2 px   = 1.0 / vec2(float(VIDEO_ATLAS_W), float(VIDEO_ATLAS_H));\n"
    "\t// 全屏 pass 的 uv.y=0 在屏幕底部；纹理 v=0 在图像顶部，故格子行号直接用 gy，格内用 1-uv.y 翻转\n"
    "\tfloat vRow = float(gy);\n"
    "\tvec2 atlasUV = vec2(float(gx), vRow) * cell + px * 0.5 + vec2(uv.x, 1.0 - uv.y) * (cell - px);\n"
    "\n"
    "\tvec4 vid = texture2D(colortex1, atlasUV);\n"
    "\tfloat luma = (ch == 0) ? vid.r : (ch == 1) ? vid.g : (ch == 2) ? vid.b : vid.w;\n"
    "\tif (luma < lumaThreshold) return float(TRUE);\n"
    "\treturn float(FALSE);\n"
    "}\n"
) % (DURATION, N, cells, CH, cols, rows, atlas_w, atlas_h, CH, CH, CH)

with open(FINAL_FSH, "r", encoding="utf-8") as fp:
    src = fp.read()

start_marker = "// ===== 视频播放"
end_marker = "void main()"
si = src.index(start_marker)
ei = src.index(end_marker)
new_src = src[:si] + block + "\n\n" + src[ei:]

with open(FINAL_FSH, "w", encoding="utf-8", newline="\n") as fp:
    fp.write(new_src)
print("wrote final.fsh:", os.path.getsize(FINAL_FSH), "bytes")

# ---------- 5. 注册纹理绑定 ----------
with open(PROPS, "r", encoding="utf-8") as fp:
    props = fp.read()
if "texture.composite.colortex1" not in props:
    props = props.replace(
        "texture.gbuffers.gaux4 = texture/ramp.png\n",
        "texture.gbuffers.gaux4 = texture/ramp.png\n\ntexture.composite.colortex1 = texture/video.png\n",
        1,
    )
    with open(PROPS, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(props)
    print("added texture binding")
