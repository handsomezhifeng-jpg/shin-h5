#ifdef VERTEX
#version 300 es

#define HLSLCC_ENABLE_UNIFORM_BUFFERS 1
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
#define UNITY_UNIFORM
#else
#define UNITY_UNIFORM uniform
#endif
#define UNITY_SUPPORTS_UNIFORM_LOCATION 1
#if UNITY_SUPPORTS_UNIFORM_LOCATION
#define UNITY_LOCATION(x) layout(location = x)
#define UNITY_BINDING(x) layout(binding = x, std140)
#else
#define UNITY_LOCATION(x)
#define UNITY_BINDING(x) layout(std140)
#endif
uniform 	vec4 _ProjectionParams;
uniform 	vec4 _ScreenParams;
uniform 	vec4 hlslcc_mtx4x4unity_MatrixVP[4];
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
UNITY_BINDING(1) uniform UnityPerDraw {
#endif
	UNITY_UNIFORM vec4 hlslcc_mtx4x4unity_ObjectToWorld[4];
	UNITY_UNIFORM vec4 hlslcc_mtx4x4unity_WorldToObject[4];
	UNITY_UNIFORM vec4 unity_LODFade;
	UNITY_UNIFORM mediump vec4 unity_WorldTransformParams;
	UNITY_UNIFORM vec4 unity_RenderingLayer;
	UNITY_UNIFORM vec4 unity_LightmapST;
	UNITY_UNIFORM vec4 unity_DynamicLightmapST;
	UNITY_UNIFORM mediump vec4 unity_SHAr;
	UNITY_UNIFORM mediump vec4 unity_SHAg;
	UNITY_UNIFORM mediump vec4 unity_SHAb;
	UNITY_UNIFORM mediump vec4 unity_SHBr;
	UNITY_UNIFORM mediump vec4 unity_SHBg;
	UNITY_UNIFORM mediump vec4 unity_SHBb;
	UNITY_UNIFORM mediump vec4 unity_SHC;
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
};
#endif
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
UNITY_BINDING(0) uniform UnityPerMaterial {
#endif
	UNITY_UNIFORM mediump vec4 _MainColor;
	UNITY_UNIFORM mediump vec4 _MainTex_ST;
	UNITY_UNIFORM mediump vec4 _RendererColor;
	UNITY_UNIFORM mediump vec4 _Color;
	UNITY_UNIFORM mediump vec4 _Flip;
	UNITY_UNIFORM mediump vec4 _AmbientLightTintColor;
	UNITY_UNIFORM mediump float _AmbientLightInfluence;
	UNITY_UNIFORM mediump float _Brightness;
	UNITY_UNIFORM mediump float _Desaturate;
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
};
#endif
in highp vec3 in_POSITION0;
in highp vec4 in_COLOR0;
in highp vec2 in_TEXCOORD0;
out mediump vec4 vs_COLOR0;
out highp vec2 vs_TEXCOORD0;
out mediump vec2 vs_TEXCOORD1;
out highp vec3 vs_TEXCOORD2;
vec4 u_xlat0;
vec4 u_xlat1;
vec2 u_xlat4;
void main()
{
    u_xlat0.xy = in_POSITION0.xy * _Flip.xy;
    u_xlat1 = u_xlat0.yyyy * hlslcc_mtx4x4unity_ObjectToWorld[1];
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[0] * u_xlat0.xxxx + u_xlat1;
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[2] * in_POSITION0.zzzz + u_xlat0;
    u_xlat0 = u_xlat0 + hlslcc_mtx4x4unity_ObjectToWorld[3];
    u_xlat1 = u_xlat0.yyyy * hlslcc_mtx4x4unity_MatrixVP[1];
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[0] * u_xlat0.xxxx + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[2] * u_xlat0.zzzz + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[3] * u_xlat0.wwww + u_xlat1;
    vs_TEXCOORD2.xyz = u_xlat0.xyz;
    u_xlat0.xy = u_xlat1.xy / u_xlat1.ww;
    u_xlat4.xy = _ScreenParams.xy * vec2(0.5, 0.5);
    u_xlat0.xy = u_xlat4.xy * u_xlat0.xy;
    u_xlat0.xy = roundEven(u_xlat0.xy);
    u_xlat0.xy = u_xlat0.xy / u_xlat4.xy;
    u_xlat1.xy = u_xlat1.ww * u_xlat0.xy;
    u_xlat0.xyz = u_xlat1.xyw / u_xlat1.www;
    gl_Position = u_xlat1;
    u_xlat1 = in_COLOR0 * _Color;
    u_xlat1 = u_xlat1 * _RendererColor;
    vs_COLOR0 = u_xlat1;
    vs_TEXCOORD0.xy = in_TEXCOORD0.xy * _MainTex_ST.xy + _MainTex_ST.zw;
    u_xlat0.y = u_xlat0.y * _ProjectionParams.x;
    u_xlat0.xzw = u_xlat0.xzy * vec3(0.5, 0.5, 0.5);
    u_xlat0.xy = u_xlat0.zz + u_xlat0.xw;
    vs_TEXCOORD1.xy = u_xlat0.xy;
    return;
}

