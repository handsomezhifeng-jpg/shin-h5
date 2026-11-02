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
uniform 	vec4 _ScreenParams;
uniform 	vec4 hlslcc_mtx4x4unity_ObjectToWorld[4];
uniform 	vec4 hlslcc_mtx4x4glstate_matrix_projection[4];
uniform 	vec4 hlslcc_mtx4x4unity_MatrixVP[4];
uniform 	vec4 hlslcc_mtx4x4_SoftMask_WorldToMask[4];
uniform 	vec4 _ClipRect;
uniform 	float _UIMaskSoftnessX;
uniform 	float _UIMaskSoftnessY;
in highp vec4 in_POSITION0;
in highp vec2 in_TEXCOORD0;
in highp vec4 in_COLOR0;
out highp vec2 vs_TEXCOORD0;
out highp vec4 vs_COLOR0;
out highp vec4 vs_TEXCOORD1;
out mediump vec4 vs_TEXCOORD2;
vec4 u_xlat0;
vec4 u_xlat1;
void main()
{
    u_xlat0 = in_POSITION0.yyyy * hlslcc_mtx4x4unity_ObjectToWorld[1];
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[0] * in_POSITION0.xxxx + u_xlat0;
    u_xlat0 = hlslcc_mtx4x4unity_ObjectToWorld[2] * in_POSITION0.zzzz + u_xlat0;
    u_xlat0 = u_xlat0 + hlslcc_mtx4x4unity_ObjectToWorld[3];
    u_xlat1 = u_xlat0.yyyy * hlslcc_mtx4x4unity_MatrixVP[1];
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[0] * u_xlat0.xxxx + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[2] * u_xlat0.zzzz + u_xlat1;
    u_xlat0 = hlslcc_mtx4x4unity_MatrixVP[3] * u_xlat0.wwww + u_xlat1;
    gl_Position = u_xlat0;
    vs_TEXCOORD0.xy = in_TEXCOORD0.xy;
    vs_COLOR0 = in_COLOR0;
    u_xlat1 = in_POSITION0.yyyy * hlslcc_mtx4x4_SoftMask_WorldToMask[1];
    u_xlat1 = hlslcc_mtx4x4_SoftMask_WorldToMask[0] * in_POSITION0.xxxx + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4_SoftMask_WorldToMask[2] * in_POSITION0.zzzz + u_xlat1;
    vs_TEXCOORD1 = hlslcc_mtx4x4_SoftMask_WorldToMask[3] * in_POSITION0.wwww + u_xlat1;
    u_xlat0.xy = _ScreenParams.yy * hlslcc_mtx4x4glstate_matrix_projection[1].xy;
    u_xlat0.xy = hlslcc_mtx4x4glstate_matrix_projection[0].xy * _ScreenParams.xx + u_xlat0.xy;
    u_xlat0.xy = u_xlat0.ww / abs(u_xlat0.xy);
    u_xlat0.xy = vec2(_UIMaskSoftnessX, _UIMaskSoftnessY) * vec2(0.25, 0.25) + abs(u_xlat0.xy);
    u_xlat0.zw = vec2(0.25, 0.25) / u_xlat0.xy;
    u_xlat1 = max(_ClipRect, vec4(-2e+10, -2e+10, -2e+10, -2e+10));
    u_xlat1 = min(u_xlat1, vec4(2e+10, 2e+10, 2e+10, 2e+10));
    u_xlat1.xy = in_POSITION0.xy * vec2(2.0, 2.0) + (-u_xlat1.xy);
    u_xlat0.xy = (-u_xlat1.zw) + u_xlat1.xy;
    vs_TEXCOORD2 = u_xlat0;
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
uniform 	vec4 _Time;
uniform 	vec4 _SoftMask_Rect;
uniform 	vec4 _SoftMask_UVRect;
uniform 	vec4 _SoftMask_ChannelWeights;
uniform 	int _SoftMask_InvertMask;
uniform 	int _SoftMask_InvertOutsides;
uniform 	vec4 _MainTex_ST;
uniform 	float _Brightness;
uniform 	float _MainPannerX;
uniform 	float _MainPannerY;
uniform 	vec4 _MainColor;
uniform 	float _SecPannerX;
uniform 	float _SecPannerY;
uniform 	float _Contrast;
uniform 	vec4 _MaskTex_ST;
UNITY_LOCATION(0) uniform mediump sampler2D _SoftMask;
UNITY_LOCATION(1) uniform mediump sampler2D _MainTex;
UNITY_LOCATION(2) uniform mediump sampler2D _MaskTex;
in highp vec2 vs_TEXCOORD0;
in highp vec4 vs_COLOR0;
in highp vec4 vs_TEXCOORD1;
layout(location = 0) out highp vec4 SV_Target0;
vec4 u_xlat0;
mediump vec4 u_xlat16_0;
bool u_xlatb0;
vec3 u_xlat1;
mediump float u_xlat16_1;
bvec2 u_xlatb1;
vec2 u_xlat2;
vec2 u_xlat4;
bvec2 u_xlatb4;
void main()
{
    u_xlat0.xy = vs_TEXCOORD1.xy + (-_SoftMask_Rect.xy);
    u_xlat4.xy = (-_SoftMask_Rect.xy) + _SoftMask_Rect.zw;
    u_xlat0.xy = u_xlat0.xy / u_xlat4.xy;
    u_xlatb4.xy = notEqual(u_xlat4.xyxy, vec4(0.0, 0.0, 0.0, 0.0)).xy;
    u_xlat0.x = u_xlatb4.x ? u_xlat0.x : 0.0;
    u_xlat0.y = u_xlatb4.y ? u_xlat0.y : 0.0;
;
    u_xlat4.xy = (-_SoftMask_UVRect.xy) + _SoftMask_UVRect.zw;
    u_xlat0.xy = u_xlat0.xy * u_xlat4.xy + _SoftMask_UVRect.xy;
    u_xlat16_0 = texture(_SoftMask, u_xlat0.xy);
    u_xlat0 = u_xlat16_0 * _SoftMask_ChannelWeights;
    u_xlat0.x = dot(u_xlat0, vec4(1.0, 1.0, 1.0, 1.0));
    u_xlat2.x = (-u_xlat0.x) + 1.0;
    u_xlat0.x = (_SoftMask_InvertMask != 0) ? u_xlat2.x : u_xlat0.x;
    u_xlat2.xy = (int(_SoftMask_InvertOutsides) != 0) ? vec2(1.0, -1.0) : vec2(0.0, -0.0);
    u_xlat0.x = u_xlat2.y + u_xlat0.x;
    u_xlatb4.xy = greaterThanEqual(vs_TEXCOORD1.xyxy, _SoftMask_Rect.xyxy).xy;
    u_xlat4.x = u_xlatb4.x ? float(1.0) : 0.0;
    u_xlat4.y = u_xlatb4.y ? float(1.0) : 0.0;
;
    u_xlatb1.xy = greaterThanEqual(_SoftMask_Rect.zwzz, vs_TEXCOORD1.xyxx).xy;
    u_xlat1.x = u_xlatb1.x ? float(1.0) : 0.0;
    u_xlat1.y = u_xlatb1.y ? float(1.0) : 0.0;
;
    u_xlat4.xy = u_xlat4.xy * u_xlat1.xy;
    u_xlat4.x = u_xlat4.y * u_xlat4.x;
    u_xlat0.x = u_xlat4.x * u_xlat0.x + u_xlat2.x;
    u_xlat0.x = u_xlat0.x + -0.00100000005;
    u_xlatb0 = u_xlat0.x<0.0;
    if(u_xlatb0){discard;}
    u_xlat0.xy = vec2(_MainPannerX, _MainPannerY) * _Time.yy + vs_TEXCOORD0.xy;
    u_xlat0.xy = u_xlat0.xy * _MainTex_ST.xy + _MainTex_ST.zw;
    u_xlat16_0 = texture(_MainTex, u_xlat0.xy);
    u_xlat0.xyz = log2(u_xlat16_0.xyz);
    u_xlat0.w = u_xlat16_0.w * _MainColor.w;
    u_xlat0.xyz = u_xlat0.xyz * vec3(vec3(_Contrast, _Contrast, _Contrast));
    u_xlat0.xyz = exp2(u_xlat0.xyz);
    u_xlat1.xyz = vec3(_Brightness) * _MainColor.xyz;
    u_xlat0.xyz = u_xlat0.xyz * u_xlat1.xyz;
    u_xlat1.xy = vec2(_SecPannerX, _SecPannerY) * _Time.yy + vs_TEXCOORD0.xy;
    u_xlat1.xy = u_xlat1.xy * _MaskTex_ST.xy + _MaskTex_ST.zw;
    u_xlat16_1 = texture(_MaskTex, u_xlat1.xy).x;
    u_xlat0 = u_xlat0 * vec4(u_xlat16_1);
    u_xlat0 = u_xlat0 * vs_COLOR0;
    SV_Target0.xyz = u_xlat0.www * u_xlat0.xyz;
    SV_Target0.w = 0.0;
    return;
}

#endif
