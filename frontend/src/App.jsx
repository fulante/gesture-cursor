import { useId, useState } from 'react'
import { useHandTracking } from './useHandTracking.js'

const gestureData = [
  {
    id: 'move',
    label: '移动',
    icon: 'move',
    title: '移动光标',
    instruction: '只伸出食指，在摄像头活动区域内移动。',
    pose: '食指伸出',
    action: '光标移动',
    state: 'CURSOR',
    flow: ['IDLE', 'CURSOR', 'IDLE'],
    activePoints: [0, 5, 6, 7, 8],
  },
  {
    id: 'click',
    label: '单击',
    icon: 'click',
    title: '左键单击',
    instruction: '拇指与食指快速捏合，松开时完成一次点击。',
    pose: '拇指 + 食指',
    action: '左键单击',
    state: 'PINCH',
    flow: ['IDLE', 'PINCH', 'CLICK'],
    activePoints: [4, 8],
  },
  {
    id: 'double',
    label: '双击',
    icon: 'double',
    title: '双击打开',
    instruction: '在系统双击窗口内完成两次静止捏合，光标位移不超过 16 px。',
    pose: '连续双捏合',
    action: '系统双击',
    state: 'DOUBLE',
    flow: ['PINCH', 'CLICK × 2', 'OPEN'],
    activePoints: [4, 8],
  },
  {
    id: 'drag',
    label: '拖拽',
    icon: 'drag',
    title: '拖拽与释放',
    instruction: '捏合按住超过 0.3 秒，并移动超过 0.15 个手掌宽。',
    pose: '捏合 + 移动',
    action: '按住 / 拖放',
    state: 'DRAG',
    flow: ['PINCH', 'DRAG', 'DROP'],
    activePoints: [0, 4, 8],
  },
  {
    id: 'right',
    label: '右键',
    icon: 'right',
    title: '右键菜单',
    instruction: '拇指快速轻触中指；静止贴合不会触发右键。',
    pose: '拇指 + 中指',
    action: '右键单击',
    state: 'RIGHT',
    flow: ['IDLE', 'TAP', 'RIGHT CLICK'],
    activePoints: [4, 12],
  },
  {
    id: 'scroll',
    label: '滚动',
    icon: 'scroll',
    title: '两指滚动',
    instruction: '伸出食指与中指，上下移动整只手控制页面滚动。',
    pose: '食指 + 中指',
    action: '滚轮上下',
    state: 'SCROLL',
    flow: ['IDLE', 'SCROLL', 'IDLE'],
    activePoints: [0, 5, 6, 7, 8, 9, 10, 11, 12],
  },
  {
    id: 'volume',
    label: '音量',
    icon: 'volume',
    title: '系统音量调节',
    instruction: '先张开拇指与无名指，再捏合；然后上下移动整只手调节音量。',
    pose: '拇指 + 无名指',
    action: '音量增减',
    state: 'VOLUME',
    flow: ['IDLE', 'VOLUME', 'UP / DOWN'],
    activePoints: [0, 4, 13, 16],
  },
]

const pipeline = [
  { title: '摄像头', tech: 'OpenCV', icon: 'camera' },
  { title: '21 点追踪', tech: 'MediaPipe', icon: 'landmarks' },
  { title: '手势状态机', tech: 'GestureController', icon: 'state' },
  { title: '鼠标动作', tech: 'PyAutoGUI', icon: 'cursor' },
]

const initialSettings = {
  smoothing: 0.4,
  sensitivity: 1,
  pinch: 0.3,
  drag: 0.3,
}

const settingsMeta = [
  { id: 'smoothing', label: '移动平滑', min: 0.1, max: 0.9, step: 0.05, format: (value) => value.toFixed(2) },
  { id: 'sensitivity', label: '光标灵敏度', min: 0.5, max: 1.5, step: 0.05, format: (value) => `${value.toFixed(2)}×` },
  { id: 'pinch', label: '捏合阈值', min: 0.15, max: 0.45, step: 0.01, format: (value) => value.toFixed(2) },
  { id: 'drag', label: '拖拽延时', min: 0.1, max: 0.7, step: 0.05, format: (value) => `${value.toFixed(2)}s` },
]

