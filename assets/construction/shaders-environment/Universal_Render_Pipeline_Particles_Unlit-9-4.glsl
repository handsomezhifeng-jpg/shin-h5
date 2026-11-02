#ifdef VERTEX
#version 310 es

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
uniform 	int unity_BaseInstanceID;
uniform 	vec4 unity_ParticleUVShiftData;
uniform 	mediump float unity_ParticleUseMeshColors;
 struct unity_ParticleInstanceData_type {
	uint[14] value;
};

layout(std430, binding = 0) readonly buffer unity_ParticleInstanceData {
	unity_ParticleInstanceData_type unity_ParticleInstanceData_buf[];
};
in highp vec4 in_POSITION0;
in mediump vec4 in_COLOR0;
in highp vec2 in_TEXCOORD0;
in highp vec3 in_NORMAL0;
layout(location = 0) out highp vec2 vs_TEXCOORD0;
layout(location = 1) out mediump vec4 vs_COLOR0;
layout(location = 2) out highp vec4 vs_TEXCOORD1;
layout(location = 3) out mediump vec3 vs_TEXCOORD2;
layout(location = 4) out mediump vec3 vs_TEXCOORD3;
layout(location = 5) out mediump vec3 vs_TEXCOORD8;
layout(location = 6) flat out highp uint vs_SV_InstanceID0;
vec4 u_xlat0;
uint u_xlatu0;
vec2 u_xlat1;
mediump vec4 u_xlat16_1;
int u_xlati1;
uvec3 u_xlatu1;
vec4 u_xlat2;
vec4 u_xlat3;
vec4 u_xlat4;
vec4 u_xlat5;
vec3 u_xlat6;
vec4 u_xlat7;
float u_xlat8;
vec3 u_xlat9;
bool u_xlatb16;
float u_xlat24;
void main()
{
    u_xlat0.xyz = in_POSITION0.xyz;
    u_xlat0.w = 1.0;
    u_xlati1 = gl_InstanceID + unity_BaseInstanceID;
    u_xlat2.xyz = vec3(uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(0 >> 2) + 2]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(0 >> 2) + 0]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(0 >> 2) + 1]));
    u_xlat3.x = u_xlat2.z;
    u_xlat4.xyz = vec3(uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(12 >> 2) + 1]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(12 >> 2) + 0]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(12 >> 2) + 2]));
    u_xlat3.y = u_xlat4.x;
    u_xlat9.xyz = vec3(uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(24 >> 2) + 0]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(24 >> 2) + 1]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(24 >> 2) + 2]));
    u_xlat3.z = u_xlat9.y;
    u_xlat5 = vec4(uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(36 >> 2) + 0]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(36 >> 2) + 1]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(36 >> 2) + 2]), uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(36 >> 2) + 3]));
    u_xlat1.x = uintBitsToFloat(unity_ParticleInstanceData_buf[u_xlati1].value[(52 >> 2) + 0]);
    u_xlat1.x = floor(u_xlat1.x);
    u_xlat3.w = u_xlat5.y;
    u_xlat6.y = dot(u_xlat3, u_xlat0);
    u_xlat3.y = dot(u_xlat3.xyz, in_NORMAL0.xyz);
    u_xlat7 = u_xlat6.yyyy * hlslcc_mtx4x4unity_MatrixVP[1];
    u_xlat4.x = u_xlat2.y;
    u_xlat2.y = u_xlat4.z;
    u_xlat4.z = u_xlat9.x;
    u_xlat2.z = u_xlat9.z;
    u_xlat4.w = u_xlat5.x;
    u_xlat6.x = dot(u_xlat4, u_xlat0);
    u_xlat3.x = dot(u_xlat4.xyz, in_NORMAL0.xyz);
    u_xlat4 = hlslcc_mtx4x4unity_MatrixVP[0] * u_xlat6.xxxx + u_xlat7;
    u_xlat2.w = u_xlat5.z;
    u_xlat6.z = dot(u_xlat2, u_xlat0);
    u_xlat3.z = dot(u_xlat2.xyz, in_NORMAL0.xyz);
    u_xlat0 = hlslcc_mtx4x4unity_MatrixVP[2] * u_xlat6.zzzz + u_xlat4;
    gl_Position = u_xlat0 + hlslcc_mtx4x4unity_MatrixVP[3];
    u_xlat0.x = u_xlat1.x / unity_ParticleUVShiftData.y;
    u_xlat0.x = floor(u_xlat0.x);
    u_xlat8 = (-u_xlat0.x) * unity_ParticleUVShiftData.y + u_xlat1.x;
    u_xlat8 = floor(u_xlat8);
    u_xlat1.x = u_xlat8 * unity_ParticleUVShiftData.z;
    u_xlat8 = (-unity_ParticleUVShiftData.w) + 1.0;
    u_xlat1.y = (-u_xlat0.x) * unity_ParticleUVShiftData.w + u_xlat8;
    u_xlat0.xy = in_TEXCOORD0.xy * unity_ParticleUVShiftData.zw + u_xlat1.xy;
    u_xlatb16 = unity_ParticleUVShiftData.x!=0.0;
    vs_TEXCOORD0.xy = (bool(u_xlatb16)) ? u_xlat0.xy : in_TEXCOORD0.xy;
    u_xlatu0 = uint(floatBitsToUint(u_xlat5.w)) & 255u;
    u_xlat0.x = float(u_xlatu0);
    u_xlatu1.xy = uvec2(bitfieldExtract(uint(floatBitsToUint(u_xlat5.w)), int(8), int(8)), bitfieldExtract(uint(floatBitsToUint(u_xlat5.w)), int(16), int(8)));
    u_xlatu1.z = uint(floatBitsToUint(u_xlat5.w)) >> 24u;
    u_xlat0.yzw = vec3(u_xlatu1.xyz);
    u_xlat0 = u_xlat0 * vec4(0.00392156886, 0.00392156886, 0.00392156886, 0.00392156886);
    u_xlat16_1 = in_COLOR0 + vec4(-1.0, -1.0, -1.0, -1.0);
    u_xlat16_1 = vec4(unity_ParticleUseMeshColors) * u_xlat16_1 + vec4(1.0, 1.0, 1.0, 1.0);
    vs_COLOR0 = u_xlat0 * u_xlat16_1;
    vs_TEXCOORD1.xyz = u_xlat6.xyz;
    u_xlat0.xyz = (-u_xlat6.xyz) + _WorldSpaceCameraPos.xyz;
    vs_TEXCOORD1.w = 0.0;
    u_xlat24 = dot(u_xlat3.xyz, u_xlat3.xyz);
    u_xlat24 = max(u_xlat24, 1.17549435e-38);
    u_xlat24 = inversesqrt(u_xlat24);
    u_xlat2.xyz = vec3(u_xlat24) * u_xlat3.xyz;
    vs_TEXCOORD2.xyz = u_xlat2.xyz;
    u_xlat24 = dot(u_xlat0.xyz, u_xlat0.xyz);
    u_xlat24 = inversesqrt(u_xlat24);
    u_xlat0.xyz = vec3(u_xlat24) * u_xlat0.xyz;
    vs_TEXCOORD3.xyz = u_xlat0.xyz;
    vs_TEXCOORD8.xyz = vec3(0.0, 0.0, 0.0);
    vs_SV_InstanceID0 =  uint(gl_InstanceID);
    return;
}

#endif
#ifdef FRAGMENT
#version 310 es

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
UNITY_BINDING(0) uniform UnityPerMaterial {
	vec4 _SoftParticleFadeParams;
	vec4 _CameraFadeParams;
	vec4 _BaseMap_ST;
	mediump vec4 _BaseColor;
	mediump vec4 _EmissionColor;
	mediump vec4 _BaseColorAddSubDiff;
	mediump float _Cutoff;
	mediump float _DistortionStrengthScaled;
	mediump float _DistortionBlend;
	mediump float _Surface;
};
UNITY_LOCATION(0) uniform mediump sampler2D _BaseMap;
layout(location = 0) in highp vec2 vs_TEXCOORD0;
layout(location = 1) in mediump vec4 vs_COLOR0;
layout(location = 0) out mediump vec4 SV_Target0;
mediump vec4 u_xlat16_0;
void main()
{
    u_xlat16_0 = texture(_BaseMap, vs_TEXCOORD0.xy);
    u_xlat16_0 = u_xlat16_0 * _BaseColor;
    SV_Target0 = u_xlat16_0 * vs_COLOR0;
    return;
}

#endif
