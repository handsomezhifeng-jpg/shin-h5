//////////////////////////////////////////
//
// NOTE: This is *not* a valid shader file
//
///////////////////////////////////////////
Shader "FTUI/UI_blend" {
Properties {

_Brightness ("Brightness", Float) = 1.0

_Contrast ("Contrast", Float) = 1.0

_MainColor ("Main Color", Color) = (1,1,1,1)

_MainTex ("Main Tex", 2D) = "white" { }

_MainPannerX ("Main Panner X", Float) = 0.0

_MainPannerY ("Main Panner Y", Float) = 0.0

_Cutoff ("Alpha cutoff", Range(0, 1)) = 0.5

_StencilComp ("Stencil Comparison", Float) = 8.0

_Stencil ("Stencil ID", Float) = 0.0

_StencilOp ("Stencil Operation", Float) = 0.0

_StencilWriteMask ("Stencil Write Mask", Float) = 255.0

_StencilReadMask ("Stencil Read Mask", Float) = 255.0

_ColorMask ("Color Mask", Float) = 15.0

_SoftMask ("Mask", 2D) = "white" { }

[Enum(Off,0,On,1)] __ZWrite ("ZWrite", Float) = 0.0

[Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Use Alpha Clip", Float) = 0.0

}
SubShader {
 Tags { "IGNOREPROJECTOR" = "true" "QUEUE" = "Transparent" "RenderType" = "Transparent" }
 Pass {
 Name "FORWARD"
  Tags { "IGNOREPROJECTOR" = "true" "QUEUE" = "Transparent" "RenderType" = "Transparent" }
 ZWrite Off
 Cull Off
  GpuProgramID 15232
}
}
CustomEditor "ShaderForgeMaterialInspector"
}