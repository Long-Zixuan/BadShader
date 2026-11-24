# BadShader — Bedrock 26.50 移植版

把 `BadShader/shaders`（Iris/OptiFine GLSL 光影）的剪影反色效果移植到
Minecraft Bedrock **26.50**（Better RenderDragon 环境）。

产物：**`BadShader.mcpack`**

---

## 效果

画面中那个剪影（少女侧脸 + 举着的苹果）**内部颜色反转**，外部保持正常。

原版是「按游戏时间播放 3267 帧视频，视频里黑的地方反色」。
Bedrock 上时间不可得（见下文），所以改成**静态剪影遮罩**，只保留反色逻辑。

---

## 工程结构

```
BE/
├── project.json                  # lazurite 配置
├── build.bat                     # 一键构建 + 打包
├── package.ps1                   # 把 pack\ 打包成 BadShader.mcpack
├── .gitignore
├── BadShader.mcpack              # 产物
│
├── ColorPostProcessing/          # 唯一的材质
│   └── shaders/
│       ├── fragment.sc           # isInBlack() + 反色 + tonemap
│       ├── vertex.sc             # 全屏 quad
│       ├── varying.def.sc
│       └── bgfx_shader.sh
│
├── vanilla/
│   └── ColorPostProcessing.material.bin   # 原版材质（lazurite merge source）
│
├── pack/                         # 打包源（原样打进 mcpack）
│   ├── manifest.json             # 可自由编辑，脚本不会覆盖
│   ├── pack_icon.png
│   └── renderer/materials/       # build\ 的产物会被复制到这里
│
├── env/shaderc.exe               # 构建依赖
│
└── tools/
    ├── trace_silhouette.py       # 从图片描出轮廓（可重新生成顶点）
    ├── emit_fragment.py          # 生成 fragment.sc
    ├── clean_pack.ps1            # 游戏卡死时的恢复脚本
    └── artwork/mask.png          # 原始剪影图（描图源）
```

---

## 构建

```
build.bat
```

依赖：

- Python 3.10
- `lazurite==0.10.0`（`pip install lazurite==0.10.0`）
- `env\shaderc.exe` — 来自 `shaderc-win-x64.zip`（veka0/bgfx-mcbe），
  **解压出来是 `shadercRelease.exe`，需要改名成 `shaderc.exe`**
- `dxc.exe`（Windows SDK，用于 SM60/SM65 的 DXIL）

`package.ps1` 以 `pack\` 为准：`manifest.json`、`pack_icon.png` 原样打包，
只把 `build\` 里新编译的 `.material.bin` 复制进 `pack\renderer\materials\`。

---

## 关键实现

### 剪影用多边形存储，不是纹理

26.50 的材质系统**无法加载自定义 PNG**：

- `texture_path` 在原版所有材质里都是空字符串（解包 `Actor.material.bin` 验证过）
- 给材质加一个带 `texture_path` 的 buffer，读出来是未绑定的品红占位色

所以把图描成 209 个顶点的多边形，坐标逐行写进着色器——就是 SVG path 的做法。

### isInBlack()

保留原版函数名和语义：

```glsl
int isInBlack(vec2 uv) {
    float crossings = 0.0;
    crossings += edge(uv, vec2(ax, ay), vec2(bx, by));   // 共 209 行
    ...
    return (fract(crossings * 0.5) > 0.25) ? TRUE : FALSE;
}
```

偶奇规则（even-odd）判断点是否在多边形内。逐行展开而不是用数组，
因为当前 shaderc 版本的数组初始化会报 `vec4_splat` 未定义。

### tonemap()

```glsl
vec3 tonemap(vec3 c) {
    vec3 s = sqrt(max(c, vec3(0.0)));
    vec3 lift = vec3(1.12 + 0.45 * (1.0 - s.x), ...);
    return clamp(s * lift, vec3(0.0), vec3(1.0));
}
```

替换掉原版 `ColorPostProcessing` 会丢掉它的色调映射/调色，
不做这一步整个画面会非常暗。`sqrt` = gamma 2.0，`lift` 用来提亮中间调、保住高光。

---

## 无法移植的部分

| 原版功能 | 原因 |
|---|---|
| `frameTimeCounter` 视频播放（3267 帧） | `ColorPostProcessing` 拿不到任何时间 uniform |
| 最后 5 秒的 logo | 同上 |
| 深度 Sobel 描边 | `ColorPostProcessing` 的 6 个纹理槽只有 `ColorTexture` 有内容，没有深度 |

### 关于时间的验证记录

| 尝试 | 结果 |
|---|---|
| `uniform vec4 Time;`（自定义名字） | 材质校验失败 → **游戏卡死** |
| `uniform vec4 ViewPositionAndTime;`（引擎真实名字） | 材质加载正常，但**四个分量全读到 0** |

`RenderChunk`（地形材质）里 `ViewPositionAndTime` 是有效的（`.w` = 游戏时间），
但那是逐表面材质，做不了整屏效果。这个限制是引擎层面的。

---

## 重新生成剪影轮廓

如果换了图，或者要调整精度：

```
py -3.10 tools\emit_fragment.py tools\artwork\mask.png ColorPostProcessing\shaders\fragment.sc tools\_preview.png 0.0012
```

第 4 个参数是简化容差，越小顶点越多、越精确（0.0012 → 209 顶点）。

---

## 重要说明

**BRD 的资源包材质加载是可用的**（日志里有 `Loaded renderer/materials/...`），
但它加载失败的材质会让游戏卡死。测试时请确认：

- BRD 的 `Load Shaders from Resource Pack` 勾选
- 世界的资源包里启用本包
- 万一卡死：运行 `tools\clean_pack.ps1`（删自定义资源包 + 校验本体材质）
