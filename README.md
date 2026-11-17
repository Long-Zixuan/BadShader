# LS Bad Shader × 网易我的世界（中国版）

把仓库里这套 OptiFine 光影（`shaders/final.fsh` 的深度描边 + Bad Apple 视频反色）移植成网易中国版
**Addon**：自定义后处理 `LSBadShader_badapple` 负责画面，Python 通过官方 **通用设置接口** 在
「暂停菜单 → 模组 → 模组设置」里提供参数入口，并播放 `badapple.mp3`（带音量调节）。

> 新生成的所有文件都在本 `ne_be` 目录下；`addon` 是文件夹，不是 zip。

---

## 0. 导入后「模组列表空、画面无变化」的原因与修复

用 MC Studio 直接导入 `ne_be/addon` 这个**文件夹**本来就是正确方式，问题出在行为包的清单文件上。

本次从你这台机器上取到的证据：

* 启动配置 `D:\MCStudioDownload\game\config\zixuan_pro@163.com\Cpp\MC_GAME\<guid>.cppconfig` 里写的是：

  ```json
  "resource_packs": [ "resource_pack_LSBadShader" ],
  "behavior_packs": []
  ```

  也就是**资源包挂上了、行为包整包被丢掉**。行为包不挂载 → Python 一行都不跑 → 模组列表是空的。

* 原因一（决定性）：**行为包缺少 `entities` 文件夹**。引擎/服务端判定「这是不是一个行为包」时会看这个
  标准目录，缺了就直接报「当前服务端无加载行为包，请确认是否遗漏 entities 文件夹」，然后整包不挂载。
  本机以前能用的 `LSOutlineShaderNE_Beh` 里就有 `entities\.gitkeep`（0 字节占位）。
* 原因二：行为包的 `manifest.json` 里还多了一个 `dependencies`，指向资源包的 UUID。本地导入的作品里
  这个 UUID 没注册成「已安装组件」，解析依赖失败也会让包不可用。资源包没有这个字段，所以它能挂上。

* 已修复：
  1. 补上 `behavior_pack_LSBadShader/entities/.gitkeep`（0 字节占位，和旧作品一致；空目录在压缩/传输时
     容易丢，所以放个占位文件）。
  2. 删掉 `dependencies`。

行为包能挂上之后又暴露出两个问题，也一并修了：

* 日志报 `TypeError: 'module' object is not callable`（`LoadWindowsAddonPy: LSBadShaderScripts.modMain`）：
  我的 `modMain.py` 在顶层 import 了自己的系统模块，还在 `InitServer` 里注册了服务端系统。
  引擎加载入口时只认官方模板那种最简写法，已按模板重写：顶层只 import `Mod` 与 `clientApi`，
  `InitServer` 留空，客户端系统用字符串路径在 `InitClient` 里注册。
* 资源包挂上了但画面没变化：我原来是想靠覆盖 `vanilla_netease/graphics_settings/post_process.json`
  静态注册后处理，这条路不生效；而且覆盖 `materials/postprocess.material` 时只写了自己一个材质，
  等于把内置 17 个后处理材质全顶掉了。已改成能跑作品的做法——后处理用 Python
  `AddPostProcess` 动态挂载，材质文件带上内置全量再追加我们的，并补上 `materials/common.json`。

验证方法：重新「开发测试」后，打开最新的
`D:\MCStudioDownload\game\config\<你的账号>\Cpp\MC_GAME\*.cppconfig`，
`"behavior_packs"` 里应该出现 `"behavior_pack_LSBadShader"`。

进游戏后：暂停菜单 → 模组 → 模组设置 里应出现 `LSBadShader · Bad Apple 光影`；
日志里搜 `[LSBadShader]` 能看到 `play lsbadshader:badapple` 之类的行。

---

## 1. 目录结构