#endif
#ifdef FRAGMENT
#version 300 es

precision highp float;
precision highp int;
#define HLSLCC_ENABLE_UNIFORM_BUFFERS 1
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
#define UNITY_UNIFORM
#else
#define UNITY_UNIFORM uniform
#endif
#define UNITY_SUPPORTS_UNIFORM_LOCATION 1
#if UNITY_SUPPORTS_UNIFORM_LOCATION
#define UNITY_LOCATION(x) layout(location = x)
#define UNITY_BINDING(x) layout(binding = x, std140)
#else
#define UNITY_LOCATION(x)
#define UNITY_BINDING(x) layout(std140)
#endif
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
UNITY_BINDING(0) uniform UnityPerMaterial {
#endif
	UNITY_UNIFORM mediump vec4 _MainColor;
	UNITY_UNIFORM mediump vec4 _MainTex_ST;
	UNITY_UNIFORM mediump vec4 _RendererColor;
	UNITY_UNIFORM mediump vec4 _Color;
	UNITY_UNIFORM mediump vec4 _Flip;
	UNITY_UNIFORM mediump vec4 _AmbientLightTintColor;
	UNITY_UNIFORM mediump float _AmbientLightInfluence;
	UNITY_UNIFORM mediump float _Brightness;
	UNITY_UNIFORM mediump float _Desaturate;
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
};
#endif
UNITY_LOCATION(0) uniform mediump sampler2D _MainTex;
in mediump vec4 vs_COLOR0;
in highp vec2 vs_TEXCOORD0;
layout(location = 0) out mediump vec4 SV_Target0;
mediump vec3 u_xlat16_0;
mediump vec4 u_xlat16_1;
mediump vec3 u_xlat16_2;
mediump float u_xlat16_9;
void main()
{
    u_xlat16_0.xyz = _MainColor.xyz * vec3(vec3(_Brightness, _Brightness, _Brightness));
    u_xlat16_0.xyz = u_xlat16_0.xyz * vs_COLOR0.xyz;
    u_xlat16_1 = texture(_MainTex, vs_TEXCOORD0.xy);
    u_xlat16_2.xyz = u_xlat16_0.xyz * u_xlat16_1.xyz;
    u_xlat16_9 = dot(u_xlat16_2.xyz, vec3(0.298999995, 0.587000012, 0.114));
    u_xlat16_0.xyz = (-u_xlat16_1.xyz) * u_xlat16_0.xyz + vec3(u_xlat16_9);
    SV_Target0.xyz = vec3(vec3(_Desaturate, _Desaturate, _Desaturate)) * u_xlat16_0.xyz + u_xlat16_2.xyz;
    u_xlat16_0.x = vs_COLOR0.w * _MainColor.w;
    SV_Target0.w = u_xlat16_0.x * u_xlat16_1.w;
    return;
}

#endif
