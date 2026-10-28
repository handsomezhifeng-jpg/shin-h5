# 蜡笔小新棋盘 H5

运行时使用原棋盘美术、FGUI切图与布局、小新Spine动画；40格顺序、位置和模型取自原项目，机会卡、倍率、首图建筑成本和扭蛋奖励由原配表导出。

目前是浏览器本地存档版。投骰、走格、九类格子、机会卡、监狱、护盾/租金、破坏、12格盲盒、建造换图、扭蛋和存钱罐累计领取可运行。好友对手在本地模拟，未连接原账号服及社交服务。

范围：已导入两套原场景；首图建筑成本使用原表，超出已导入数值的地图采用本地计算。存钱罐目前只做累计领取，未移植完整好友基金玩法；画册仅记录扭蛋所得贴纸数量。限时活动、机会卡触发的独立挑战、线上匹配和付费系统未接入。原FGUI有缺失插图引用，机会卡暂用已有原小新插图显示，清单见assets-source.json。

## 运行

需要HTTP服务打开，不能双击file://入口（浏览器模块与资源请求需要HTTP）。本机预览可在此目录执行Python http.server，或使用常见静态网站服务。

## 文件

- src/engine.mjs：本地棋盘状态与结算。
- src/fgui.mjs：原FGUI布局读取与控件绑定。
- src/scene.mjs：原网格、UV和地图的绘制。
- scripts/export_config.py：只读导出原配置及中文文案。
- tools/export_assets.py、tools/resolve_grid_assets.py：原资源导出。
- assets-source.json：素材来源。
- tests/engine.test.mjs、scripts/browser-check.mjs：规则与浏览器操作检查。

## 构建

用Node执行 scripts/build.mjs，产物在dist。发布复用.openai/hosting.json中的同一网站身份。