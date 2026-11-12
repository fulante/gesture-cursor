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

国内网络下载慢时，可加中科大镜像（2026-11-09 首次安装与 2026-11-12
迁移演练重建均用该源验证通过）：

```bat
python -m pip install -r requirements.txt -c constraints.txt ^
  -i https://pypi.mirrors.ustc.edu.cn/simple/
```

> 2026-11-12 演练中阿里云镜像解析不到 `opencv-python==4.11.0.86`
> （`ResolutionImpossible` / `No matching distribution found`），
> 换中科大源后正常。如果仍想用阿里云源，先确认它能列出该版本的
> cp312 win_amd64 wheel，再执行安装。

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

## 8. 手势稳定性改进（v1.1.5）

2026-11-09 对 `gesture_controller.py` 做了稳定性重构，原始版本完整保存在
`legacy/`，详细分析见 `CHANGELOG.md`。

主要变化：

- 手势距离全部按**手掌尺寸**归一化，不再依赖固定像素阈值；
- 手指伸展改用“指尖到 MCP / PIP 到 MCP 距离 + PIP 关节角”，手倾斜也能识别；
- 右键改为**轻触 + 边沿触发 + 锁存**：必须在短时间内有拇指-中指距离明显
  缩小的“轻触”动作，静止贴合不会触发；按住不会连续右键；必须把拇指移开
  后才重新武装；
- 滚动改为**小数累加器**：慢速移动不会丢，快速移动每帧限幅，并带
  0.18 秒宽限期；死区和每格距离下调，小幅上下移动也能滚；
- Windows 滚动改为直接发送正确的 `WHEEL_DELTA=120`，修复 PyAutoGUI
  0.9.54 把格数直接当 `dwData` 导致滚动几乎不可见的问题；
- 右键锁存增加 0.8 秒超时，避免拇指停在中间时无限期冻结光标；
- 拖拽必须“按住超过 0.3 秒 + 移动超过 0.15 手掌宽”，静止长按松开算点击，
  修复慢点击关闭按钮没反应的问题；
- 光标与屏幕四角保持 8 px，避免 PyAutoGUI failsafe 把光标卡在角落；
- 双击：两次静止的捏合；第一次点击立即发出，第二次在
  `DOUBLE_CLICK_WINDOW` 内且光标位移 ≤ `DOUBLE_CLICK_MAX_MOVE_PX` 时发出，
  Windows 识别为双击；超时或位移过大则退化为两次单击；
- 左键后 0.3 秒内抑制右键候选，避免拇指回到中指时抢走第二次点击；
- 音量：拇指 + 无名指捏合后上下移动手；先分离再捏合才进入音量模式，
  避免自然握拳误触；Windows 使用 `VK_VOLUME_UP/DOWN` 媒体键；
- 打开相机后读取第一帧，用真实 `frame.shape` 构造控制器；`FRAME_REDUCTION`
  按配置参考分辨率缩放到实际分辨率，避免光标映射偏移；
- 活动区域外不再把光标压到屏幕边缘，而是保持位置并显示 `Out of Area`；
- `MouseController.release_all()` 在 failsafe 时临时关闭 failsafe 释放左右键，
  避免安全角触发后左键卡住；
- 所有鼠标动作都捕获 PyAutoGUI failsafe，单个滚动调用最多 3 格。

新的可调参数（都在 `config.py`）：

```python
PINCH_ENTER_RATIO / PINCH_EXIT_RATIO
RIGHT_CLICK_ENTER_RATIO / RIGHT_CLICK_EXIT_RATIO / RIGHT_CLICK_DOMINANCE
RIGHT_CLICK_TAP_DELTA / RIGHT_CLICK_TAP_WINDOW / RIGHT_CLICK_LATCH_TIMEOUT
FINGER_EXTENDED_RATIO_ENTER / FINGER_EXTENDED_RATIO_EXIT
SCROLL_DEAD_ZONE_RATIO / SCROLL_PALM_PER_TICK
VOLUME_ENTER_RATIO / VOLUME_EXIT_RATIO
VOLUME_DEAD_ZONE_RATIO / VOLUME_PALM_PER_STEP
VOLUME_MAX_STEPS_PER_FRAME / VOLUME_CONFIRM_FRAMES
DRAG_HOLD_TIME / DRAG_START_MOVE_RATIO
DOUBLE_CLICK_WINDOW / DOUBLE_CLICK_MAX_MOVE_PX
RIGHT_CLICK_SUPPRESS_AFTER_CLICK
SCREEN_EDGE_MARGIN
GESTURE_CONFIRM_FRAMES / SCROLL_EXIT_GRACE
```

如果升级后右键“点一次后没反应”，这是预期行为：把拇指从中指移开
（超过 `RIGHT_CLICK_EXIT_RATIO`）再点第二次。

