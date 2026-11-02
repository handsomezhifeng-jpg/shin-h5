//////////////////////////////////////////
//
// NOTE: This is *not* a valid shader file
//
///////////////////////////////////////////
Shader "FTUI/UI_add_mask" {
Properties {

_Brightness ("Brightness", Float) = 1.0

_Contrast ("Contrast", Float) = 1.0

_MainColor ("Main Color", Color) = (1,1,1,1)

_MainTex ("Main Tex", 2D) = "white" { }

_MaskTex ("Mask Tex", 2D) = "white" { }

_MainPannerX ("Main Panner X", Float) = 0.0

_MainPannerY ("Main Panner Y", Float) = 0.0

_SecPannerX ("Sec Panner X", Float) = 0.0

_SecPannerY ("Sec Panner Y", Float) = 0.0

_SoftMask ("Mask", 2D) = "white" { }

[Enum(Off,0,On,1)] __ZWrite ("ZWrite", Float) = 0.0

[Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Use Alpha Clip", Float) = 0.0

}
SubShader {
 Tags { "IGNOREPROJECTOR" = "true" "QUEUE" = "Transparent" "RenderType" = "Transparent" }
 Pass {
  Tags { "IGNOREPROJECTOR" = "true" "QUEUE" = "Transparent" "RenderType" = "Transparent" }
 ZWrite Off
 Cull Off
  GpuProgramID 916
}
}
CustomEditor "ShaderForgeMaterialInspector"
}