```
ne_be/
├── README.md
├── badapple.mp3                            ← 你提供的原始 mp3（母版，原样保留）
└── addon/
    ├── behavior_pack_LSBadShader/           行为包（Python 逻辑）
    │   ├── manifest.json
    │   ├── pack_icon.png                    ← badapple_icon.png 原图
    │   ├── entities/                        行为包标准目录（.gitkeep 占位，缺了引擎不认这个包）
    │   └── LSBadShaderScripts/
    │       ├── __init__.py
    │       ├── modMain.py                   模组入口（只注册客户端系统）
    │       ├── LSBadShaderConfig.py         参数表、界面取值换算、后处理定义
    │       └── LSBadShaderClientSystem.py   设置界面 + 后处理 + 音频 + 视频时钟
    └── resource_pack_LSBadShader/           资源包（着色器 / 贴图 / 音频）
        ├── manifest.json
        ├── pack_icon.png                    ← badapple_icon.png 原图
        ├── materials/
        │   ├── common.json                  声明加载 postprocess.material（必需）
        │   └── postprocess.material         内置 17 个材质 + 我们的 LSBadShader_badapple
        ├── shaders/glsl/
        │   ├── LSBadShader_badapple.fragment 由 final.fsh 移植的全屏片元着色器
        │   └── uv_fullscreen.vertex         全屏顶点着色器（引擎同款副本）
        ├── textures/
        │   ├── postprocess/
        │   │   ├── LSBadShader_video.png    ← 原 shaders/texture/video.png（帧图集）
        │   │   └── LSBadShader_logo.png     ← 原 shaders/texture/logo.png
        │   └── ui/
        │       └── LSBadShader_icon.png     设置界面用的模组图标（同一张原图）
        └── sounds/
            ├── badapple.ogg                 由母版 mp3 转码、引擎实际播放的文件
            └── sound_definitions.json
```

`badapple.mp3` 放在 `ne_be/` 根目录当母版；包内 `sounds/` 只放转码后的 `badapple.ogg`。
两者**不能同名同目录**——`sound_definitions.json` 里的 `sounds/badapple` 是按去扩展名解析的，
同名 mp3/ogg 并存时引擎可能挑到 mp3，而基岩引擎不解码 mp3。

---

## 2. 对着这台机器的客户端（MinecraftPE_Netease 3.10.0.448891）核对过的事实

这一版把「按文档猜」的地方全改成按引擎实包、以及本机那个能跑的 `LSOutlineShaderNE_*` 作品核对：

| 项目 | 引擎/能跑作品的实际情况 | 我们的做法 |
| --- | --- | --- |
| 行为包结构 | 必须有 `entities/`，否则报「当前服务端无加载行为包」并把整包丢掉 | 已补 `entities/.gitkeep` |
| 行为包清单 | 不能带 `dependencies`（本地导入时指向的组件没注册，解析失败整包被排除） | 已删除该字段 |
| `modMain.py` | 官方模板只在顶层 import `Mod` 和 `clientApi`，`InitServer` 留空；顶层再牵进自己的系统模块会加载失败（`TypeError: 'module' object is not callable`） | 已按模板重写，`InitServer` 空实现，客户端系统用字符串路径注册 |
| 后处理挂载 | 能跑的作品**不覆盖** `vanilla_netease/graphics_settings/post_process.json`，而是 Python `AddPostProcess(dict, -1)` 动态注册 | 改为动态注册，删掉了静态覆盖文件 |
| `paras` 结构 | 每一项是一个 vec4（`{"name":..,"value":[4 个 float],"range":[..]}`），依次对应 `EXTRA_VECTOR1..N` | 3 个 vec4 对应 `EXTRA_VECTOR1..3` |
| 材质文件 | `materials/postprocess.material` 是扁平的**全量**文件：覆盖它就会顶掉内置 17 个后处理材质，必须整份带上；还要 `materials/common.json` 声明加载 | 已改成「内置 17 个 + 我们的 1 个」并补 `common.json` |
| 着色器路径 | 内置材质写 `shaders/tutorial/old_tv.fragment`，实际文件在 `shaders/tutorial/glsl/` 下；`shaders/uv_fullscreen.vertex` 对应 `shaders/glsl/uv_fullscreen.vertex` | 材质里写 `shaders/LSBadShader_badapple.fragment`，文件放 `shaders/glsl/` |
| `TIME` | `uniformPerFrameConstants.h` 注释写明 **“TIME will loop from [0, 210]”** | 视频 217.77 秒撑不满 210 秒循环，改用 Python 每 tick 推 `videoClock` |
| 埋点约定 | `// __multiversion__` → `precision highp float;` → `#include` → `LAYOUT_BINDING(n)` → `uniform vec4 EXTRA_VECTOR1` → `gl_FragColor` | 一致 |
| `SetParameter` 时机 | 对「关闭状态」的自定义后处理写参数会被拒绝，能跑的作品先 `SetEnableByName(True)` 再写 | 同样先开再写 |
| 界面文字 | 脚本跑在 Python 2，网易的绑定要 **UTF-8 字节串**；直接传 `u"中文"` 给 `AddText`/`AddToggle`/`AddSlider`/`RegisterSettingInst`，标签会渲染成空白（字体本身不缺中文） | 统一过 `Config.api_text()` 做 `encode("utf-8")` |
| 返回值判定 | `AddPostProcess` / `SetParameter` / `PlayCustomUIMusic` 在不同版本可能返回 `True` 或 `None` | 只有明确 `False` 才算失败，避免重复起播/反复重建 |