运行回归测试：

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

当前 38 个测试（29 个手势 + 6 个鼠标安全 + 3 个音量键）全部通过。旧版恢复方法见
`legacy/SNAPSHOT.md`；如果想对比旧版，可双击 `run_legacy.bat`（旧版仍有
滚动/右键的已知缺陷）。

现场调参建议：

- 右键太灵敏/误触：降低 `RIGHT_CLICK_ENTER_RATIO`，提高
  `RIGHT_CLICK_DOMINANCE`，或提高 `RIGHT_CLICK_TAP_DELTA`
  （要求更明显的轻触，如 0.16）。
- 右键不够灵敏：降低 `RIGHT_CLICK_TAP_DELTA`（如 0.08），提高
  `RIGHT_CLICK_ENTER_RATIO`（如 0.36），或适当降低
  `RIGHT_CLICK_DOMINANCE`（如 0.70）。
- 右键按住只触发一次是设计行为：必须把拇指移开超过
  `RIGHT_CLICK_EXIT_RATIO` 才能再次右键。
- 滚动太慢：降低 `SCROLL_PALM_PER_TICK`（如 0.12），或降低
  `SCROLL_DEAD_ZONE_RATIO`（如 0.015）。
- 滚动太快：提高 `SCROLL_PALM_PER_TICK`（如 0.20），或降低
  `SCROLL_MAX_TICKS_PER_FRAME`。
- 滚动不启动：确认食指和中指伸直、无名指和小指不要同时伸直；
  可降低 `FINGER_EXTENDED_RATIO_ENTER`（如 1.15）或
  `SCROLL_DEAD_ZONE_RATIO`。
- 滚动时页面不动：先点一下目标窗口（浏览器/文档）让它获得焦点，并把
  光标移到可滚动区域；不要把焦点留在 OpenCV 预览窗口上，滚轮事件
  会发给焦点窗口。
- 捏合点击太灵敏：降低 `PINCH_ENTER_RATIO`；点击太迟钝则提高。
- 光标偶尔卡住：先看 HUD 的 `State`/`Action`。若是 `Right Click`，
  v1.1.2 会在 `RIGHT_CLICK_LATCH_TIMEOUT=0.8` 秒后自动恢复；若是
  `PINCH`/`SCROLL`，释放捏合或收起两指。若经常在屏幕边缘卡住，可把
  `SCREEN_EDGE_MARGIN` 从 8 调到 12–16。
- 左键偶尔没反应：确认是“按住不动再松开”，而不是捏合后移动；如果仍然
  变成拖拽，把 `DRAG_START_MOVE_RATIO` 从 0.15 调到 0.20。
- 双击只选中不打开：两次点击必须落在 Windows 的双击时间内；可把
  `DOUBLE_CLICK_MAX_MOVE_PX` 调到 20。要放宽时间窗口，需要在 Windows
  鼠标设置里调慢双击速度，并把 `DOUBLE_CLICK_WINDOW` 调到不小于系统值；
  应用会取两者中更严格的值，只改一个不会生效。
- 双击时两次捏合之间必须让拇指-食指距离超过 `PINCH_EXIT_RATIO`；如果
  松手不够，第二次捏合不会被算作新的一次点击。可把 `PINCH_EXIT_RATIO`
  从 0.40 降到 0.36，让释放更容易。
- 双击太容易误开：降低 `DOUBLE_CLICK_WINDOW`（如 0.40）或
  `DOUBLE_CLICK_MAX_MOVE_PX`（如 10），确认两次捏合确实是连续动作。
- 音量不触发：先把拇指和无名指分开，再捏合；HUD 应显示 `VOLUME`。无名指
  指尖必须比食指/中指更靠近拇指，否则会按单击/右键/滚动处理。可把
  `VOLUME_ENTER_RATIO` 从 0.30 调到 0.34。
- 音量变化太慢：降低 `VOLUME_PALM_PER_STEP`（如 0.14），或降低
  `VOLUME_DEAD_ZONE_RATIO`；太快则反过来。
- 音量键没反应：先确认 Windows 本身媒体键可用；应用使用
  `VK_VOLUME_UP/DOWN`，不会修改静音状态。
- 光标映射偏移：看启动 banner 的“Camera resolution”实际值是否与请求值
  一致；v1.1.5 使用第一帧真实分辨率，若相机中途改分辨率请重启。
- 安全角后左键一直按着：v1.1.5 会通过 `release_all()` 临时关闭 failsafe
  并释放左右键；如果仍复现，记录触发前是否处于拖拽状态。
- HUD 显示 `Out of Area`：手离开了活动区域，光标会保持最后位置，把手
  移回活动区域即可恢复；这不是程序卡死。
