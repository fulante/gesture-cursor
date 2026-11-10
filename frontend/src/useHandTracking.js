import { useCallback, useEffect, useRef, useState } from 'react'

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
]

const INITIAL_SNAPSHOT = {
  gestureId: 'move',
  state: 'READY',
  action: '等待开启',
  fps: 0,
  hands: 0,
  handedness: '',
  confidence: 0,
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function cosineAtPip(mcp, pip, tip) {
  const ax = pip.x - mcp.x
  const ay = pip.y - mcp.y
  const bx = tip.x - pip.x
  const by = tip.y - pip.y
  const denominator = Math.hypot(ax, ay) * Math.hypot(bx, by)
  return denominator > 1e-8 ? (ax * bx + ay * by) / denominator : 0
}

function fingerExtended(landmarks, tipIndex, pipIndex, mcpIndex) {
  const tip = landmarks[tipIndex]
  const pip = landmarks[pipIndex]
  const mcp = landmarks[mcpIndex]
  const ratio = distance(tip, mcp) / Math.max(distance(pip, mcp), 1e-6)
  return ratio > 1.18 && cosineAtPip(mcp, pip, tip) > 0.05
}

function palmCenterY(landmarks) {
  return [0, 5, 9, 13, 17].reduce((sum, index) => sum + landmarks[index].y, 0) / 5
}

function updateVolumePose(landmarks, palm, thumbRing, controller) {
  // 拇指与无名指分开到退出阈值之外：结束音量模式并重新武装
  if (thumbRing > VOLUME_EXIT_RATIO) {
    controller.volumeActive = false
    controller.volumeArmed = true
    controller.volumeAnchorY = null
    controller.volumeAccumulator = 0
    return { state: 'IDLE', action: 'Volume Stop', steps: 0 }
  }

  const cursorY = palmCenterY(landmarks)
  if (controller.volumeAnchorY === null) {
    controller.volumeAnchorY = cursorY
    return { state: 'VOLUME', action: 'Volume Ready', steps: 0 }
  }

  const delta = cursorY - controller.volumeAnchorY
  const deadZone = palm * VOLUME_DEAD_ZONE_RATIO
  if (Math.abs(delta) > deadZone) {
    const palmPerStep = Math.max(0.008, palm * VOLUME_PALM_PER_STEP)
    controller.volumeAccumulator += -delta / palmPerStep
    let steps = Math.trunc(controller.volumeAccumulator)
    steps = Math.max(-VOLUME_MAX_STEPS_PER_FRAME, Math.min(VOLUME_MAX_STEPS_PER_FRAME, steps))
    controller.volumeAccumulator -= steps
    controller.volumeAccumulator = Math.max(-VOLUME_MAX_STEPS_PER_FRAME, Math.min(VOLUME_MAX_STEPS_PER_FRAME, controller.volumeAccumulator))
    controller.volumeAnchorY = cursorY
    if (steps) {
      return { state: 'VOLUME', action: steps > 0 ? 'Volume Up' : 'Volume Down', steps }
    }
  }
  return { state: 'VOLUME', action: 'Volume Ready', steps: 0 }
}

const VOLUME_ENTER_RATIO = 0.3
const VOLUME_EXIT_RATIO = 0.4
const VOLUME_DEAD_ZONE_RATIO = 0.03
const VOLUME_PALM_PER_STEP = 0.18
const VOLUME_MAX_STEPS_PER_FRAME = 2
const VOLUME_CONFIRM_FRAMES = 2

function createControllerState() {
  return {
    pinchActive: false,
    pinchStartedAt: 0,
    pinchStartPoint: null,
    dragging: false,
    lastClickAt: 0,
    lastClickPoint: null,
    rightHistory: [],
    rightLatched: false,
    scrollAnchorY: null,
    scrollAccumulator: 0,
    volumeArmed: false,
    volumeActive: false,
    volumeFrames: 0,
    volumeAnchorY: null,
    volumeAccumulator: 0,
  }
}

function resetController(controller) {
  Object.assign(controller, createControllerState())
}

function classifyGesture(landmarks, now, controller) {
  const palm = Math.max(distance(landmarks[0], landmarks[9]), 1e-5)
  const indexExtended = fingerExtended(landmarks, 8, 6, 5)
  const middleExtended = fingerExtended(landmarks, 12, 10, 9)
  const ringExtended = fingerExtended(landmarks, 16, 14, 13)
  const pinkyExtended = fingerExtended(landmarks, 20, 18, 17)
  const thumbIndex = distance(landmarks[4], landmarks[8]) / palm
  const thumbMiddle = distance(landmarks[4], landmarks[12]) / palm
  const thumbRing = distance(landmarks[4], landmarks[16]) / palm
  const cursor = { x: 1 - landmarks[8].x, y: landmarks[8].y }

  // 音量模式进行中：拇指 + 无名指捏合并上下移动整只手
  if (controller.volumeActive) {
    const volume = updateVolumePose(landmarks, palm, thumbRing, controller)
    return {
      gestureId: 'volume',
      state: volume.state,
      action: volume.action,
      event: volume.steps ? 'volume' : undefined,
      volumeSteps: volume.steps,
      cursor,
    }
  }

  // 音量武装：拇指与无名指先分开，防止握拳时误触发
  if (thumbRing > VOLUME_EXIT_RATIO) {
    controller.volumeArmed = true
  }

  const volumeCandidate = !controller.pinchActive
    && !controller.rightLatched
    && controller.volumeArmed
    && thumbRing < VOLUME_ENTER_RATIO
    && thumbRing < thumbIndex
    && thumbRing < thumbMiddle
  if (volumeCandidate) {
    controller.volumeFrames += 1
    if (controller.volumeFrames >= VOLUME_CONFIRM_FRAMES) {
      controller.volumeActive = true
      controller.volumeArmed = false
      controller.volumeAnchorY = palmCenterY(landmarks)
      controller.volumeAccumulator = 0
      return { gestureId: 'volume', state: 'VOLUME', action: 'Volume Ready', cursor }
    }
    return { gestureId: 'volume', state: 'IDLE', action: 'Volume Ready', cursor }
  }
  controller.volumeFrames = 0

  controller.rightHistory.push({ time: now, value: thumbMiddle })
  controller.rightHistory = controller.rightHistory.filter((sample) => now - sample.time <= 300)
  const recentRightMax = controller.rightHistory.reduce((max, sample) => Math.max(max, sample.value), thumbMiddle)
  const rightTap = recentRightMax - thumbMiddle >= 0.1
  const rightDominant = thumbMiddle < thumbIndex * 0.78

  if (controller.rightLatched) {
    if (thumbMiddle > 0.44 || !rightDominant) controller.rightLatched = false
  } else if (!controller.pinchActive && rightDominant && thumbMiddle < 0.32 && rightTap) {
    controller.rightLatched = true
    return { gestureId: 'right', state: 'RIGHT', action: 'Right Click', event: 'right', cursor }
  }

  if (controller.pinchActive) {
    if (thumbIndex > 0.4) {
      const wasDragging = controller.dragging
      controller.pinchActive = false
      controller.dragging = false
      if (wasDragging) {
        return { gestureId: 'drag', state: 'DROP', action: 'Drop', event: 'drop', cursor }
      }

      const isDouble = now - controller.lastClickAt <= 500
        && controller.lastClickPoint
        && distance(cursor, controller.lastClickPoint) <= 0.08
      controller.lastClickAt = now
      controller.lastClickPoint = cursor
      if (isDouble) {
        controller.lastClickPoint = null
        return { gestureId: 'double', state: 'DOUBLE', action: 'Double Click', event: 'double', cursor }
      }
      return { gestureId: 'click', state: 'CLICK', action: 'Click', event: 'click', cursor }
    }

    const pinchMidpoint = {
      x: (1 - landmarks[4].x + 1 - landmarks[8].x) / 2,
      y: (landmarks[4].y + landmarks[8].y) / 2,
    }
    const moved = controller.pinchStartPoint
      ? distance(pinchMidpoint, controller.pinchStartPoint) / palm
      : 0
    if (!controller.dragging && now - controller.pinchStartedAt > 300 && moved > 0.15) {
      controller.dragging = true
    }
    if (controller.dragging) {
      return { gestureId: 'drag', state: 'DRAG', action: 'Dragging', event: 'drag', cursor: pinchMidpoint }
    }
    return { gestureId: 'click', state: 'PINCH', action: 'Pinch', cursor: pinchMidpoint }
  }

  if (thumbIndex < 0.3) {
    controller.pinchActive = true
    controller.pinchStartedAt = now
    controller.pinchStartPoint = {
      x: (1 - landmarks[4].x + 1 - landmarks[8].x) / 2,
      y: (landmarks[4].y + landmarks[8].y) / 2,
    }
    return { gestureId: 'click', state: 'PINCH', action: 'Pinch', cursor: controller.pinchStartPoint }
  }

  const scrollPose = indexExtended && middleExtended && !(ringExtended && pinkyExtended)
  if (scrollPose) {
    const currentY = palmCenterY(landmarks)
    let scrollTicks = 0
    if (controller.scrollAnchorY !== null) {
      const delta = currentY - controller.scrollAnchorY
      if (Math.abs(delta) > 0.006) {
        controller.scrollAccumulator += -delta / 0.018
        scrollTicks = Math.max(-3, Math.min(3, Math.trunc(controller.scrollAccumulator)))
        controller.scrollAccumulator -= scrollTicks
        controller.scrollAnchorY = currentY
      }
    } else {
      controller.scrollAnchorY = currentY
    }
    return {
      gestureId: 'scroll',
      state: 'SCROLL',
      action: scrollTicks > 0 ? 'Scrolling Up' : scrollTicks < 0 ? 'Scrolling Down' : 'Scroll Ready',
      event: scrollTicks ? 'scroll' : undefined,
      scrollTicks,
      cursor,
    }
  }
  controller.scrollAnchorY = null
  controller.scrollAccumulator = 0

  if (indexExtended && !middleExtended) {
    return { gestureId: 'move', state: 'CURSOR', action: 'Move', cursor }
  }

  return { gestureId: 'move', state: 'IDLE', action: 'Idle', cursor }
}

function drawLandmarks(canvas, landmarks) {
  const context = canvas.getContext('2d')
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  const ratio = window.devicePixelRatio || 1
  const targetWidth = Math.max(1, Math.round(width * ratio))
  const targetHeight = Math.max(1, Math.round(height * ratio))
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth
    canvas.height = targetHeight
  }
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  context.clearRect(0, 0, width, height)
  if (!landmarks) return

  context.lineWidth = 2
  context.strokeStyle = 'rgba(73, 242, 177, 0.88)'
  context.shadowBlur = 8
  context.shadowColor = 'rgba(73, 242, 177, 0.45)'
  for (const [from, to] of HAND_CONNECTIONS) {
    context.beginPath()
    context.moveTo((1 - landmarks[from].x) * width, landmarks[from].y * height)
    context.lineTo((1 - landmarks[to].x) * width, landmarks[to].y * height)
    context.stroke()
  }

  context.shadowBlur = 10
  for (let index = 0; index < landmarks.length; index += 1) {
    const landmark = landmarks[index]
    const x = (1 - landmark.x) * width
    const y = landmark.y * height
    context.beginPath()
    context.arc(x, y, index === 8 ? 5.5 : 3.6, 0, Math.PI * 2)
    context.fillStyle = index === 8 ? '#ffffff' : '#49f2b1'
    context.fill()
  }
  context.shadowBlur = 0
}

