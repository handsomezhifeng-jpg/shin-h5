# 角色动作模拟器

当前审核入口：http://127.0.0.1:3689/

启动：在 shin-h5 目录执行 `powershell -File tools/start_action_lab.ps1`，会隐藏启动本机后台服务。前台调试可执行 `python tools/serve_action_lab.py --port 3689`。只监听本机；页面和视频位于 action-lab，审核意见单独存入 outputs/action-lab/reviews.json。

原扫地角色新版本位于列表最前：扫地20帧、走路24帧。两组由原画角色透明参考图约束Seedance 2.5首尾帧生成，从完整活动循环选出不重复帧；透明PNG、整张序列图、GIF和实际采样时间均可下载，仍待用户审核。完整检查在 outputs/original-sweeper-v3/verification.json。审核页已正确映射有限帧序列与完整原片时间，视频支持分段读取和定位。

网关兼容修复：该New API视频转发读取 metadata.content；只有顶层content时，早期候选的参考图未得到有效约束。项目适配器沿用已安装技能的鉴权、提交和防重复逻辑，将首尾帧和生成参数在内存中放入metadata后提交，不修改全局技能、不保存base64或密钥。修正后原片首帧与输入角色参考的轮廓IoU均超过0.98，原音轨为0。此前生成版本保留作核对。参考实现：https://github.com/QuantumNous/new-api/blob/main/plugins/tasks/doubao/plugin.js 。

首批8条动作由 Doubao-seedance-2-5 实际生成：扫地、携扫帚正背走路、顾客正背走路与购买、摊主服务和整理。原片均约6.08秒、720×1280、24fps；每条145帧，共1160帧。候选视频的头身比、发型或服装与身份参考存在差异，片段可能含位移、边界或衔接问题，页面已提示；需要用户审片，尚未批准或接入正式游戏。

绿幕原片与去背帧分开保留。根据实际绿幕颜色去背景，统一裁切范围后输出透明PNG与分片图集，保持帧间相对位置；原片意外带音轨，审核播放副本已实际去音轨并复核。

技能客户端保留真实任务ID和seed；私有任务记录在 ../seedance-jobs/market-actions-draft-v1（相对shin-h5），不通过审核服务器对外提供。manifest.json只包含可供审片的提示词、角色参考、任务标识和本机媒体路径，不含凭证。

页面支持逐帧、速度、循环起止帧、原片/角色参考/分时对照、背景切换、镜像、首帧叠加、模拟位移，以及通过/重做/待审和文字意见。审核点击才写入决定；测试使用隔离数据，不替用户批准。

验证：`node scripts/action-lab-check.mjs`，报告在 outputs/action-lab/page-verification.json；媒体实际解码、静音与帧数验证在 media-verification.json。