**`videoClock` 是顺手修的一个真问题**：原来直接 `#define frameTimeCounter TIME`，
而 TIME 在 210 秒处回绕，会导致视频在 210 秒跳帧、并且永远看不到「最后 5 秒的 logo」。
现在由 `LSBadShaderClientSystem.py` 每 tick 把「进世界后的真实秒数」写进 `EXTRA_VECTOR3.y`，
着色器里 `frameTimeCounter` 优先用它，Python 还没写进来时才退回 `TIME` 兜底。
音频与视频都从进入世界开始计时，所以两者同步。

---

## 3. 移植过来的画面逻辑

`shaders/glsl/LSBadShader_badapple.fragment` 的主体是从 `shaders/final.fsh` 逐行搬过来的，
只有「输入从哪来」这一层做了替换，计算本身没动：

| OptiFine 的输入 | 网易后处理里的来源 |
| --- | --- |
| `colortex0`（场景颜色） | `TEXTURE_0` |
| `depthtex0`（深度） | `TEXTURE_2`（pass 里 `depth_enable: true`） |
| `colortex1`（帧图集 video.png） | `TEXTURE_3`（`bindTexture` 第 1 项） |
| `colortex2`（logo.png） | `TEXTURE_4`（`bindTexture` 第 2 项） |
| `texcoord` | `uv`（`fragmentVersionCentroidUV.h`） |
| `frameTimeCounter` | `EXTRA_VECTOR3.y`（Python 每 tick 写入），回退 `TIME` |
| `gbufferProjectionInverse` / `far` | 由 `PROJ` 现场推导 |
| `#define` 常量参数 | `EXTRA_VECTOR1..3`（`SetParameter` 运行时写入） |
| `gl_FragData[0]` | `gl_FragColor` |

保留原样：`screenSpaceToViewSpace` / `screenDepth2LinearDepth`（含 `FALLOFF_CURVE` 分支与
`1.0 - linearDepth`）、`SobelDepth` / `SobelSampleDepth` 五点采样、
`pow(clamp(sobel)*OutlineDepthMultiplier, OutlineDepthBias)` 与 `mix`、
`isInBlack()` 的「帧号 → 格子/通道（每格 4 帧 RGBA）→ 与 0.5 比阈值反色」、
最后 5 秒 logo 的 8 邻域描边、`BAD_LINE` 左侧反色。

必要的「接线级」改动：

1. **`PAPER_WORLD`**：原光影在 `gbuffers_*.fsh` 里把世界颜色写成白色，网易后处理没有逐物体阶段，
   所以在读入场景色后立刻执行同一句，整帧刷白（覆盖面比原版略大），alpha 沿用原逻辑。
