# -*- coding: utf-8 -*-
"""
LS Bad Shader · Bad Apple 光影 · 网易我的世界（中国版）移植
================================================================

参数表与取值映射，全部来自原 OptiFine 光影 shaders/final.fsh 与 shaders.properties：

    RIM_OFFECT             深度采样偏移    0.0003    [0.0003 ... 0.01]
    OUTLINE_COL            描边颜色        0.3       [0.0 ... 0.9]
    OutlineDepthMultiplier 描边深度乘数    2.0       [0.1 ... 2.0]
    OutlineDepthBias       描边深度幂次    0.5       [0.1 ... 2.0]
    BAD_LINE               左侧反色条      OFF       [OFF ON]
    BAD_LINE_VALUE         反色条宽度      0.5       [0.0 ... 1.0]
    PAPER_WORLD            仅黑白世界      ON        [OFF ON]

说明：原光影里只作用于逐物体 gbuffers 阶段的参数（阴影 ENABLE_SHADOWS / SOFT_SHADOWS /
shadowMapResolution / SHADOW_DISTANCE、Shininess、CEL、纹理描边 ENABLE_TEXTURE_OUTLINES /
TEXTURE_OUTLINE_STRENGTH / OUTLINE_THICKNESS）在网易的全屏后处理管线里没有对应的计算位置，
按需求本次不移植进设置界面。

本模块不依赖任何引擎 API，方便单独做单元校验。
"""

MOD_NAME = "LSBadShader"
MOD_VERSION = "1.0.0"
MOD_DISPLAY_NAME = u"BadShader"
MOD_DESCRIPTION = u"Bad Apple 光影"


def api_text(text):
    """把界面文字转成网易 Python2 绑定能吃的 UTF-8 字节串。

    直接用 u"中文" 传给 AddText / AddToggle / AddSlider / RegisterSettingInst，
    在这版 SDK 上标签会渲染成空白（字体并不缺中文，是参数类型不对）。
    脚本运行在 Python 2，必须 encode("utf-8") 成 str。
    """
    try:
        if isinstance(text, unicode):  # noqa: F821  (Python 2 only)
            return text.encode("utf-8")
    except NameError:
        pass
    return text

# ---- 通用设置界面（暂停菜单 - 模组）-------------------------------------
# 第一个参数在正式服是平台分配的 ItemID，上传模组后请替换成自己的 ItemID。
SETTING_ITEM_ID = "LSBadShader"
SETTING_ICON = "textures/ui/LSBadShader_icon"

# ---- 后处理 -------------------------------------------------------------
# 后处理效果名与材质名：材质定义在资源包 materials/postprocess.material 里
POST_EFFECT_NAME = "LSBadShader_badapple"
PROCESS_NAME = POST_EFFECT_NAME
MATERIAL_NAME = "LSBadShader_badapple"

# 三个参数槽，每槽一个 vec4（对应 shader 的 EXTRA_VECTOR1..3）
PARAM_A = "p_a"
PARAM_B = "p_b"
PARAM_C = "p_c"

# bindTexture：按顺序绑到 3、4 号纹理槽（depth_enable=true 时深度占 2 号槽）
VIDEO_TEXTURE = "textures/postprocess/LSBadShader_video"
LOGO_TEXTURE = "textures/postprocess/LSBadShader_logo"

# ---- 音频（资源包 sounds/sound_definitions.json 中注册的名字）------------
# 工程根目录的 badapple.mp3 是母版，包内放的是同源转码的 sounds/badapple.ogg。
AUDIO_NAMES = ("lsbadshader:badapple", "lsbadshader.badapple")
AUDIO_FADE_OUT = 0.2

# ---- 屏幕尺寸兜底（真实值由 GetScreenSize 获取）-------------------------
DEFAULT_SCREEN_SIZE = (1920.0, 1080.0)

# ---- 滑块默认值（滑块取值范围 0~100）------------------------------------
DEFAULT_SLIDERS = {
    "rim_offect": 2,        # RIM_OFFECT      ≈ 0.0003
    "outline_col": 33,      # OUTLINE_COL     ≈ 0.30
    "depth_mul": 100,       # depth multiplier = 2.0
    "depth_bias": 21,       # depth bias      ≈ 0.50
    "bad_line_value": 50,   # BAD_LINE_VALUE  = 0.50
    "volume": 60,           # 音量 60%
}

DEFAULT_TOGGLES = {
    "paper_world": True,    # PAPER_WORLD = ON
    "bad_line": False,      # BAD_LINE = OFF
    "bgm": True,            # 进世界即播放 badapple.mp3
}

