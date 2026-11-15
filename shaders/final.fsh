#version 120

#define FALLOFF_CURVE 0.0 // [-10.0 -9.0 -8.0 -7.0 -6.0 -5.0 -4.0 -3.0 -2.0 -1.0 0.0 1.0 2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0]
//#define x linearDepth
#define a actualMaxDistance
#define p FALLOFF_CURVE

#define TRUE 1
#define FALSE 0

#define OFF 0
#define ON 1
/////

#define THRESHOLD 0.0001 // [0.005 0.01 0.02 0.03 0.04 0.05 0.06 0.07 0.08 0.09 0.1]
#define RIM_OFFECT 0.0003 // [0.0003 0.0004 0.0005 0.001 0.002 0.003 0.004 0.005 0.01]
#define OUTLINE_COL 0.3 // [0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9]
//#define RAMP_VALUE 0.0001
#define SCREEN_VALUE 2000

#define OutlineDepthMultiplier 2.0 // [0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 1.5 1.6 1.7 1.8 1.9 2.0]
#define OutlineDepthBias 0.5 // [0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 1.5 1.6 1.7 1.8 1.9 2.0]
#define BAD_LINE_VALUE 0.5 // [0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0]
#define BAD_LINE OFF // [ON OFF]


uniform float far;
uniform sampler2D depthtex0;

uniform sampler2D colortex0;

uniform float viewHeight;
uniform float viewWidth;

vec2 texelStep = 1.0 / vec2(viewWidth, viewHeight);
const float lumaThreshold = 0.5;
const float mulReduce = 1.0 / 8.0;
const float minReduce = 1.0 / 128.;
const float maxSpan = 8.0;

uniform mat4 gbufferProjectionInverse;
varying vec2 texcoord;

// ===== Logo(视频最后 5 秒右下角显示) =====
uniform sampler2D colortex2;   // logo 纹理(由 shaders.properties 绑定 texture/logo.png)
#define LOGO_ASPECT 4.357      // 1024/235

/* DRAWBUFFERS:0 */

float screenSpaceToViewSpace(float depth, mat4 projInv) {
	depth = depth * 2.0 - 1.0;
	return projInv[3].z / (projInv[2].w * depth + projInv[3].w);
}

float screenDepth2LinearDepth(float depth)
{
   float viewDepth = screenSpaceToViewSpace(depth, gbufferProjectionInverse);
   float linearDepth = max(-viewDepth, 0.0);
   float actualMaxDistance = float(far);
   if(FALLOFF_CURVE != 0.0)
   {
      linearDepth = (exp(p * (linearDepth / a)) - 1.0) / (exp(p) - 1.0);
   } 
   else 
   {
      linearDepth /= actualMaxDistance;
   }
   linearDepth = 1.0 - linearDepth;
   return linearDepth;
}

float SobelDepth(float ldc, float ldl, float ldr, float ldu, float ldd)
{
   return abs(ldl - ldc) +
      abs(ldr - ldc) +
      abs(ldu - ldc) +
      abs(ldd - ldc);
}

float SobelSampleDepth(vec2 uv, vec3 offset)
{
   float pixelCenter = screenDepth2LinearDepth(texture(depthtex0, uv).r);
   float pixelLeft = screenDepth2LinearDepth(texture(depthtex0, uv - offset.xz).r);
   float pixelRight = screenDepth2LinearDepth(texture(depthtex0, uv + offset.xz).r);
   float pixelUp = screenDepth2LinearDepth(texture(depthtex0, uv + offset.zy).r);
   float pixelDown = screenDepth2LinearDepth(texture(depthtex0, uv - offset.zy).r);

   return SobelDepth(pixelCenter, pixelLeft, pixelRight, pixelUp, pixelDown);
}

// ===== 视频播放：帧图集纹理(每格 4 帧 RGBA)，按时间逐帧采样 =====
uniform sampler2D colortex1;      // 视频帧图集(由 shaders.properties 绑定 texture/video.png)
uniform float frameTimeCounter;   // 游戏运行时间(秒)，由 OptiFine/Iris 提供

#define VIDEO_DURATION 217.766667 // 视频总时长(秒)
#define VIDEO_FRAMES  3267        // 总帧数
#define VIDEO_CELLS   817        // 图集格子数(每格 4 帧)
#define VIDEO_GRID_X  29        // 图集列数
#define VIDEO_GRID_Y  29        // 图集行数
#define VIDEO_ATLAS_W 5568        // 图集像素宽
#define VIDEO_ATLAS_H 3132        // 图集像素高

