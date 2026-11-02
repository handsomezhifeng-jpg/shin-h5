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
uniform 	vec3 _WorldSpaceCameraPos;
uniform 	vec4 hlslcc_mtx4x4unity_MatrixVP[4];
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
UNITY_BINDING(0) uniform UnityPerDraw {
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
in highp vec3 in_POSITION0;
in highp vec3 in_NORMAL0;
in highp vec4 in_TEXCOORD0;
in highp vec4 in_COLOR0;
out highp vec4 vs_INTERP0;
out highp vec4 vs_INTERP1;
out highp vec3 vs_INTERP2;
out highp vec3 vs_INTERP3;
out highp vec3 vs_INTERP4;
vec3 u_xlat0;
vec4 u_xlat1;
float u_xlat6;
void main()
{
    u_xlat0.xyz = in_POSITION0.yyy * hlslcc_mtx4x4unity_ObjectToWorld[1].xyz;
    u_xlat0.xyz = hlslcc_mtx4x4unity_ObjectToWorld[0].xyz * in_POSITION0.xxx + u_xlat0.xyz;
    u_xlat0.xyz = hlslcc_mtx4x4unity_ObjectToWorld[2].xyz * in_POSITION0.zzz + u_xlat0.xyz;
    u_xlat0.xyz = u_xlat0.xyz + hlslcc_mtx4x4unity_ObjectToWorld[3].xyz;
    u_xlat1 = u_xlat0.yyyy * hlslcc_mtx4x4unity_MatrixVP[1];
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[0] * u_xlat0.xxxx + u_xlat1;
    u_xlat1 = hlslcc_mtx4x4unity_MatrixVP[2] * u_xlat0.zzzz + u_xlat1;
    gl_Position = u_xlat1 + hlslcc_mtx4x4unity_MatrixVP[3];
    vs_INTERP0 = in_TEXCOORD0;
    vs_INTERP1 = in_COLOR0;
    vs_INTERP2.xyz = u_xlat0.xyz;
    vs_INTERP4.xyz = (-u_xlat0.xyz) + _WorldSpaceCameraPos.xyz;
    u_xlat0.xyz = in_NORMAL0.yyy * hlslcc_mtx4x4unity_ObjectToWorld[1].xyz;
    u_xlat0.xyz = hlslcc_mtx4x4unity_ObjectToWorld[0].xyz * in_NORMAL0.xxx + u_xlat0.xyz;
    u_xlat0.xyz = hlslcc_mtx4x4unity_ObjectToWorld[2].xyz * in_NORMAL0.zzz + u_xlat0.xyz;
    u_xlat6 = dot(u_xlat0.xyz, u_xlat0.xyz);
    u_xlat6 = max(u_xlat6, 1.17549435e-38);
    u_xlat6 = inversesqrt(u_xlat6);
    vs_INTERP3.xyz = vec3(u_xlat6) * u_xlat0.xyz;
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
uniform 	vec4 _TimeParameters;
uniform 	vec4 _ClipRect;
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
UNITY_BINDING(0) uniform UnityPerDraw {
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
UNITY_BINDING(1) uniform UnityPerMaterial {
#endif
	UNITY_UNIFORM vec4 _MainTex_TexelSize;
	UNITY_UNIFORM vec4 _MainTex_ST;
	UNITY_UNIFORM vec4 _MainColor;
	UNITY_UNIFORM vec2 _MainUV_Speed;
	UNITY_UNIFORM vec4 _Tex2_TexelSize;
	UNITY_UNIFORM vec4 _Tex2_ST;
	UNITY_UNIFORM vec2 _Tex2UV_Speed;
	UNITY_UNIFORM float _Tex2Open;
	UNITY_UNIFORM vec2 _PolarUV;
	UNITY_UNIFORM float _PolarSwitch;
	UNITY_UNIFORM vec4 _DissTex_TexelSize;
	UNITY_UNIFORM vec4 _DissTex_ST;
	UNITY_UNIFORM float _Diss_Value;
	UNITY_UNIFORM float _DissSoft_Value;
	UNITY_UNIFORM vec2 _DissUV_Speed;
	UNITY_UNIFORM vec2 _DisturbanceUV_Speed;
	UNITY_UNIFORM float _DisturbanceValue;
	UNITY_UNIFORM vec4 _DisturbanceTex_TexelSize;
	UNITY_UNIFORM vec4 _DisturbanceTex_ST;
	UNITY_UNIFORM vec4 _MaskMapping_TexelSize;
	UNITY_UNIFORM vec4 _MaskMapping_ST;
	UNITY_UNIFORM vec4 _DissEdgeColor;
	UNITY_UNIFORM float _DissEdgeOpen;
	UNITY_UNIFORM float _Brightness;
	UNITY_UNIFORM float _MaskMapping_Rotate;
	UNITY_UNIFORM float _MainTex_Rotate;
	UNITY_UNIFORM float _Tex2_Rotate;
	UNITY_UNIFORM float _DissTex_Rotate;
#if HLSLCC_ENABLE_UNIFORM_BUFFERS
};
#endif
UNITY_LOCATION(0) uniform mediump sampler2D _MainTex;
UNITY_LOCATION(1) uniform mediump sampler2D _Tex2;
UNITY_LOCATION(2) uniform mediump sampler2D _DissTex;
UNITY_LOCATION(3) uniform mediump sampler2D _DisturbanceTex;
UNITY_LOCATION(4) uniform mediump sampler2D _MaskMapping;
in highp vec4 vs_INTERP0;
in highp vec4 vs_INTERP1;
in highp vec3 vs_INTERP2;
layout(location = 0) out mediump vec4 SV_TARGET0;
vec4 u_xlat0;
vec4 u_xlat1;
mediump vec4 u_xlat16_1;
bvec4 u_xlatb1;
vec4 u_xlat2;
mediump vec4 u_xlat16_2;
vec4 u_xlat3;
bvec3 u_xlatb3;
vec3 u_xlat4;
vec3 u_xlat5;
vec3 u_xlat6;
vec3 u_xlat7;
mediump vec3 u_xlat16_8;
float u_xlat9;
bool u_xlatb9;
float u_xlat12;
vec2 u_xlat19;
bool u_xlatb19;
vec2 u_xlat21;
float u_xlat27;
mediump float u_xlat16_27;
bool u_xlatb27;
float u_xlat28;
bool u_xlatb28;
mediump float u_xlat16_30;
void main()
{
    u_xlat0.xyz = log2(abs(_DissEdgeColor.xyz));
    u_xlat0.xyz = u_xlat0.xyz * vec3(0.416666657, 0.416666657, 0.416666657);
    u_xlat0.xyz = exp2(u_xlat0.xyz);
    u_xlat0.xyz = u_xlat0.xyz * vec3(1.05499995, 1.05499995, 1.05499995) + vec3(-0.0549999997, -0.0549999997, -0.0549999997);
    u_xlatb1.xyz = greaterThanEqual(vec4(0.00313080009, 0.00313080009, 0.00313080009, 0.0), _DissEdgeColor.xyzx).xyz;
    u_xlat16_2.xyz = _DissEdgeColor.xyz * vec3(12.9232101, 12.9232101, 12.9232101);
    {
        vec4 hlslcc_movcTemp = u_xlat0;
        hlslcc_movcTemp.x = (u_xlatb1.x) ? u_xlat16_2.x : u_xlat0.x;
        hlslcc_movcTemp.y = (u_xlatb1.y) ? u_xlat16_2.y : u_xlat0.y;
        hlslcc_movcTemp.z = (u_xlatb1.z) ? u_xlat16_2.z : u_xlat0.z;
        u_xlat0 = hlslcc_movcTemp;
    }
    u_xlat1.xy = vs_INTERP0.xy + vec2(-0.5, -0.5);
    u_xlat27 = max(abs(u_xlat1.y), abs(u_xlat1.x));
    u_xlat27 = float(1.0) / u_xlat27;
    u_xlat19.x = min(abs(u_xlat1.y), abs(u_xlat1.x));
    u_xlat27 = u_xlat27 * u_xlat19.x;
    u_xlat19.x = u_xlat27 * u_xlat27;
    u_xlat28 = u_xlat19.x * 0.0208350997 + -0.0851330012;
    u_xlat28 = u_xlat19.x * u_xlat28 + 0.180141002;
    u_xlat28 = u_xlat19.x * u_xlat28 + -0.330299497;
    u_xlat19.x = u_xlat19.x * u_xlat28 + 0.999866009;
    u_xlat28 = u_xlat27 * u_xlat19.x;
    u_xlat28 = u_xlat28 * -2.0 + 1.57079637;
    u_xlatb3.x = abs(u_xlat1.y)<abs(u_xlat1.x);
    u_xlat28 = u_xlatb3.x ? u_xlat28 : float(0.0);
    u_xlat27 = u_xlat27 * u_xlat19.x + u_xlat28;
    u_xlatb19 = u_xlat1.y<(-u_xlat1.y);
    u_xlat19.x = u_xlatb19 ? -3.14159274 : float(0.0);
    u_xlat27 = u_xlat27 + u_xlat19.x;
    u_xlat19.x = min(u_xlat1.y, u_xlat1.x);
    u_xlatb19 = u_xlat19.x<(-u_xlat19.x);
    u_xlat28 = max(u_xlat1.y, u_xlat1.x);
    u_xlatb28 = u_xlat28>=(-u_xlat28);
    u_xlatb19 = u_xlatb28 && u_xlatb19;
    u_xlat27 = (u_xlatb19) ? (-u_xlat27) : u_xlat27;
    u_xlat27 = u_xlat27 * _PolarUV.y;
    u_xlat3.y = u_xlat27 * 0.159235656;
    u_xlatb27 = vec4(0.0, 0.0, 0.0, 0.0)!=vec4(_PolarSwitch);
    u_xlat19.x = dot(u_xlat1.xy, u_xlat1.xy);
    u_xlat19.x = sqrt(u_xlat19.x);
    u_xlat3.x = dot(u_xlat19.xx, _PolarUV.xx);
    u_xlat19.xy = (bool(u_xlatb27)) ? u_xlat3.xy : vs_INTERP0.xy;
    u_xlat3.xy = u_xlat19.xy + vec2(-0.5, -0.5);
    u_xlat21.xy = vec2(_Tex2_Rotate, _DissTex_Rotate) * vec2(0.0174532924, 0.0174532924);
    u_xlat4.x = sin(u_xlat21.y);
    u_xlat5.x = cos(u_xlat21.y);
    u_xlat6.x = sin(u_xlat21.x);
    u_xlat7.x = cos(u_xlat21.x);
    u_xlat5.yz = u_xlat4.xx;
    u_xlat4.xyz = u_xlat5.xyz * vec3(0.5, -0.5, 0.5) + vec3(0.5, 0.5, 0.5);
    u_xlat4.xyz = u_xlat4.xyz * vec3(2.0, 2.0, 2.0) + vec3(-1.0, -1.0, -1.0);
    u_xlat5.x = dot(u_xlat3.xy, u_xlat4.xz);
    u_xlat5.y = dot(u_xlat3.yx, u_xlat4.xy);
    u_xlat3.xy = u_xlat5.xy + vec2(0.5, 0.5);
    u_xlat3.xy = _TimeParameters.xx * vec2(_DissUV_Speed.x, _DissUV_Speed.y) + u_xlat3.xy;
    u_xlat3.xy = u_xlat3.xy * _DissTex_ST.xy + _DissTex_ST.zw;
    u_xlat16_27 = texture(_DissTex, u_xlat3.xy).x;
    u_xlat3.xy = vec2(_Diss_Value) * vec2(1.54999995, 1.54999995) + vec2(-0.519999981, -0.5);
    u_xlat3.xy = vec2(u_xlat16_27) + (-u_xlat3.xy);
    u_xlat27 = u_xlat16_27 + 1.0;
    u_xlat27 = _Diss_Value * -2.0 + u_xlat27;
    u_xlat3.xy = u_xlat3.xy * vec2(100.000099, 49.9999733);
    u_xlat3.xy = clamp(u_xlat3.xy, 0.0, 1.0);
    u_xlat21.xy = u_xlat3.xy * vec2(-2.0, -2.0) + vec2(3.0, 3.0);
    u_xlat3.xy = u_xlat3.xy * u_xlat3.xy;
    u_xlat12 = u_xlat3.y * u_xlat21.y;
    u_xlat3.x = u_xlat21.x * u_xlat3.x + (-u_xlat12);
    u_xlat2.xyz = u_xlat0.xyz * u_xlat3.xxx;
    u_xlat2.w = u_xlat3.x * _DissEdgeColor.w;
    u_xlat0.x = (-_DissSoft_Value) + 1.0;
    u_xlat9 = (-u_xlat0.x) + u_xlat27;
    u_xlat0.x = (-u_xlat0.x) + _DissSoft_Value;
    u_xlat0.x = float(1.0) / u_xlat0.x;
    u_xlat0.x = u_xlat0.x * u_xlat9;
    u_xlat0.x = clamp(u_xlat0.x, 0.0, 1.0);
    u_xlat9 = u_xlat0.x * -2.0 + 3.0;
    u_xlat0.x = u_xlat0.x * u_xlat0.x;
    u_xlat2 = vec4(u_xlat9) * u_xlat0.xxxx + u_xlat2;
    u_xlat0.x = u_xlat0.x * u_xlat9;
    u_xlatb9 = vec4(0.0, 0.0, 0.0, 0.0)!=vec4(_DissEdgeOpen);
    u_xlat0 = (bool(u_xlatb9)) ? u_xlat2 : u_xlat0.xxxx;
    u_xlat7.yz = u_xlat6.xx;
    u_xlat3.xyz = u_xlat7.xyz * vec3(0.5, -0.5, 0.5) + vec3(0.5, 0.5, 0.5);
    u_xlat3.xyz = u_xlat3.xyz * vec3(2.0, 2.0, 2.0) + vec3(-1.0, -1.0, -1.0);
    u_xlat4.xy = _TimeParameters.xx * _DisturbanceUV_Speed.xy + u_xlat19.xy;
    u_xlat4.xy = u_xlat4.xy * _DisturbanceTex_ST.xy + _DisturbanceTex_ST.zw;
    u_xlat16_30 = texture(_DisturbanceTex, u_xlat4.xy).x;
    u_xlat19.xy = vec2(u_xlat16_30) * vec2(vec2(_DisturbanceValue, _DisturbanceValue)) + u_xlat19.xy;
    u_xlat19.xy = u_xlat19.xy + vec2(-0.5, -0.5);
    u_xlat4.x = dot(u_xlat19.xy, u_xlat3.xz);
    u_xlat4.y = dot(u_xlat19.yx, u_xlat3.xy);
    u_xlat3.xy = u_xlat4.xy + vec2(0.5, 0.5);
    u_xlat3.xy = _TimeParameters.xx * _Tex2UV_Speed.xy + u_xlat3.xy;
    u_xlat3.xy = u_xlat3.xy * _Tex2_ST.xy + _Tex2_ST.zw;
    u_xlat16_2 = texture(_Tex2, u_xlat3.xy);
    u_xlat3.xy = vec2(_MainTex_Rotate, _MaskMapping_Rotate) * vec2(0.0174532924, 0.0174532924);
    u_xlat4.x = cos(u_xlat3.x);
    u_xlat3.x = sin(u_xlat3.x);
    u_xlat5.x = sin(u_xlat3.y);
    u_xlat6.x = cos(u_xlat3.y);
    u_xlat4.yz = u_xlat3.xx;
    u_xlat3.xyz = u_xlat4.xyz * vec3(0.5, -0.5, 0.5) + vec3(0.5, 0.5, 0.5);
    u_xlat3.xyz = u_xlat3.xyz * vec3(2.0, 2.0, 2.0) + vec3(-1.0, -1.0, -1.0);
    u_xlat4.x = dot(u_xlat19.xy, u_xlat3.xz);
    u_xlat4.y = dot(u_xlat19.yx, u_xlat3.xy);
    u_xlat19.xy = u_xlat4.xy + vec2(0.5, 0.5);
    u_xlat19.xy = _TimeParameters.xx * _MainUV_Speed.xy + u_xlat19.xy;
    u_xlat19.xy = u_xlat19.xy * _MainTex_ST.xy + _MainTex_ST.zw;
    u_xlat3 = texture(_MainTex, u_xlat19.xy);
    u_xlat2 = u_xlat16_2 * u_xlat3;
    u_xlatb19 = vec4(0.0, 0.0, 0.0, 0.0)!=vec4(_Tex2Open);
    u_xlat2 = (bool(u_xlatb19)) ? u_xlat2 : u_xlat3;
    u_xlat0 = u_xlat0 * u_xlat2;
    u_xlat6.yz = u_xlat5.xx;
    u_xlat3.xyz = u_xlat6.xyz * vec3(0.5, -0.5, 0.5) + vec3(0.5, 0.5, 0.5);
    u_xlat3.xyz = u_xlat3.xyz * vec3(2.0, 2.0, 2.0) + vec3(-1.0, -1.0, -1.0);
    u_xlat4.x = dot(u_xlat1.xy, u_xlat3.xz);
    u_xlat4.y = dot(u_xlat1.yx, u_xlat3.xy);
    u_xlat1.xy = u_xlat4.xy + vec2(0.5, 0.5);
    u_xlat1.xy = u_xlat1.xy * _MaskMapping_ST.xy + _MaskMapping_ST.zw;
    u_xlat16_1 = texture(_MaskMapping, u_xlat1.xy);
    u_xlat0 = u_xlat0 * u_xlat16_1;
    u_xlat1.xyz = log2(abs(_MainColor.xyz));
    u_xlat1.xyz = u_xlat1.xyz * vec3(0.416666657, 0.416666657, 0.416666657);
    u_xlat1.xyz = exp2(u_xlat1.xyz);
    u_xlat1.xyz = u_xlat1.xyz * vec3(1.05499995, 1.05499995, 1.05499995) + vec3(-0.0549999997, -0.0549999997, -0.0549999997);
    u_xlatb3.xyz = greaterThanEqual(vec4(0.00313080009, 0.00313080009, 0.00313080009, 0.0), _MainColor.xyzx).xyz;
    u_xlat16_8.xyz = _MainColor.xyz * vec3(12.9232101, 12.9232101, 12.9232101);
    {
        vec4 hlslcc_movcTemp = u_xlat1;
        hlslcc_movcTemp.x = (u_xlatb3.x) ? u_xlat16_8.x : u_xlat1.x;
        hlslcc_movcTemp.y = (u_xlatb3.y) ? u_xlat16_8.y : u_xlat1.y;
        hlslcc_movcTemp.z = (u_xlatb3.z) ? u_xlat16_8.z : u_xlat1.z;
        u_xlat1 = hlslcc_movcTemp;
    }
    u_xlat1.xyz = u_xlat1.xyz * vs_INTERP1.xyz;
    u_xlat1.w = vs_INTERP1.w * _MainColor.w;
    u_xlat0 = u_xlat0 * u_xlat1;
    u_xlat1.xy = vs_INTERP2.yy * hlslcc_mtx4x4unity_WorldToObject[1].xy;
    u_xlat1.xy = hlslcc_mtx4x4unity_WorldToObject[0].xy * vs_INTERP2.xx + u_xlat1.xy;
    u_xlat1.xy = hlslcc_mtx4x4unity_WorldToObject[2].xy * vs_INTERP2.zz + u_xlat1.xy;
    u_xlat1.xy = u_xlat1.xy + hlslcc_mtx4x4unity_WorldToObject[3].xy;
    u_xlatb1.zw = greaterThanEqual(u_xlat1.xxxy, _ClipRect.xxxy).zw;
    u_xlatb1.xy = greaterThanEqual(_ClipRect.zwzz, u_xlat1.xyxx).xy;
    u_xlat1.x = u_xlatb1.x ? float(1.0) : 0.0;
    u_xlat1.y = u_xlatb1.y ? float(1.0) : 0.0;
    u_xlat1.z = u_xlatb1.z ? float(1.0) : 0.0;
    u_xlat1.w = u_xlatb1.w ? float(1.0) : 0.0;
;
    u_xlat1.xy = u_xlat1.xy * u_xlat1.zw;
    u_xlat1.x = u_xlat1.y * u_xlat1.x;
    u_xlat1.w = u_xlat0.w * u_xlat1.x;
    u_xlat1.xyz = u_xlat0.xyz * vec3(vec3(_Brightness, _Brightness, _Brightness));
    SV_TARGET0 = u_xlat1;
    return;
}

#endif
