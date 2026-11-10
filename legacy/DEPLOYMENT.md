# 环境部署说明（Windows）

部署时间：2026-11-09
项目目录：`D:\Gesture-Cursor-main`

## 1. 当前环境状态

| 组件 | 版本 / 路径 | 状态 |
|---|---|---|
| Python | 3.12.8，`.python312\python.exe` | 已就绪 |
| 虚拟环境 | `.venv` | 已就绪 |
| OpenCV | 4.11.0.86 | 已安装 |
| MediaPipe | 0.10.21 | 已安装 |
| NumPy | 1.26.4 | 已安装 |
| PyAutoGUI | 0.9.54 | 已安装 |
| 摄像头 | 当前会话未检测到 | 无法实时运行 |

> **重要：** 当前这台机器/会话没有可用摄像头，直接运行会看到
> `[Fatal] Could not open camera at index 0.`。这是硬件/会话限制，
> 不是依赖问题。接入摄像头（或在有摄像头的电脑上运行）后即可正常使用。

## 2. 启动

双击项目根目录的 `run.bat`，或在项目目录执行：

```bat
.venv\Scripts\python.exe main.py
```

启动后会出现 **Gesture Mouse Control** 预览窗口。按 `q` 或 `Esc` 退出；
鼠标甩到屏幕角落可触发 PyAutoGUI 的 failsafe 强制中止。

手势：

| 手势 | 动作 |
|---|---|
| 只伸出食指 | 移动光标 |
| 拇指 + 食指快速捏合 | 左键单击 |
| 捏合并保持 ≥ 0.3 秒 | 拖拽，松开结束 |
| 拇指 + 中指捏合 | 右键单击 |
| 食指 + 中指伸出，上下移动 | 滚动 |

## 3. 本次部署做了什么

1. 本机原有 Python 3.11/3.12 注册项均已失效，实际可用的是 Anaconda
   **3.13**；而 `mediapipe==0.10.21` 只提供 Python 3.9–3.12 的 wheel。
2. 下载免安装的完整 CPython **3.12.8** 到 `.python312`，不修改系统
   Python，也不影响 Anaconda。
3. 用该解释器创建 `.venv`，安装 `requirements.txt` 中的依赖。
4. 使用 `constraints.txt` 固定 MediaPipe 的传递依赖，避免 2026 年的
   新版 `jax` / `opencv` / `protobuf` 与 0.10.21 不兼容。
5. 完成导入、MediaPipe 手部检测、PyAutoGUI 屏幕访问和完整主循环测试。

`constraints.txt` 中比较关键的固定项：

- `jax==0.4.38` / `jaxlib==0.4.38`：与 mediapipe 0.10.21 同期，Windows
  有 cp312 wheel；
- `numpy==1.26.4`：mediapipe 0.10.21 使用 NumPy 1.x ABI；
- `opencv-python==4.11.0.86` / `opencv-contrib-python==4.11.0.86`：
  两个包版本保持一致，避免 `cv2` 文件互相覆盖；
- `protobuf==4.25.8`、`flatbuffers==24.3.25`：满足 mediapipe 的
  `protobuf<5,>=4.25.3` 且保持同期兼容性。

## 4. 重新安装（换电脑 / 删除 `.venv` 后）

本机已经预建好 `.venv`，**不需要执行本节**；本节只用于换电脑或迁移项目。
前提：安装 **Python 3.12**（3.9–3.12 均可，**不要用 3.13**）。

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -c constraints.txt
```

国内网络下载慢时，可加阿里云镜像：

```bat
python -m pip install -r requirements.txt -c constraints.txt ^
  -i https://mirrors.aliyun.com/pypi/simple/
