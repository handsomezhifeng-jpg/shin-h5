//////////////////////////////////////////
//
// NOTE: This is *not* a valid shader file
//
///////////////////////////////////////////
Shader "Universal Render Pipeline/2D/Sprite-Unlit-Default" {
Properties {

_MainTex ("Sprite Texture", 2D) = "white" { }

_Brightness ("Brightness", Float) = 1.0

_MainColor ("Main Color", Color) = (1,1,1,1)

_Color ("Tint", Color) = (1,1,1,1)

PixelSnap ("Pixel snap", Float) = 0.0

_RendererColor ("RendererColor", Color) = (1,1,1,1)

_Flip ("Flip", Vector) = (1,1,1,1)

_AlphaTex ("External Alpha", 2D) = "white" { }

_EnableExternalAlpha ("Enable External Alpha", Float) = 0.0

}
SubShader {
 Tags { "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" }
 Pass {
  Tags { "LIGHTMODE" = "Universal2D" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" }
 ZWrite Off
 Cull Off
  GpuProgramID 47309
}
 Pass {
  Tags { "LIGHTMODE" = "UniversalForward" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" }
 ZWrite Off
 Cull Off
  GpuProgramID 76234
}
}
Fall back "Sprites/Default"
}