2. **投影矩阵求逆**：OptiFine 直接给 `gbufferProjectionInverse`，网易只给 `PROJ`，
   用一份手写的 `lsMat4Inverse()` 求逆（已用 numpy 对 200 组随机矩阵比对，误差 ~1e-12），
   `far` 由 `PROJ[3][2] / (PROJ[2][2] + 1.0)` 推导并带回退兜底。
3. **浮点字面量**：原文件 `#version 120` 允许 int 隐式转 float，网易会编成 `#version 100`
   （ESSL 1.00 没有隐式转换），所以 `SCREEN_VALUE 2000.0`、`vec4(..., 1.0)`、`1.0 - color.x`
   都补成了浮点写法，语义不变。

---

## 4. 设置界面里的参数

按你的选择：**只保留在网易后处理里真正生效的参数**。全部来自原 `shaders.properties`。

| 界面上的选项 | 原光影参数 | 原默认值 | 界面取值 → shader 取值 |
| --- | --- | --- | --- |
| 仅黑白世界 | `PAPER_WORLD` | `ON` | 开关 → 0 / 1 |
| 描边颜色深浅 | `OUTLINE_COL` | `0.3` | 0~100 → `0.9·v/100` |
| 描边采样精度 | `RIM_OFFECT` | `0.0003` | 0~100 → `0.0001 + 0.0099·v/100` |
| 描边强度 | `OutlineDepthMultiplier` | `2.0` | 0~100 → `0.1 + 1.9·v/100` |
| 描边收敛 | `OutlineDepthBias` | `0.5` | 0~100 → `0.1 + 1.9·v/100` |
| 左侧整列反色 | `BAD_LINE` | `OFF` | 开关 → 0 / 1（**开启后原代码会跳过 Bad Apple 画面和 logo**） |
| 反色条宽度 | `BAD_LINE_VALUE` | `0.5` | 0~100 → `v/100` |
| 播放 Bad Apple | —（新增） | 开 | 开关 |
| 音量 | —（新增） | 60 | 0~100（0 等于静音停止） |

打包顺序（`Config.build_process()` 里的 `paras` 顺序，必须与着色器里的 `EXTRA_VECTOR` 一致）：

```
EXTRA_VECTOR1 = (rimOffset, outlineCol, depthMultiplier, depthBias)   # p_a
EXTRA_VECTOR2 = (badLine, badLineValue, paperWorld, screenWidth)       # p_b
EXTRA_VECTOR3 = (screenHeight, videoClock, -, -)                        # p_c
```

### 没有移植的参数（说明原因，不是漏掉）

| 参数 | 为什么没进界面 |
| --- | --- |
| `ENABLE_SHADOWS` / `SOFT_SHADOWS` / `shadowMapResolution` / `SHADOW_DISTANCE` | 只在 gbuffers 逐物体光照阶段生效；网易后处理没有阴影采样阶段 |
| `Shininess` | 同上（水面高光在 gbuffers_water.fsh 里） |
| `CEL` | 同上（对 lightmap 做 ramp 量化） |
| `ENABLE_TEXTURE_OUTLINES` / `TEXTURE_OUTLINE_STRENGTH` / `OUTLINE_THICKNESS` | 需求里明确排除「纹理描边」 |
| `THRESHOLD` | 原 `final.fsh` 里声明了但**从未参与计算**，调它本来也不会有变化 |

---

## 5. 音频

* `badapple.mp3` 原样放在 `ne_be/badapple.mp3`（3.49 MB / 217.81 秒），与原光影
  `VIDEO_DURATION = 217.766667` 对得上。
* 基岩引擎只播 `.ogg` / `.fsb`，同一份音频用 ffmpeg 转成 `sounds/badapple.ogg`
  （Vorbis / 44.1 kHz / 2ch，实测 217.78 秒）；`sound_definitions.json` 里
  `sounds/badapple` 会命中它。
* Python 用 `PlayCustomUIMusic(name, volume, 1.0, True)` 循环播放，播放前
  `DisableOriginMusic(True)` 关原版 BGM；改音量会 `StopCustomMusic` 后用新音量重起播。