# ---- 设置界面控件表 -----------------------------------------------------
# (key, 控件类型, 显示文字, 优先级)
SETTING_SPECS = (
    ("text_shader", "text", u"LoongLy SoftWare 2026", 0),
    ("paper_world", "toggle", u"仅黑白世界（PAPER_WORLD）", 1),
    ("outline_col", "slider", u"描边颜色深浅（OUTLINE_COL 0.0~0.9）", 2),
    ("rim_offect", "slider", u"描边采样精度（RIM_OFFECT 0.0001~0.01）", 3),
    ("depth_mul", "slider", u"描边强度（OutlineDepthMultiplier 0.1~2.0）", 4),
    ("depth_bias", "slider", u"描边收敛（OutlineDepthBias 0.1~2.0）", 5),
    ("bad_line", "toggle", u"左侧整列反色（开启后暂停 Bad Apple 画面与 logo）", 6),
    ("bad_line_value", "slider", u"反色条宽度（BAD_LINE_VALUE 0~1）", 7),
    ("text_audio", "text", u"音频", 8),
    ("bgm", "toggle", u"播放 Bad Apple", 9),
    ("volume", "slider", u"音量（0~100）", 10),
)

SLIDER_MAX = 100


def _clamp01(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def slider_ratio(value):
    """滑块 0~100 -> 0.0~1.0"""
    try:
        ratio = float(value) / float(SLIDER_MAX)
    except (TypeError, ValueError):
        ratio = 0.0
    return _clamp01(ratio)


def rim_offect(value):
    """RIM_OFFECT：原光影取值 0.0003~0.01"""
    return 0.0001 + 0.0099 * slider_ratio(value)


def outline_col(value):
    """OUTLINE_COL：原光影取值 0.0~0.9"""
    return 0.9 * slider_ratio(value)


def depth_multiplier(value):
    """OutlineDepthMultiplier：原光影取值 0.1~2.0"""
    return 0.1 + 1.9 * slider_ratio(value)


def depth_bias(value):
    """OutlineDepthBias：原光影取值 0.1~2.0"""
    return 0.1 + 1.9 * slider_ratio(value)


def bad_line_value(value):
    """BAD_LINE_VALUE：原光影取值 0.0~1.0"""
    return slider_ratio(value)


def flag(value):
    """开关 -> shader 里的 0.0 / 1.0"""
    return 1.0 if value else 0.0


def build_vectors(sliders, toggles, screen_size, video_clock=0.0):
    """把界面取值换算成 3 个 vec4，对应 shader 里的 EXTRA_VECTOR1..3：

        EXTRA_VECTOR1 = (RIM_OFFECT, OUTLINE_COL, OutlineDepthMultiplier, OutlineDepthBias)
        EXTRA_VECTOR2 = (BAD_LINE, BAD_LINE_VALUE, PAPER_WORLD, viewWidth)
        EXTRA_VECTOR3 = (viewHeight, videoClock, 0, 0)

    videoClock 是「进入世界后的真实秒数」，由客户端系统每 tick 更新。
    网易引擎的 TIME 是 0~210 秒循环的，而视频总长 217.77 秒，
    直接用 TIME 会在 210 秒处跳帧、并且永远看不到最后 5 秒的 logo。
    """
    width, height = DEFAULT_SCREEN_SIZE
    try:
        if screen_size and float(screen_size[0]) > 0.0 and float(screen_size[1]) > 0.0:
            width, height = float(screen_size[0]), float(screen_size[1])
    except (TypeError, ValueError, IndexError):
        pass

    try:
        clock = max(0.0, float(video_clock))
    except (TypeError, ValueError):
        clock = 0.0

    vec_a = [
        float(rim_offect(sliders.get("rim_offect", DEFAULT_SLIDERS["rim_offect"]))),
        float(outline_col(sliders.get("outline_col", DEFAULT_SLIDERS["outline_col"]))),
        float(depth_multiplier(sliders.get("depth_mul", DEFAULT_SLIDERS["depth_mul"]))),
        float(depth_bias(sliders.get("depth_bias", DEFAULT_SLIDERS["depth_bias"]))),
    ]
    vec_b = [
        float(flag(toggles.get("bad_line", DEFAULT_TOGGLES["bad_line"]))),
        float(bad_line_value(sliders.get("bad_line_value", DEFAULT_SLIDERS["bad_line_value"]))),
        float(flag(toggles.get("paper_world", DEFAULT_TOGGLES["paper_world"]))),
        float(width),
    ]
    vec_c = [float(height), clock, 0.0, 0.0]
    return vec_a, vec_b, vec_c


def build_process(sliders, toggles, screen_size, video_clock=0.0):
    """给 AddPostProcess 用的自定义后处理定义。

    结构照抄引擎内置的 oldtv / scanmap：paras 里每一项是一个 vec4，
    会依次对应 shader 里的 EXTRA_VECTOR1、EXTRA_VECTOR2、EXTRA_VECTOR3。
    """
    vec_a, vec_b, vec_c = build_vectors(sliders, toggles, screen_size, video_clock)
    return {
        "name": PROCESS_NAME,
        "enable": True,
        "paras": [
            {"name": PARAM_A, "value": vec_a, "range": [-1000.0, 8192.0]},
            {"name": PARAM_B, "value": vec_b, "range": [-1.0, 8192.0]},
            {"name": PARAM_C, "value": vec_c, "range": [-1.0, 1000000.0]},
        ],
        "pass_array": [
            {
                "render_target": {"width": 1.0, "height": 1.0},
                "material": MATERIAL_NAME,
                "depth_enable": True,
                "bindTexture": [
                    {"texture": VIDEO_TEXTURE},
                    {"texture": LOGO_TEXTURE},
                ],
            }
        ],
    }
