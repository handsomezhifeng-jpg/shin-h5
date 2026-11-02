//////////////////////////////////////////
//
// NOTE: This is *not* a valid shader file
//
///////////////////////////////////////////
Shader "FTUI/UI_Universal _Alpha" {
Properties {

[Toggle(_ISUI)] _ISUI ("IsUI", Float) = 1.0

_MainTex ("MainTex", 2D) = "white" { }

_MainTex_Rotate ("MainTex_Rotate", Float) = 0.0

_Brightness ("Brightness", Float) = 1.0

_MainColor ("MainColor", Color) = (1,1,1,1)

_MainUV_Speed ("MainUV_Speed", Vector) = (0,0,0,0)

[ToggleUI] _Tex2Open ("Tex2Open", Float) = 0.0

_Tex2 ("Tex2", 2D) = "white" { }

_Tex2_Rotate ("Tex2_Rotate", Float) = 0.0

_Tex2UV_Speed ("Tex2UV_Speed", Vector) = (0,0,0,0)

_MaskMapping_Rotate ("MaskMapping_Rotate", Float) = 0.0

_MaskMapping ("MaskMapping", 2D) = "white" { }

[ToggleUI] _PolarSwitch ("PolarSwitch", Float) = 0.0

_PolarUV ("PolarUV", Vector) = (1,1,0,0)

_DissTex ("DissTex", 2D) = "white" { }

_DissTex_Rotate ("DissTex_Rotate", Float) = 0.0

_Diss_Value ("Diss_Value", Range(0, 1)) = 0.5

_DissSoft_Value ("DissSoft_Value", Range(0.5, 1)) = 0.5

_DissUV_Speed ("DissUV_Speed", Vector) = (0,0,0,0)

[ToggleUI] _DissEdgeOpen ("DissEdgeOpen", Float) = 0.0

_DissEdgeColor ("DissEdgeColor", Color) = (1,1,1,1)

_DisturbanceTex ("DisturbanceTex", 2D) = "white" { }

_DisturbanceValue ("DisturbanceValue", Float) = 0.0

_DisturbanceUV_Speed ("DisturbanceUV_Speed", Vector) = (0,0,0,0)

_QueueOffset ("_QueueOffset", Float) = 0.0

_QueueControl ("_QueueControl", Float) = -1.0

unity_Lightmaps ("unity_Lightmaps", 2DArray) = "" { }

unity_LightmapsInd ("unity_LightmapsInd", 2DArray) = "" { }

unity_ShadowMasks ("unity_ShadowMasks", 2DArray) = "" { }

}
SubShader {
 Tags { "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
 Pass {
 Name "Universal Forward"
  Tags { "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
 ZTest Always
 ZWrite Off
  GpuProgramID 21030
}
 Pass {
 Name "DepthNormalsOnly"
  Tags { "LIGHTMODE" = "DepthNormalsOnly" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
  GpuProgramID 93326
}
 Pass {
 Name "DepthNormals"
  Tags { "LIGHTMODE" = "DepthNormalsOnly" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
  GpuProgramID 326332
}
}
SubShader {
 Tags { "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
 Pass {
 Name "Universal Forward"
  Tags { "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
 ZTest Always
 ZWrite Off
  GpuProgramID 378346
}
 Pass {
 Name "DepthNormalsOnly"
  Tags { "LIGHTMODE" = "DepthNormalsOnly" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
  GpuProgramID 397865
}
 Pass {
 Name "DepthNormals"
  Tags { "LIGHTMODE" = "DepthNormalsOnly" "QUEUE" = "Transparent" "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "ShaderGraphShader" = "true" "ShaderGraphTargetId" = "UniversalUnlitSubTarget" "UniversalMaterialType" = "Unlit" }
  GpuProgramID 621604
}
}
Fall back "Hidden/Shader Graph/FallbackError"
CustomEditor "UnityEditor.ShaderGraph.GenericShaderGraphMaterialGUI"
}