function clearCanvas(canvas) {
  if (!canvas) return
  const context = canvas.getContext('2d')
  context.clearRect(0, 0, canvas.width, canvas.height)
}

export function useHandTracking(onGesture) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const cursorRef = useRef(null)
  const streamRef = useRef(null)
  const landmarkerRef = useRef(null)
  const animationFrameRef = useRef(0)
  const onGestureRef = useRef(onGesture)
  const controllerRef = useRef(createControllerState())
  const lastVideoTimeRef = useRef(-1)
  const lastUiKeyRef = useRef('')
  const fpsRef = useRef({ frames: 0, startedAt: performance.now(), current: 0 })
  const feedbackSequenceRef = useRef(0)
  const scrollFeedbackRef = useRef(50)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [snapshot, setSnapshot] = useState(INITIAL_SNAPSHOT)
  const [feedback, setFeedback] = useState({ type: '', sequence: 0, x: 50, y: 50, scroll: 50, volumeDelta: 0 })

  onGestureRef.current = onGesture

  const stop = useCallback(() => {
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
    animationFrameRef.current = 0
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    landmarkerRef.current?.close?.()
    landmarkerRef.current = null
    clearCanvas(canvasRef.current)
    resetController(controllerRef.current)
    lastVideoTimeRef.current = -1
    lastUiKeyRef.current = ''
    if (cursorRef.current) cursorRef.current.style.opacity = '0'
    setSnapshot(INITIAL_SNAPSHOT)
    setFeedback({ type: '', sequence: 0, x: 50, y: 50, scroll: 50, volumeDelta: 0 })
    setStatus('idle')
  }, [])

  const start = useCallback(async () => {
    if (status === 'loading' || status === 'running') return
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('当前浏览器不支持摄像头访问，请使用最新版 Edge 或 Chrome。')
      setStatus('error')
      return
    }

    setStatus('loading')
    setError('')
    try {
      const [{ FilesetResolver, HandLandmarker }, stream] = await Promise.all([
        import('@mediapipe/tasks-vision'),
        navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: false,
        }),
      ])

      streamRef.current = stream
      const video = videoRef.current
      video.srcObject = stream
      await video.play()

      const wasmRoot = new URL('wasm', document.baseURI).href.replace(/\/$/, '')
      const modelPath = new URL('models/hand_landmarker.task', document.baseURI).href
      const vision = await FilesetResolver.forVisionTasks(wasmRoot)
      const options = {
        baseOptions: { modelAssetPath: modelPath, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numHands: 1,
        minHandDetectionConfidence: 0.65,
        minHandPresenceConfidence: 0.55,
        minTrackingConfidence: 0.5,
      }

      try {
        landmarkerRef.current = await HandLandmarker.createFromOptions(vision, options)
      } catch {
        landmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
          ...options,
          baseOptions: { modelAssetPath: modelPath, delegate: 'CPU' },
        })
      }

      fpsRef.current = { frames: 0, startedAt: performance.now(), current: 0 }
      setStatus('running')

      const renderLoop = () => {
        const currentVideo = videoRef.current
        const canvas = canvasRef.current
        const landmarker = landmarkerRef.current
        if (!currentVideo || !canvas || !landmarker || !streamRef.current) return

        if (currentVideo.readyState >= 2 && currentVideo.currentTime !== lastVideoTimeRef.current) {
          lastVideoTimeRef.current = currentVideo.currentTime
          const now = performance.now()
          const result = landmarker.detectForVideo(currentVideo, now)
          const landmarks = result.landmarks?.[0]
          drawLandmarks(canvas, landmarks)

          fpsRef.current.frames += 1
          const elapsed = now - fpsRef.current.startedAt
          let fps = fpsRef.current.current
          if (elapsed >= 500) {
            fps = Math.round((fpsRef.current.frames * 1000) / elapsed)
            fpsRef.current = { frames: 0, startedAt: now, current: fps }
          }

          if (landmarks) {
            const gesture = classifyGesture(landmarks, now, controllerRef.current)
            const handedness = result.handednesses?.[0]?.[0]
            const cursorX = Math.max(0, Math.min(1, gesture.cursor.x))
            const cursorY = Math.max(0, Math.min(1, gesture.cursor.y))
            if (cursorRef.current) {
              cursorRef.current.style.opacity = '1'
              cursorRef.current.style.left = `${cursorX * 100}%`
              cursorRef.current.style.top = `${cursorY * 100}%`
              cursorRef.current.dataset.dragging = gesture.event === 'drag' ? 'true' : 'false'
            }

            const uiKey = `${gesture.gestureId}:${gesture.state}:${gesture.action}:${fps}`
            if (uiKey !== lastUiKeyRef.current) {
              lastUiKeyRef.current = uiKey
              setSnapshot({
                gestureId: gesture.gestureId,
                state: gesture.state,
                action: gesture.action,
                fps,
                hands: 1,
                handedness: handedness?.categoryName ?? '',
                confidence: handedness?.score ?? 0,
              })
              onGestureRef.current?.(gesture)
            }

            if (gesture.event && gesture.event !== 'drag') {
              if (gesture.event === 'scroll') {
                scrollFeedbackRef.current = Math.max(8, Math.min(92, scrollFeedbackRef.current + gesture.scrollTicks * 3))
              }
              feedbackSequenceRef.current += 1
              setFeedback({
                type: gesture.event,
                sequence: feedbackSequenceRef.current,
                x: cursorX * 100,
                y: cursorY * 100,
                scroll: scrollFeedbackRef.current,
                volumeDelta: gesture.volumeSteps ?? 0,
              })
            }
          } else {
            if (cursorRef.current) cursorRef.current.style.opacity = '0'
            const uiKey = `no-hand:${fps}`
            if (uiKey !== lastUiKeyRef.current) {
              lastUiKeyRef.current = uiKey
              setSnapshot((current) => ({ ...current, state: 'NO HAND', action: 'No Hand', fps, hands: 0, handedness: '', confidence: 0 }))
            }
          }
        }
        animationFrameRef.current = requestAnimationFrame(renderLoop)
      }
      animationFrameRef.current = requestAnimationFrame(renderLoop)
    } catch (cameraError) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      const message = cameraError?.name === 'NotAllowedError'
        ? '摄像头权限被拒绝，请在浏览器地址栏中允许摄像头后重试。'
        : cameraError?.name === 'NotFoundError'
          ? '没有检测到可用摄像头。'
          : `摄像头启动失败：${cameraError?.message ?? '未知错误'}`
      setError(message)
      setStatus('error')
    }
  }, [status])

  useEffect(() => stop, [stop])

  return {
    videoRef,
    canvasRef,
    cursorRef,
    status,
    error,
    snapshot,
    feedback,
    start,
    stop,
  }
}
