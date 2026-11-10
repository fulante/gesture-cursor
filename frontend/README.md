# Gesture Cursor 前端展示页

这个目录包含 Gesture Cursor 的 React + Vite 产品展示前端。它不会修改或替代根目录中的 Python 手势控制程序。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

页面包含：

- 浏览器内直接开启摄像头，使用本地 MediaPipe 模型实时检测 21 个手部关键点
- 页面内虚拟光标，以及单击、双击、拖拽、右键和滚动的实时动作反馈
- 七种手势/动作的可交互说明与状态转换
- 21 点手部追踪视觉演示
- OpenCV → MediaPipe → GestureController → PyAutoGUI 技术管线
- `config.py` 关键参数的交互式预览
- 自动化测试、推理基准和快速安装入口

## 摄像头现场演示

点击首屏的“开启摄像头演示”，允许浏览器访问摄像头。MediaPipe 的 WASM
运行时和 `hand_landmarker.task` 模型都存放在 `public/`，推理在浏览器本地完成，
不上传摄像头画面。

摄像头访问需要 `localhost` 或 HTTPS。普通网页受浏览器安全策略限制，不能移动
Windows 系统光标；当前前端会在页面内展示虚拟光标和所有手势结果。需要控制系统
鼠标时，仍应运行项目根目录的 Python 程序。
