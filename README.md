# 蜡笔小新棋盘 H5

运行时使用原棋盘美术、FGUI切图与布局、小新Spine动画；40格顺序、位置和模型取自原项目，机会卡、倍率、首图建筑成本和扭蛋奖励由原配表导出。

目前是浏览器本地存档版。投骰、走格、九类格子、机会卡、监狱、护盾/租金、破坏、12格盲盒、建造换图、扭蛋和存钱罐累计领取可运行。好友对手在本地模拟，未连接原账号服及社交服务。

范围：已按原表导入前三图：春日部(base1)、野原家(base41)、幼稚园(base2)；首图建筑成本使用原表，超出已导入数值的地图采用本地计算。存钱罐目前只做累计领取，未移植完整好友基金玩法；画册仅记录扭蛋所得贴纸数量。限时活动、机会卡触发的独立挑战、线上匹配和付费系统未接入。FGUI旧占位引用未作为真实插图使用：机会卡插图读取原ChanceIcon的_01资源；UI使用默认原版分支，不混用assets_CN。FGUI仍由H5适配器呈现，未完整移植全部转场和粒子特效。

## 运行

需要HTTP服务打开，不能双击file://入口（浏览器模块与资源请求需要HTTP）。本机预览可在此目录执行Python http.server，或使用常见静态网站服务。

## 文件

- src/engine.mjs：本地棋盘状态与结算。
- src/fgui.mjs：原FGUI布局读取与控件绑定。
- src/scene.mjs：原网格、UV和地图的绘制。
- scripts/export_config.py：只读导出原配置及中文文案。
- tools/export_assets.py、tools/export_fidelity_ui.py、tools/inspect_board_scene.py、tools/inspect_grid_shader.py、tools/export_fund_prop.py、tools/export_dice_prop.py：原资源导出。
- assets-source.json、fidelity-assets-source.json、assets/scene/original-scene-evidence.json：素材来源。
- tests/engine.test.mjs、scripts/browser-check.mjs：规则与浏览器操作检查。

## 构建

用Node执行 scripts/build.mjs，产物在dist。发布复用.openai/hosting.json中的同一网站身份。
本次画面校正：使用原35°相机、0.9棋盘比例、格子各自材质与顶点色；按原矩阵绘制前后景和格面文字，小新按0.01×0.24比例及原Center朝向显示；存钱罐和普通骰子使用原3D模型，普通投骰重放原横向动画及6×6落点修正。建造图读取map_base坐标与原贴图大小。

动态还原：普通经过/落地重放原 ani_gezi_jingguo、ani_gezi_stop（1.5倍速），连带父节点变形和原加色叠层。普通移动使用walk，捣蛋末三格使用原jump01/02/03，移动时长按原速度/距离计算，动画画框覆盖原跳跃全部边界；相机按原Cinemachine的1秒误差衰减到1%的阻尼逐帧跟随XY，并保留0.5秒启用过渡。数据在assets/scene/board-motion.json、board-overlays.json、piece-motion.json。

棋盘模型现在共用三维深度缓冲，倾斜和联动时按几何遮挡。格面数字仍单独绘制，原TMP深度需要运行时核对；落地烟尘和扫光粒子未移植。