function Icon({ name, size = 22, strokeWidth = 1.8 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  }

  const paths = {
    arrow: <><path d="M5 12h14" /><path d="m14 7 5 5-5 5" /></>,
    play: <path d="m8 5 11 7-11 7Z" fill="currentColor" stroke="none" />,
    menu: <><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></>,
    close: <><path d="m6 6 12 12" /><path d="M18 6 6 18" /></>,
    move: <><path d="M12 2v20M2 12h20" /><path d="m8 6 4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4" /></>,
    click: <><path d="M12 2v4M4.93 4.93l2.83 2.83M2 12h4" /><path d="m10 10 3 11 2.1-4.7L20 14Z" /></>,
    double: <><path d="M7 3v3M2.8 4.8l2.1 2.1M2 10h3" /><path d="m7 8 3 11 2-4.5 4.5-2Z" /><path d="m13 5 3 11 2-4.5 4-2Z" /></>,
    drag: <><rect x="3" y="3" width="12" height="12" rx="2" strokeDasharray="3 3" /><path d="m10 10 3 11 2.2-4.7L20 14Z" /></>,
    right: <><rect x="6" y="2.5" width="12" height="19" rx="6" /><path d="M12 3v7M12 10h6" /><path d="M6 10h12" /></>,
    scroll: <><path d="M12 3v18" /><path d="m8 7 4-4 4 4M8 17l4 4 4-4" /></>,
    volume: <><path d="M11 5 6 9H3v6h3l5 4V5Z" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M18.6 5.9a9.3 9.3 0 0 1 0 12.2" /></>,
    camera: <><circle cx="12" cy="12" r="4" /><path d="M3 8a2 2 0 0 1 2-2h3l1-2h6l1 2h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" /></>,
    landmarks: <><circle cx="12" cy="18" r="1.2" fill="currentColor" /><circle cx="7" cy="10" r="1.2" fill="currentColor" /><circle cx="10" cy="5" r="1.2" fill="currentColor" /><circle cx="15" cy="6" r="1.2" fill="currentColor" /><circle cx="18" cy="11" r="1.2" fill="currentColor" /><path d="m12 18-5-8 3-5 2 13 3-12 3 5-6 7" /></>,
    state: <><rect x="2" y="4" width="8" height="5" rx="2.5" /><rect x="14" y="15" width="8" height="5" rx="2.5" /><path d="M10 6.5h4a3 3 0 0 1 3 3v1.5" /><path d="m15 9 2 2 2-2" /><path d="M14 17.5h-4a3 3 0 0 1-3-3V13" /><path d="m5 15-2-2 2-2" /></>,
    cursor: <path d="m5 3 13 8-6 2-3 6Z" />,
    webcam: <><circle cx="12" cy="11" r="5" /><circle cx="12" cy="11" r="2" /><path d="M5 21h14M8 16l-1 5M16 16l1 5" /></>,
    shield: <><path d="M12 3 4 6v5c0 5 3.4 8.4 8 10 4.6-1.6 8-5 8-10V6Z" /><path d="m9 12 2 2 4-5" /></>,
    gesture: <><path d="M8.5 12V5.5a1.5 1.5 0 0 1 3 0V10" /><path d="M11.5 9V4a1.5 1.5 0 0 1 3 0v6" /><path d="M14.5 9V5.5a1.5 1.5 0 0 1 3 0V13" /><path d="M8.5 10.5 7 9a1.5 1.5 0 0 0-2.2 2l4.6 7a5 5 0 0 0 4.2 2.2h.4a5 5 0 0 0 5-5V10a1.5 1.5 0 0 0-1.5-1.5" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    bolt: <path d="m13 2-9 12h7l-1 8 9-12h-7Z" />,
    terminal: <><path d="m4 7 4 4-4 4" /><path d="M11 15h7" /></>,
    package: <><path d="m4 7 8-4 8 4-8 4Z" /><path d="M4 7v10l8 4 8-4V7M12 11v10" /></>,
    download: <><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" /></>,
    code: <><path d="m8 9-3 3 3 3M16 9l3 3-3 3M14 5l-4 14" /></>,
  }

  return <svg {...common}>{paths[name] ?? paths.cursor}</svg>
}

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span className="brand-mark__corner brand-mark__corner--tl" />
      <span className="brand-mark__corner brand-mark__corner--br" />
      <Icon name="gesture" size={24} strokeWidth={1.65} />
    </span>
  )
}

