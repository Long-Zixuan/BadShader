# -*- coding: utf-8 -*-
"""
LS Bad Shader · 配置存档

把设置界面上的取值存进网易的全局 key/value 存储，退出游戏 / 换存档后保留。
用的是 ConfigClient 组件（isGlobal=True 表示所有存档共用一份）：

    comp = clientApi.GetEngineCompFactory().CreateConfigClient(levelId)
    comp.GetConfigData(key, True)      # 读，返回 dict
    comp.SetConfigData(key, data, True)  # 写

存档结构：
    {
        "version": 1,
        "sliders": {"rim_offect": 2, "outline_col": 33, ...},
        "toggles": {"paper_world": True, "bgm": True, ...}
    }
"""

try:
    import mod.client.extraClientApi as clientApi
except ImportError:  # 很老的 SDK 目录结构
    import client.extraClientApi as clientApi

STORE_KEY = "ls_bad_shader_settings_v1"
STORE_VERSION = 1


def _log(message):
    print("[LSBadShader] " + str(message))


class LSBadShaderStore(object):

    def __init__(self):
        self.mComp = None
        self.mLastError = None

    def GetComp(self):
        if self.mComp is not None:
            return self.mComp
        try:
            self.mComp = clientApi.GetEngineCompFactory().CreateConfigClient(
                clientApi.GetLevelId())
        except Exception as exc:
            self.mLastError = str(exc)
            _log("CreateConfigClient failed: %s" % exc)
        return self.mComp

    def Load(self):
        """读存档；没有或损坏时返回空 dict。"""
        comp = self.GetComp()
        if comp is None:
            return {}
        try:
            data = comp.GetConfigData(STORE_KEY, True)
        except Exception as exc:
            _log("GetConfigData failed: %s" % exc)
            return {}
        if isinstance(data, dict):
            return data
        return {}

    def Save(self, sliders, toggles):
        """写存档；成功返回 True。"""
        comp = self.GetComp()
        if comp is None:
            return False
        payload = {
            "version": STORE_VERSION,
            "sliders": dict(sliders),
            "toggles": dict(toggles),
        }
        try:
            ok = comp.SetConfigData(STORE_KEY, payload, True)
        except Exception as exc:
            _log("SetConfigData failed: %s" % exc)
            return False
        if ok is False:
            _log("SetConfigData returned False")
        return ok is not False
