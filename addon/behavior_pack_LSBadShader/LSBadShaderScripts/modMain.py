# -*- coding: utf-8 -*-
"""
LS Bad Shader · ModSDK 入口（纯客户端光影，服务端不需要任何逻辑）

写法与网易官方「入门脚本模板」一致：
    * 顶层只 import Mod 与 clientApi，不 import 自己的系统模块
      （引擎加载 modMain 时会检查入口类，顶层再牵进别的模块容易出问题）；
    * @Mod.Binding 装饰唯一的入口类，InitClient 里用字符串路径注册客户端系统。
"""

print("[LSBadShader] modMain.py executing")

try:
    from mod.common.mod import Mod
except ImportError:  # 很老的 SDK 目录结构
    from common.mod import Mod

try:
    import mod.client.extraClientApi as clientApi
except ImportError:  # 很老的 SDK 目录结构
    import client.extraClientApi as clientApi

MOD_NAME = "LSBadShader"
MOD_VERSION = "1.0.0"
SCRIPT_ROOT = "LSBadShaderScripts"

print("[LSBadShader] modMain.py imported")


@Mod.Binding(name=MOD_NAME, version=MOD_VERSION)
class LSBadShaderMod(object):

    @Mod.InitServer()
    def init_server(self):
        # 这个光影完全是客户端效果，服务端什么都不做。
        pass

    @Mod.InitClient()
    def init_client(self):
        clientApi.RegisterSystem(
            MOD_NAME,
            "LSBadShaderClientSystem",
            SCRIPT_ROOT + ".LSBadShaderClientSystem.LSBadShaderClientSystem"
        )
        print("[LSBadShader] client system registered")

    @Mod.DestroyServer()
    def destroy_server(self):
        pass

    @Mod.DestroyClient()
    def destroy_client(self):
        pass