function CornerFrame() {
  return (
    <span className="corner-frame" aria-hidden="true">
      <i className="corner-frame__tl" />
      <i className="corner-frame__tr" />
      <i className="corner-frame__bl" />
      <i className="corner-frame__br" />
    </span>
  )
}

function Header({ menuOpen, onMenuToggle }) {
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="Gesture Cursor 首页">
        <BrandMark />
        <span>Gesture Cursor</span>
      </a>
      <button
        type="button"
        className="menu-button"
        aria-label={menuOpen ? '关闭菜单' : '打开菜单'}
        aria-expanded={menuOpen}
        onClick={onMenuToggle}
      >
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <nav className={menuOpen ? 'main-nav main-nav--open' : 'main-nav'} aria-label="主导航">
        <a href="#gestures">功能</a>
        <a href="#architecture">工作原理</a>
        <a href="#quickstart">快速开始</a>
        <a className="header-cta" href="#quickstart">
          <Icon name="play" size={16} />
          启动指南
        </a>
      </nav>
    </header>
  )
}

const handPoints = [
  [128, 252], [103, 220], [82, 190], [64, 158], [49, 129],
  [112, 170], [106, 128], [104, 86], [103, 47],
  [136, 164], [138, 112], [138, 67], [139, 27],
  [159, 174], [171, 130], [180, 94], [187, 61],
  [180, 190], [200, 160], [214, 135], [226, 111],
]

const handConnections = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
]