int isInBlack(vec2 uv)
{
	// 循环播放：当前时间 -> 帧号
	float t = mod(frameTimeCounter, VIDEO_DURATION);
	int f = int(floor(t / VIDEO_DURATION * float(VIDEO_FRAMES)));

	// 帧 -> 格子(每格 4 帧)与通道(R/G/B/A)
	int c = f / 4;
	int ch = f - c * 4;
	int gx = c % VIDEO_GRID_X;
	int gy = c / VIDEO_GRID_X;

	vec2 cell = 1.0 / vec2(float(VIDEO_GRID_X), float(VIDEO_GRID_Y));
	vec2 px   = 1.0 / vec2(float(VIDEO_ATLAS_W), float(VIDEO_ATLAS_H));
	// 全屏 pass 的 uv.y=0 在屏幕底部；纹理 v=0 在图像顶部，故格子行号直接用 gy，格内用 1-uv.y 翻转
	float vRow = float(gy);
	vec2 atlasUV = vec2(float(gx), vRow) * cell + px * 0.5 + vec2(uv.x, 1.0 - uv.y) * (cell - px);

	vec4 vid = texture2D(colortex1, atlasUV);
	float luma = (ch == 0) ? vid.r : (ch == 1) ? vid.g : (ch == 2) ? vid.b : vid.w;
	if (luma < lumaThreshold) return TRUE;
	return FALSE;
}


void main() 
{
	vec4 sceneColor = texture(colortex0, texcoord);

   vec3 offset = vec3((1.0 / viewWidth), (1.0 / viewHeight), 0.0) * RIM_OFFECT * SCREEN_VALUE;

   float sobelDepth = SobelSampleDepth(texcoord, offset);

   sobelDepth = pow(clamp(sobelDepth, 0.0, 1.0) * OutlineDepthMultiplier, OutlineDepthBias);

   vec4 outlineCol = vec4(OUTLINE_COL,OUTLINE_COL,OUTLINE_COL,1);

   vec4 color = mix(sceneColor, outlineCol, sobelDepth);
   if(BAD_LINE == OFF)
   {
      if(isInBlack(texcoord) == TRUE)
      {
         color.x = 1 - color.x;
         color.y = 1 - color.y;
         color.z = 1 - color.z;
      }

      // ===== 视频最后 5 秒：屏幕右下角显示 logo =====
      if (mod(frameTimeCounter, VIDEO_DURATION) > VIDEO_DURATION - 5.0)
      {
         float margin = 0.035;
         float logoW = 0.30;
         float logoH = logoW * (viewWidth / viewHeight) / LOGO_ASPECT;
         vec2 lo = vec2(1.0 - margin - logoW, margin);
         vec2 hi = vec2(1.0 - margin, margin + logoH);
         if (texcoord.x > lo.x && texcoord.x < hi.x && texcoord.y > lo.y && texcoord.y < hi.y)
         {
            vec2 lv = (texcoord - lo) / (hi - lo);
            vec2 luv = vec2(lv.x, 1.0 - lv.y);
            float la = texture2D(colortex2, luv).w;

            // 深色描边，确保在任何背景上都清晰可见
            vec2 tp = vec2(5.0 / 1024.0, 5.0 / 235.0);
            float halo = 0.0;
            halo = max(halo, texture2D(colortex2, luv + vec2( tp.x, 0.0)).w);
            halo = max(halo, texture2D(colortex2, luv - vec2( tp.x, 0.0)).w);
            halo = max(halo, texture2D(colortex2, luv + vec2(0.0,  tp.y)).w);
            halo = max(halo, texture2D(colortex2, luv - vec2(0.0,  tp.y)).w);
            halo = max(halo, texture2D(colortex2, luv + vec2( tp.x,  tp.y)).w);
            halo = max(halo, texture2D(colortex2, luv + vec2(-tp.x,  tp.y)).w);
            halo = max(halo, texture2D(colortex2, luv + vec2( tp.x, -tp.y)).w);
            halo = max(halo, texture2D(colortex2, luv + vec2(-tp.x, -tp.y)).w);

            color.rgb = mix(color.rgb, vec3(0.0), halo * 0.9);
            color.rgb = mix(color.rgb, vec3(1.0), la);
         }
      }
   }
   if(BAD_LINE == ON)
   {
      if(texcoord.x < BAD_LINE_VALUE)
      {
         color.x = 1 - color.x;
         color.y = 1 - color.y;
         color.z = 1 - color.z;
      } 
   }

   gl_FragData[0] = color;
}

//LZX vscode 2025/03/24

//||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
//||||--==||||||||||||||||------==||||||||||----------==||||
//||||--==||||||||||||||------------==||||||------------==||
//||||--==|||||||||||||---==||||----==||||||--==||||----==||
//||||--==|||||||||||||---==||||||||||||||||--------------||
//||||--==|||||||||||||---==||||----==||||||----------==||||
//||||------------==||||------------==||||||--==||||||||||||
//||||------------==||||||------==||||||||||--==||||||||||||
//||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
//|||||||||||||||||LZX.Celluloid.Project||||||||||||||||||||