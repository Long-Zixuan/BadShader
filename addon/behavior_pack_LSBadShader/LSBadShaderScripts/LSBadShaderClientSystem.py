# -*- coding: utf-8 -*-
"""
LS Bad Shader · 客户端系统

职责：
    1. 用官方 AddPostProcess 动态挂载自定义后处理 LSBadShader_badapple
       （不覆盖内置 post_process.json，内置的 bloom / oldtv 等不受影响）。
    2. 把设置界面的取值打包成 3 个 vec4，通过 SetParameter 写进 shader。
    3. 用官方通用设置接口在「暂停菜单 → 模组」注册参数入口（不自绘 UI）。
    4. 播放 / 停止 badapple.mp3，并提供音量控制。
"""

try:
    import mod.client.extraClientApi as clientApi
except ImportError:  # 很老的 SDK 目录结构
    import client.extraClientApi as clientApi

from LSBadShaderScripts import LSBadShaderConfig as Config

try:
    import time as _time
except Exception:  # 极端环境禁用了标准库，退回按 tick 计时
    _time = None

ClientSystem = clientApi.GetClientSystemCls()


def _log(message):
    print("[LSBadShader] " + str(message))


class LSBadShaderClientSystem(ClientSystem):

    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        self.mSettingInst = None
        self.mSliders = dict(Config.DEFAULT_SLIDERS)
        self.mToggles = dict(Config.DEFAULT_TOGGLES)
        self.mScreenSize = Config.DEFAULT_SCREEN_SIZE
        self.mAudioPlaying = False
        self.mAudioName = None
        self.mAudioComp = None
        self.mPostComp = None
        self.mProcessReady = False
        self.mLogged = False
        self.mClockStart = None
        self.mTickCount = 0
        self.ListenEvent()
        _log("client system init")

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def ListenEvent(self):
        engineNS = clientApi.GetEngineNamespace()
        engineName = clientApi.GetEngineSystemName()
        listeners = (
            ("UiInitFinished", self.OnUiInitFinished),
            ("ScreenSizeChangedClientEvent", self.OnScreenSizeChanged),
            ("OnScriptTickClient", self.OnClientTick),
        )
        for eventName, callback in listeners:
            try:
                self.ListenForEvent(engineNS, engineName, eventName, self, callback)
            except Exception as exc:
                _log("ListenForEvent %s failed: %s" % (eventName, exc))

    def OnUiInitFinished(self, args=None):
        """UI 就绪 / 每次进入世界：注册设置、挂后处理、起播。"""
        _log("UiInitFinished")
        self.RefreshScreenSize()
        self.RegisterSettings()
        self.ResetVideoClock()
        self.Apply()
        self.UpdateAudio(force=True)

    def OnScreenSizeChanged(self, args=None):
        self.RefreshScreenSize()
        self.Apply()

    def OnClientTick(self, args=None):
        self.mTickCount += 1
        if not self.mProcessReady:
            # 进世界早期后处理可能还建不起来，逐 tick 重试
            self.Apply()
            return
        post = self.mPostComp
        if post is None:
            return
        try:
            post.SetParameter(Config.PROCESS_NAME, Config.PARAM_C, self.BuildVecC())
        except Exception as exc:
            _log("SetParameter(%s) failed: %s" % (Config.PARAM_C, exc))
            self.mProcessReady = False

    # ------------------------------------------------------------------
    # 屏幕尺寸 / 视频时钟
    # ------------------------------------------------------------------
    def RefreshScreenSize(self):
        try:
            width, height = clientApi.GetScreenSize()
            if width and height and width > 0 and height > 0:
                self.mScreenSize = (float(width), float(height))
                return
        except Exception as exc:
            _log("GetScreenSize failed: %s" % exc)
        _log("screen size fallback: %s" % (self.mScreenSize,))

    def ResetVideoClock(self):
        self.mTickCount = 0
        self.mClockStart = _time.time() if _time is not None else None

    def GetVideoClock(self):
        if self.mClockStart is not None:
            try:
                return max(0.0, _time.time() - self.mClockStart)
            except Exception:
                pass
        return self.mTickCount / 20.0

    def BuildVecC(self):
        return [float(self.mScreenSize[1]), float(self.GetVideoClock()), 0.0, 0.0]

    # ------------------------------------------------------------------
    # 后处理
    # ------------------------------------------------------------------
    def GetPostComp(self):
        if self.mPostComp is not None:
            return self.mPostComp
        try:
            self.mPostComp = clientApi.GetEngineCompFactory().CreatePostProcess(
                clientApi.GetLevelId())
        except Exception as exc:
            _log("CreatePostProcess failed: %s" % exc)
        return self.mPostComp

    def EnsureProcess(self, post):
        if self.mProcessReady:
            return True
        order = []
        try:
            order = post.GetPostProcessOrder()
        except Exception as exc:
            _log("GetPostProcessOrder failed: %s" % exc)
        if not order:
            order = []
        if not self.mLogged:
            self.mLogged = True
            _log("post-process order: %s" % (order,))

        if Config.PROCESS_NAME in order:
            self.mProcessReady = True
            return True

        try:
            definition = Config.build_process(self.mSliders, self.mToggles,
                                              self.mScreenSize, self.GetVideoClock())
            ok = post.AddPostProcess(definition, -1)
            _log("AddPostProcess(%s) -> %s" % (Config.PROCESS_NAME, ok))
        except Exception as exc:
            _log("AddPostProcess failed: %s" % exc)
            return False
        self.mProcessReady = True
        return True

    def Apply(self):
        post = self.GetPostComp()
        if post is None:
            return
        if not self.EnsureProcess(post):
            return

        # 有些版本对「关闭状态」的自定义后处理拒绝 SetParameter，先开再写
        try:
            post.SetEnableByName(Config.PROCESS_NAME, True)
        except Exception as exc:
            _log("SetEnableByName failed: %s" % exc)

        vec_a, vec_b, vec_c = Config.build_vectors(self.mSliders, self.mToggles,
                                                   self.mScreenSize, self.GetVideoClock())
        ok = True
        for name, value in ((Config.PARAM_A, vec_a),
                            (Config.PARAM_B, vec_b),
                            (Config.PARAM_C, vec_c)):
            try:
                ret = post.SetParameter(Config.PROCESS_NAME, name, value)
            except Exception as exc:
                _log("SetParameter %s failed: %s" % (name, exc))
                ret = False
            # 只有明确返回 False 才算失败，None 也当成功（不同版本返回值不一致）
            if ret is False:
                ok = False
        if not ok:
            self.mProcessReady = False

    # ------------------------------------------------------------------
    # 通用设置界面
    # ------------------------------------------------------------------
    def RegisterSettings(self):
        if self.mSettingInst is not None:
            self.LoadSavedValues()
            return
        try:
            levelId = clientApi.GetLevelId()
            comp = clientApi.GetEngineCompFactory().CreateNeteaseWindow(levelId)
            if not comp:
                _log("CreateNeteaseWindow returned None")
                return
            settingInst = comp.RegisterSettingInst(
                Config.SETTING_ITEM_ID, Config.api_text(Config.MOD_DISPLAY_NAME),
                Config.SETTING_ICON)
            if not settingInst:
                _log("RegisterSettingInst returned None (稍后重试)")
                return
            self.mSettingInst = settingInst

            for key, kind, name, priority in Config.SETTING_SPECS:
                label = Config.api_text(name)
                if kind == "text":
                    settingInst.AddText(key, label, priority)
                elif kind == "toggle":
                    settingInst.AddToggle(key, label, self.OnSettingChanged,
                                          priority, Config.DEFAULT_TOGGLES.get(key, False))
                elif kind == "slider":
                    settingInst.AddSlider(key, label, Config.SLIDER_MAX,
                                          self.OnSettingChanged, priority,
                                          Config.DEFAULT_SLIDERS.get(key, 0))
            _log("settings registered")
            self.LoadSavedValues()
        except Exception as exc:
            _log("RegisterSettings failed: %s" % exc)

    def LoadSavedValues(self):
        inst = self.mSettingInst
        if not inst:
            return
        for key, kind, _name, _priority in Config.SETTING_SPECS:
            try:
                if kind == "toggle":
                    value = inst.GetToggleDefault(key)
                    if value is not None:
                        self.mToggles[key] = bool(value)
                elif kind == "slider":
                    value = inst.GetSliderDefault(key)
                    if value is not None:
                        self.mSliders[key] = int(value)
            except Exception as exc:
                _log("read default %s failed: %s" % (key, exc))

    def OnSettingChanged(self, *args):
        """所有控件的统一回调：args = (控件 key, 控件当前值)。"""
        if not args:
            return
        key = args[0]
        value = args[1] if len(args) > 1 else None

        if key in Config.DEFAULT_TOGGLES:
            self.mToggles[key] = bool(value)
        elif key in Config.DEFAULT_SLIDERS:
            try:
                self.mSliders[key] = int(value)
            except (TypeError, ValueError):
                return
        else:
            return

        self.RememberValue(key, value)
        self.Apply()
        self.UpdateAudio(force=(key == "volume"))

    def RememberValue(self, key, value):
        inst = self.mSettingInst
        if not inst:
            return
        try:
            if key in Config.DEFAULT_TOGGLES:
                inst.SetToggleDefault(key, bool(value))
            elif key in Config.DEFAULT_SLIDERS:
                inst.SetSliderDefault(key, int(value))
        except Exception as exc:
            _log("RememberValue %s failed: %s" % (key, exc))

    # ------------------------------------------------------------------
    # 音频：badapple.mp3
    # ------------------------------------------------------------------
    def GetAudioComp(self):
        if self.mAudioComp is not None:
            return self.mAudioComp
        try:
            self.mAudioComp = clientApi.GetEngineCompFactory().CreateCustomAudio(
                clientApi.GetLevelId())
        except Exception as exc:
            _log("CreateCustomAudio failed: %s" % exc)
        return self.mAudioComp

    def UpdateAudio(self, force=False):
        audio = self.GetAudioComp()
        if not audio:
            return
        volume = float(self.mSliders.get("volume", Config.DEFAULT_SLIDERS["volume"])) / 100.0
        wanted = bool(self.mToggles.get("bgm", Config.DEFAULT_TOGGLES["bgm"])) and volume > 0.0

        if not wanted:
            if self.mAudioPlaying:
                self.StopAudio()
            return
        if self.mAudioPlaying and not force:
            return
        if self.mAudioPlaying:
            self.StopAudio()
        self.StartAudio(audio, volume)

    def StartAudio(self, audio, volume):
        try:
            audio.DisableOriginMusic(True)
        except Exception as exc:
            _log("DisableOriginMusic failed: %s" % exc)

        for name in Config.AUDIO_NAMES:
            try:
                ret = audio.PlayCustomUIMusic(name, volume, 1.0, True)
            except Exception as exc:
                _log("PlayCustomUIMusic %s failed: %s" % (name, exc))
                ret = False
            # 返回值可能是 True 也可能是 None，只有明确 False 才算失败，
            # 否则会把同一首曲子播两遍。
            if ret is not False:
                self.mAudioPlaying = True
                self.mAudioName = name
                _log("play %s volume=%.2f" % (name, volume))
                return

        self.mAudioPlaying = False
        self.mAudioName = None
        _log("no playable sound definition: %s" % (Config.AUDIO_NAMES,))

    def StopAudio(self):
        audio = self.GetAudioComp()
        if audio:
            try:
                if self.mAudioName:
                    audio.StopCustomMusic(self.mAudioName, Config.AUDIO_FADE_OUT)
            except Exception as exc:
                _log("StopCustomMusic failed: %s" % exc)
            try:
                audio.DisableOriginMusic(False)
            except Exception:
                pass
        self.mAudioPlaying = False
        self.mAudioName = None

    # ------------------------------------------------------------------
    def Destroy(self):
        self.StopAudio()
        try:
            post = self.GetPostComp()
            if post:
                post.SetEnableByName(Config.PROCESS_NAME, False)
        except Exception:
            pass
        try:
            ClientSystem.Destroy(self)
        except Exception:
            pass
