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
uniform 	vec4 _Time;
uniform 	vec4 hlslcc_mtx4x4unity_ObjectToWorld[4];
uniform 	vec4 hlslcc_mtx4x4unity_MatrixVP[4];
uniform 	vec4 _MainTex_ST;
uniform 	vec4 _MaskTex_ST;
uniform 	vec4 _DistortionTex_ST;
uniform 	vec4 _DistortionSpeed;
uniform 	vec4 _DistortionScale;
uniform 	vec4 _MaskSpeed;
uniform 	vec4 _MaskScale;
in highp vec4 in_POSITION0;
in highp vec2 in_TEXCOORD0;
in highp vec4 in_COLOR0;
out highp vec2 vs_TEXCOORD0;
out highp vec2 vs_TEXCOORD1;
out highp vec4 vs_COLOR0;
out highp vec2 vs_TEXCOORD2;
vec4 u_xlat0;
vec4 u_xlat1;
void main()
{
    u_xlat0.xy = _Time.yy * _MaskSpeed.xy;
    u_xlat0.xy = in_TEXCOORD0.xy * _MaskScale.xy + u_xlat0.xy;
    vs_TEXCOORD1.xy = u_xlat0.xy * _MaskTex_ST.xy + _MaskTex_ST.zw;
    vs_TEXCOORD0.xy = in_TEXCOORD0.xy * _MainTex_ST.xy + _MainTex_ST.zw;
    u_xlat0 = in_POSITION0.yyyy * hlslcc_mtx4x4unity_ObjectToWorld[1];
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[0] * in_POSITION0.xxxx + u_xlat0;
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[2] * in_POSITION0.zzzz + u_xlat0;
    u_xlat0 = u_xlat0 + hlslcc_mtx4x4unity_ObjectToWorld[3];
    u_xlat1 = u_xlat0.yyyy * hlslcc_mtx4x4unity_MatrixVP[1];
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[0] * u_xlat0.xxxx + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[2] * u_xlat0.zzzz + u_xlat1;
    gl_Position = hlslcc_mtx4x4unity_MatrixVP[3] * u_xlat0.wwww + u_xlat1;
    vs_COLOR0 = in_COLOR0;
    u_xlat0.xy = _Time.yy * _DistortionSpeed.xy;
    u_xlat0.xy = in_TEXCOORD0.xy * _DistortionScale.xy + u_xlat0.xy;
    vs_TEXCOORD2.xy = u_xlat0.xy * _DistortionTex_ST.xy + _DistortionTex_ST.zw;
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
uniform 	float _DistortionAmount;
UNITY_LOCATION(0) uniform mediump sampler2D _DistortionTex;
UNITY_LOCATION(1) uniform mediump sampler2D _MainTex;
UNITY_LOCATION(2) uniform mediump sampler2D _MaskTex;
in highp vec2 vs_TEXCOORD0;
in highp vec2 vs_TEXCOORD1;
in highp vec4 vs_COLOR0;
in highp vec2 vs_TEXCOORD2;
layout(location = 0) out mediump vec4 SV_Target0;
vec2 u_xlat0;
mediump vec3 u_xlat16_0;
mediump vec4 u_xlat16_1;
vec4 u_xlat2;
mediump float u_xlat16_3;
mediump float u_xlat16_4;
void main()
{
    u_xlat16_0.xyz = texture(_DistortionTex, vs_TEXCOORD2.xy).xyz;
    u_xlat0.xy = u_xlat16_0.xy * vec2(2.0, 2.0) + vec2(-1.0, -1.0);
    u_xlat0.xy = u_xlat0.xy * vec2(_DistortionAmount) + vs_TEXCOORD0.xy;
    u_xlat16_1 = texture(_MainTex, u_xlat0.xy);
    u_xlat2.xyz = u_xlat16_1.xyz;
    u_xlat2.w = vs_COLOR0.w;
    u_xlat2 = u_xlat2 * vs_COLOR0;
    u_xlat0.x = u_xlat16_1.w * u_xlat2.w;
    u_xlat16_4 = texture(_MaskTex, vs_TEXCOORD1.xy).w;
    u_xlat16_3 = u_xlat16_4 * u_xlat0.x;
    u_xlat2.w = u_xlat16_0.z * u_xlat16_3;
    SV_Target0 = u_xlat2;
    return;
}

#endif