* `PlayCustomUIMusic` 的返回值在不同版本可能是 `True` 也可能是 `None`，
  代码里只有明确 `False` 才算失败，避免同一首歌被当成失败再播一遍、叠成两轨。

---

## 6. 已知限制

1. **帧图集是 5568×3132 的单张贴图**（原 `video.png`，10.4 MB，29×29 格、每格 192×108 装 4 帧）。
   PC 上没问题；部分低端手机对超大贴图有上限，视频区域不显示时需按原 `encode_video.py`
   的打包方式重新切分图集（着色器里的 `VIDEO_*` 常量要一起改）。
2. **后处理是动态注册的**：由 `AddPostProcess` 在进世界时挂上去，不覆盖内置的
   `post_process.json`，所以原版 bloom / 老电视 / 扫描等效果仍然在，只是默认不开启。
3. 音乐与画面都从进入世界开始计时，暂停、换维度后可能轻微错位，重进世界即可对齐。
4. 想调效果不用碰着色器：改 `LSBadShaderConfig.py` 里的
   `rim_offect()` / `outline_col()` / `depth_multiplier()` / `depth_bias()` / `bad_line_value()`。

---

## 7. 排错

| 现象 | 先检查什么 |
| --- | --- |
| 模组列表空、画面无变化 | 看启动配置 `<guid>.cppconfig` 里的 `"behavior_packs"` 是不是空的（见第 0 节），再看日志 `[LSBadShader]` |
| 日志有 `RegisterSettingInst returned None` | 注册太早，重进世界即可（代码已按 `UiInitFinished` 注册） |
| 有描边、没有 Bad Apple 画面 | 帧图集贴图未加载（见限制 1），或 `bindTexture` 槽位被别的后处理占用 |
| 画面完全没有后处理效果 | 日志里有没有 `AddPostProcess(...) -> True`；材质名与 `Config.MATERIAL_NAME`、`PROCESS_NAME` 是否都是 `LSBadShader_badapple`；`materials/common.json` 是否声明了 `materials/postprocess.material` |
| 设置页里控件的文字是空白 | 传给 `AddText`/`AddToggle`/`AddSlider` 的文字必须是 UTF-8 字节串，用 `Config.api_text()` 包一层（直接传 `u"中文"` 就会空标签） |
| 日志报 `TypeError: 'module' object is not callable` | `modMain.py` 又被写回了「顶层 import 自己的系统模块」或「InitServer 里注册服务端系统」的写法，恢复成现在的模板形态 |
| 音效不响 | `sounds/sound_definitions.json` 的 key 与 `LSBadShaderConfig.AUDIO_NAMES` 是否一致；`.ogg` 是否在 `sounds/` 下 |
| 设置页里没有本模组 | `RegisterSettingInst` 第一个参数要换成平台分配的 ItemID（`LSBadShaderConfig.SETTING_ITEM_ID`） |

---

## 8. 从原仓库搬过来的对照表

| 原文件 | 现在的去处 | 处理方式 |
| --- | --- | --- |
| `shaders/final.fsh` | `shaders/glsl/LSBadShader_badapple.fragment` | 核心逻辑逐行移植 |
| `shaders/shaders.properties` | `LSBadShaderConfig.py` + 通用设置界面 | 参数变成官方 SettingInst 控件 |
| `shaders/texture/video.png` | `textures/postprocess/LSBadShader_video.png` | 原样 |
| `shaders/texture/logo.png` | `textures/postprocess/LSBadShader_logo.png` | 原样 |
| `shaders/texture/cel_ramp.png` / `ramp.png` / `blueNoiseR.png` | — | 只有 gbuffers 阶段的 CEL / PCF 噪声用得到，本次不移植 |
| `shaders/gbuffers_*.fsh|vsh`、`shadow.*` | — | 网易后处理没有逐物体/阴影阶段，无法对位移植 |
| `badapple_icon.png` | 两个包的 `pack_icon.png` + `textures/ui/LSBadShader_icon.png` | 原图，未重新生成 |