```

> 如果只执行 `pip install -r requirements.txt`，pip 可能安装最新的
> OpenCV 5.x / jax 0.9.x，从而与 mediapipe 0.10.21 不兼容；请带上
> `-c constraints.txt`。

## 5. 摄像头排查

### 5.1 先运行自带诊断

双击 `camera_test.bat`（从 Windows 资源管理器双击，**不要通过 AI 助手运行**）。
它会尝试 `ANY` / `DSHOW` / `MSMF` 三种后端和索引 0–5，并输出可用的组合。
按输出修改 `config.py`：

```python
CAMERA_INDEX = 0
CAMERA_BACKEND = "DSHOW"   # 或脚本报告的 ANY / MSMF
```

如果找到摄像头，脚本会在项目根目录保存 `camera_test.jpg` 快照。

### 5.2 为什么 AI 助手会话里打不开？

当前 AI 会话的 Python 进程运行在 **Low 完整性级别**（`S-1-16-4096`），
Windows 摄像头设备通常要求 Medium 及以上完整性，因此会拒绝打开设备。
这不是隐私设置问题：截图中的“摄像头访问”“允许桌面应用访问摄像头”
都已经开启，注册表 `ConsentStore\webcam` 也是 `Allow`，设备管理器中
`Integrated Camera` / `Integrated IR Camera` 均为 `Started`。

**解决方式：从 Windows 资源管理器双击 `run.bat` 或 `camera_test.bat`**，
这样进程以 Medium 完整性运行，即可访问摄像头。不要从 AI 对话里启动。

### 5.3 正常桌面下仍打不开时

1. 关闭相机、微信、Teams、OBS、联想视觉/Vantage 等可能占用摄像头的程序。
2. 检查笔记本的摄像头物理开关/快门，以及 F9（或带相机图标的 Fn 键）。
3. 联想 Vantage 中关闭“摄像头隐私模式”。
4. 设备管理器 → 摄像头 → Integrated Camera → 更新/回滚驱动程序。
5. 用 `config.py` 的 `CAMERA_BACKEND` 切换后端（例如 `"DSHOW"` / `"MSMF"`），
   不需要改 `main.py`。
6. 仍不行时，运行 `camera_test.bat` 把输出发我，重点看哪个
   backend/index 报什么错。

### 5.4 普通模式打不开、管理员模式可以

管理员模式是 **High 完整性**，能绕过某些设备访问限制。如果普通双击
`run.bat` 仍打不开摄像头，而右键“以管理员身份运行”可以，说明摄像头
驱动或安全策略要求更高权限。

可以继续用“以管理员身份运行”，但要注意：**手势程序会以管理员权限
控制鼠标**，误触或代码问题的影响范围更大。建议：

1. 先试普通双击；普通模式能打开就不要用管理员。
2. 只有确认普通模式不行时，才右键 `run.bat` →“以管理员身份运行”。
3. 不要长期把整个项目或终端都放在管理员权限下运行。

本项目不会自动请求管理员权限，保持普通启动更安全。

## 6. 验证记录

- `cv2` / `mediapipe` / `numpy` / `pyautogui` 全部导入成功；
- `mediapipe 0.10.21` 的 `mp.solutions.hands` 可用；
- 对 MediaPipe 示例手部图片检测到 **21 个关键点**；
- 用假摄像头 + 假鼠标跑通 `main.py` 的完整 8 帧循环，HUD 绘制、
  手势状态机、退出清理均正常；
- `pip check` 输出 `No broken requirements found.`；
- PyAutoGUI 识别到屏幕分辨率 `2560 x 1600`。

## 7. 注意事项

- `.python312/`、`.venv/`、`.setup/` 是本地运行时/部署产物，已加入
  `.gitignore`，不要提交到 Git。
- `.venv` 内部记录了绝对路径；移动项目目录后需要按第 4 节重建。
- 本项目会真实控制鼠标。首次运行建议先把手放在画面外，确认预览窗口
  和退出键正常，再尝试手势。
- 如果在本 DSH 沙箱会话内重新执行 `pip install`，可能遇到临时目录
  ACL 拒绝（`PermissionError: [WinError 5]`）；这是沙箱限制，正常的
  Windows 终端不受影响。