function HandDiagram({ gesture, compact = false }) {
  const active = new Set(gesture.activePoints)
  const prefix = useId()
  const selectedLinks = gesture.id === 'click' || gesture.id === 'double' || gesture.id === 'drag'
    ? [[4, 8]]
    : gesture.id === 'right'
      ? [[4, 12]]
      : gesture.id === 'volume'
        ? [[4, 16]]
        : []

  return (
    <div className={compact ? 'hand-diagram hand-diagram--compact' : 'hand-diagram'}>
      <svg viewBox="0 0 270 290" role="img" aria-label={`${gesture.label}手势关键点示意图`}>
        <defs>
          <linearGradient id={`${prefix}-hand-fill`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#263139" stopOpacity=".92" />
            <stop offset="1" stopColor="#12171b" stopOpacity=".78" />
          </linearGradient>
          <filter id={`${prefix}-point-glow`} x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <path
          className="hand-diagram__silhouette"
          d="M128 260C103 251 85 239 77 221c-7-17-16-36-28-54-7-10-7-20-1-25 7-6 15-3 22 5l22 28-8-86c-1-13 5-21 14-21 8 0 13 6 15 17l6 49 2-91c0-13 6-21 16-21 9 0 14 7 14 19l2 91 12-70c2-12 8-18 17-17 9 1 13 9 11 21l-9 76 24-42c6-10 14-13 22-8 8 5 9 14 3 25l-30 66c-9 20-14 41-15 63Z"
          fill={`url(#${prefix}-hand-fill)`}
        />
        {handConnections.map(([from, to]) => (
          <line
            key={`${from}-${to}`}
            className={active.has(from) && active.has(to) ? 'hand-diagram__line hand-diagram__line--active' : 'hand-diagram__line'}
            x1={handPoints[from][0]}
            y1={handPoints[from][1]}
            x2={handPoints[to][0]}
            y2={handPoints[to][1]}
          />
        ))}
        {selectedLinks.map(([from, to]) => (
          <line
            key={`selected-${from}-${to}`}
            className="hand-diagram__gesture-link"
            x1={handPoints[from][0]}
            y1={handPoints[from][1]}
            x2={handPoints[to][0]}
            y2={handPoints[to][1]}
          />
        ))}
        {handPoints.map(([x, y], index) => (
          <circle
            key={index}
            className={active.has(index) ? 'hand-diagram__point hand-diagram__point--active' : 'hand-diagram__point'}
            cx={x}
            cy={y}
            r={active.has(index) ? 4.6 : 3.3}
            filter={active.has(index) ? `url(#${prefix}-point-glow)` : undefined}
          />
        ))}
      </svg>
      <div className={`motion-cue motion-cue--${gesture.id}`} aria-hidden="true">
        <span />
        <Icon name={gesture.id === 'scroll' ? 'scroll' : gesture.id === 'move' ? 'cursor' : gesture.icon} size={compact ? 24 : 30} />
      </div>
    </div>
  )
}

function GestureTabs({ activeId, onChange, compact = false }) {
  return (
    <div className={compact ? 'gesture-tabs gesture-tabs--compact' : 'gesture-tabs'} role="tablist" aria-label="手势列表">
      {gestureData.map((gesture) => (
        <button
          key={gesture.id}
          type="button"
          role="tab"
          aria-selected={activeId === gesture.id}
          className={activeId === gesture.id ? 'gesture-tab gesture-tab--active' : 'gesture-tab'}
          onClick={() => onChange(gesture.id)}
        >
          <Icon name={gesture.icon} size={compact ? 18 : 21} />
          <span>{gesture.label}</span>
        </button>
      ))}
    </div>
  )
}

function LiveFeedback({ feedback, snapshot }) {
  const actionLabel = {
    click: '单击成功',
    double: '双击成功',
    drop: '拖放完成',
    right: '右键菜单',
    volume: feedback.volumeDelta > 0 ? '音量增大' : feedback.volumeDelta < 0 ? '音量减小' : '音量调节',
    scroll: snapshot.action,
  }[feedback.type]

  return (
    <>
      {feedback.type && feedback.type !== 'scroll' ? (
        <span
          key={feedback.sequence}
          className={`live-action-ripple live-action-ripple--${feedback.type}`}
          style={{ left: `${feedback.x}%`, top: `${feedback.y}%` }}
          aria-hidden="true"
        >
          {feedback.type === 'double' ? '×2' : feedback.type === 'right' ? 'R' : feedback.type === 'volume' ? (feedback.volumeDelta > 0 ? '+' : '−') : '✓'}
        </span>
      ) : null}
      {feedback.type === 'right' ? (
        <div
          key={`menu-${feedback.sequence}`}
          className="live-context-menu"
          style={{ left: `${Math.min(feedback.x, 72)}%`, top: `${Math.min(feedback.y, 64)}%` }}
        >
          <span>现场右键菜单</span>
          <button type="button">识别成功</button>
        </div>
      ) : null}
      <div className="live-action-panel" aria-live="polite">
        <div>
          <span>现场动作</span>
          <strong>{actionLabel ?? snapshot.action}</strong>
        </div>
        <div className="live-scroll-meter" aria-label={`滚动位置 ${Math.round(feedback.scroll)}%`}>
          <i style={{ left: `${feedback.scroll}%` }} />
        </div>
      </div>
    </>
  )
}

function HeroStage({ activeGesture, onGestureChange, tracking }) {
  const isLive = tracking.status === 'running'
  const isLoading = tracking.status === 'loading'
  const statusLabel = isLive ? 'LIVE' : isLoading ? 'LOADING' : 'CAMERA'

  return (
    <div className={isLive ? 'hero-stage hero-stage--live' : 'hero-stage'} id="live-demo">
      <CornerFrame />
      <div className="stage-grid" aria-hidden="true" />
      <div className="stage-hud">
        <div className="hud-left">
          <span className={isLive ? 'status-label status-label--live' : 'status-label'}><i /> {statusLabel}</span>
          <span className="hud-divider" />
          <span>{isLive ? `${tracking.snapshot.fps || '--'} FPS` : '-- FPS'}</span>
        </div>
        <div className="hud-mode">
          <span>{isLive ? tracking.snapshot.state : activeGesture.state}</span>
          <span>{isLive ? tracking.snapshot.action : activeGesture.label}</span>
        </div>
      </div>

      <div className={isLive || isLoading ? 'hero-stage__camera hero-stage__camera--active' : 'hero-stage__camera'}>
        <video ref={tracking.videoRef} muted playsInline aria-label="实时摄像头画面" />
        <canvas ref={tracking.canvasRef} aria-hidden="true" />
        <span ref={tracking.cursorRef} className="virtual-cursor" aria-hidden="true">
          <Icon name="cursor" size={28} strokeWidth={2} />
        </span>
        {isLive ? <LiveFeedback feedback={tracking.feedback} snapshot={tracking.snapshot} /> : null}
      </div>

      <div className={isLive || isLoading ? 'hero-stage__visual hero-stage__visual--hidden' : 'hero-stage__visual'}>
        <HandDiagram gesture={activeGesture} compact />
      </div>

      {!isLive ? (
        <div className="camera-gate">
          <span className="camera-gate__icon"><Icon name="webcam" size={28} /></span>
          <div>
            <strong>{isLoading ? '正在加载识别模型' : '开启现场演示'}</strong>
            <p>{isLoading ? '首次加载需要几秒，请保持页面开启。' : '实时识别 21 点；演示仅控制网页内反馈。'}</p>
          </div>
          <button type="button" onClick={tracking.start} disabled={isLoading}>
            {isLoading ? <span className="loading-spinner" /> : <Icon name="play" size={15} />}
            {isLoading ? '初始化中' : '开启摄像头'}
          </button>
          {tracking.error ? <span className="camera-gate__error">{tracking.error}</span> : null}
        </div>
      ) : (
        <button type="button" className="stage-stop" onClick={tracking.stop} aria-label="关闭摄像头">
          <Icon name="close" size={16} />
          关闭
        </button>
      )}

      {isLive ? (
        <div className="live-meta">
          <span>{tracking.snapshot.hands ? '检测到 1 只手' : '请把手放入画面'}</span>
          {tracking.snapshot.handedness ? (
            <span>{tracking.snapshot.handedness === 'Left' ? '左手' : '右手'} · {Math.round(tracking.snapshot.confidence * 100)}%</span>
          ) : null}
        </div>
      ) : null}
      <GestureTabs activeId={activeGesture.id} onChange={onGestureChange} compact />
    </div>
  )
}

function FeatureStrip() {
  const features = [
    { icon: 'webcam', title: '普通摄像头即可', copy: '无需额外硬件' },
    { icon: 'shield', title: '本地运行', copy: '保护隐私与数据' },
    { icon: 'gesture', title: '七种完整操作', copy: '移动 · 点击 · 拖拽 · 滚动 · 音量' },
  ]

  return (
    <div className="feature-strip" aria-label="核心特性">
      {features.map((feature) => (
        <div className="feature-strip__item" key={feature.title}>
          <Icon name={feature.icon} size={25} />
          <div>
            <strong>{feature.title}</strong>
            <span>{feature.copy}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function SectionHeading({ title, copy }) {
  return (
    <div className="section-heading">
      <i aria-hidden="true" />
      <div>
        <h2>{title}</h2>
        {copy ? <p>{copy}</p> : null}
      </div>
    </div>
  )
}

function GestureExplorer({ activeGesture, onGestureChange }) {
  return (
    <section className="gestures-section page-section" id="gestures">
      <SectionHeading title="手势一览" copy="用自然的手势，完成日常的鼠标操作。" />
      <GestureTabs activeId={activeGesture.id} onChange={onGestureChange} />
      <div className="gesture-detail" role="tabpanel" aria-label={`${activeGesture.label}手势说明`}>
        <CornerFrame />
        <div className="gesture-detail__visual">
          <div className="stage-grid" aria-hidden="true" />
          <HandDiagram gesture={activeGesture} />
        </div>
        <div className="gesture-detail__copy">
          <div className="detail-title">
            <i />
            <div>
              <span className="detail-title__index">0{gestureData.findIndex((item) => item.id === activeGesture.id) + 1}</span>
              <h3>{activeGesture.title}</h3>
            </div>
          </div>
          <p className="detail-instruction">{activeGesture.instruction}</p>
          <dl className="detail-data">
            <div><dt>手势</dt><dd><Icon name="gesture" size={19} />{activeGesture.pose}</dd></div>
            <div><dt>系统动作</dt><dd><Icon name="cursor" size={19} />{activeGesture.action}</dd></div>
            <div><dt>识别状态</dt><dd><span className="state-code">{activeGesture.state}</span></dd></div>
          </dl>
          <p className="detail-hint">点击任一手势查看动作要领</p>
        </div>
        <div className="state-flow" aria-label="状态转换">
          {activeGesture.flow.map((state, index) => (
            <div className="state-flow__fragment" key={`${state}-${index}`}>
              <span className={index === 1 ? 'state-flow__node state-flow__node--active' : 'state-flow__node'}>{state}</span>
              {index < activeGesture.flow.length - 1 ? <Icon name="arrow" size={24} /> : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Architecture() {
  return (
    <section className="architecture-section page-section" id="architecture">
      <SectionHeading
        title="从手部到光标"
        copy="采集画面、追踪 21 个关键点，再由状态机把自然动作转换为系统鼠标事件。"
      />
      <div className="pipeline">
        {pipeline.map((step, index) => (
          <div className="pipeline__fragment" key={step.title}>
            <article className="pipeline__step">
              <span className="pipeline__icon"><Icon name={step.icon} size={34} /></span>
              <h3>{step.title}</h3>
              <span className="pipeline__tech">{step.tech}</span>
            </article>
            {index < pipeline.length - 1 ? <span className="pipeline__arrow"><Icon name="arrow" size={26} /></span> : null}
          </div>
        ))}
      </div>
    </section>
  )
}

function Calibration() {
  const [settings, setSettings] = useState(initialSettings)

  const updateSetting = (id, value) => {
    setSettings((current) => ({ ...current, [id]: Number(value) }))
  }

  return (
    <section className="calibration-section page-section" id="calibration">
      <SectionHeading
        title="为不同的手，调到刚刚好"
        copy="关键参数集中在 config.py，识别灵敏度与光标手感都可以微调。"
      />
      <div className="calibration-layout">
        <div className="settings-panel">
          <div className="panel-header">
            <div><Icon name="code" size={22} /><h3>参数预览</h3></div>
            <code>config.py</code>
          </div>
          <div className="settings-list">
            {settingsMeta.map((setting) => {
              const value = settings[setting.id]
              const progress = ((value - setting.min) / (setting.max - setting.min)) * 100
              return (
                <label className="setting-row" key={setting.id}>
                  <span>{setting.label}</span>
                  <input
                    type="range"
                    min={setting.min}
                    max={setting.max}
                    step={setting.step}
                    value={value}
                    style={{ '--range-progress': `${progress}%` }}
                    onChange={(event) => updateSetting(setting.id, event.target.value)}
                  />
                  <output>{setting.format(value)}</output>
                </label>
              )
            })}
          </div>
          <p className="panel-note">交互式预览 · 运行参数以项目中的 config.py 为准</p>
        </div>
        <aside className="proof-panel" aria-label="工程验证">
          <div className="proof-panel__title"><Icon name="shield" size={26} /><h3>工程验证</h3></div>
          <div className="proof-item">
            <span className="proof-item__icon"><Icon name="check" size={20} /></span>
            <div><strong>29</strong><span>项自动化测试</span></div>
          </div>
          <div className="proof-item">
            <span className="proof-item__icon"><Icon name="bolt" size={20} /></span>
            <div><small>p50</small><strong>11.3 ms</strong></div>
          </div>
          <p>640 × 480 · MODEL_COMPLEXITY=1<br />静态示例图推理基准</p>
        </aside>
      </div>
    </section>
  )
}

function QuickStart() {
  const [showDetails, setShowDetails] = useState(false)
  const steps = [
    { number: '01', icon: 'terminal', title: '创建 Python 3.12 环境', code: 'py -3.12 -m venv .venv' },
    { number: '02', icon: 'package', title: '安装 requirements.txt', code: 'pip install -r requirements.txt' },
    { number: '03', icon: 'play', title: '运行 run.bat', code: '双击即可启动' },
  ]

  return (
    <section className="quickstart-section page-section" id="quickstart">
      <SectionHeading title="三步开始" copy="在 Windows 上快速搭建并运行 Gesture Cursor。" />
      <div className="quickstart-steps">
        {steps.map((step, index) => (
          <div className="quickstart-step__fragment" key={step.number}>
            <article className="quickstart-step">
              <span className="quickstart-step__number">{step.number}</span>
              <Icon name={step.icon} size={26} />
              <div>
                <h3>{step.title}</h3>
                <code>{step.code}</code>
              </div>
            </article>
            {index < steps.length - 1 ? <span className="quickstart-arrow"><Icon name="arrow" size={25} /></span> : null}
          </div>
        ))}
      </div>
      <button
        type="button"
        className="primary-button quickstart-cta"
        aria-expanded={showDetails}
        aria-controls="install-details"
        onClick={() => setShowDetails((visible) => !visible)}
      >
        <Icon name="download" size={20} />
        {showDetails ? '收起安装命令' : '查看完整安装说明'}
      </button>
      <div
        className={showDetails ? 'quickstart-details quickstart-details--visible' : 'quickstart-details'}
        id="install-details"
        aria-hidden={!showDetails}
      >
        <div><span>1</span><code>py -3.12 -m venv .venv</code></div>
        <div><span>2</span><code>.venv\Scripts\activate</code></div>
        <div><span>3</span><code>python -m pip install -r requirements.txt -c constraints.txt</code></div>
        <div><span>4</span><code>run.bat</code></div>
        <p>Python 3.9–3.12 可用，推荐 3.12；当前 MediaPipe 依赖不支持 Python 3.13。</p>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="brand brand--footer"><BrandMark /><span>Gesture Cursor</span></div>
      <p>普通摄像头，也能成为自然的人机交互入口。</p>
      <span className="version">v1.1.3</span>
    </footer>
  )
}

function App() {
  const [activeId, setActiveId] = useState('move')
  const [menuOpen, setMenuOpen] = useState(false)
  const tracking = useHandTracking((gesture) => {
    if (gesture.gestureId) setActiveId(gesture.gestureId)
  })
  const activeGesture = gestureData.find((gesture) => gesture.id === activeId) ?? gestureData[0]

  const selectGesture = (id) => {
    setActiveId(id)
  }

  return (
    <div className="app" id="top">
      <Header menuOpen={menuOpen} onMenuToggle={() => setMenuOpen((open) => !open)} />
      <main>
        <section className="hero page-section">
          <div className="hero__copy">
            <h1>让手势，<br />成为你的光标</h1>
            <p>用普通摄像头捕捉 21 个手部关键点，把移动、点击、拖拽与滚动变成自然动作。</p>
            <div className="hero__actions">
              <button
                type="button"
                className="primary-button"
                onClick={tracking.status === 'running' ? tracking.stop : tracking.start}
                disabled={tracking.status === 'loading'}
              >
                <Icon name={tracking.status === 'running' ? 'close' : 'webcam'} size={20} />
                {tracking.status === 'running' ? '关闭现场演示' : tracking.status === 'loading' ? '正在初始化' : '开启摄像头演示'}
              </button>
              <a className="secondary-button" href="#gestures">
                <Icon name="gesture" size={20} />
                查看手势说明
              </a>
            </div>
            <FeatureStrip />
          </div>
          <HeroStage activeGesture={activeGesture} onGestureChange={selectGesture} tracking={tracking} />
        </section>
        <GestureExplorer activeGesture={activeGesture} onGestureChange={selectGesture} />
        <Architecture />
        <Calibration />
        <QuickStart />
      </main>
      <Footer />
    </div>
  )
}

export default App
