import { Canvas, useThree } from '@react-three/fiber'
import type { ThreeEvent } from '@react-three/fiber'
import { Center, Line, OrbitControls, useGLTF } from '@react-three/drei'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from 'react'
import * as THREE from 'three'

// Served from frontend/public (avoids stale API/browser cache of a broken GLB).
const MESH_URL = '/meshes/bone.glb'

type MeasurePoint = {
  position: THREE.Vector3
}

type BoneMeshProps = {
  clipX: number
  clipY: number
  clipEnabled: boolean
  measureMode: boolean
  onMeasureHit: (point: THREE.Vector3) => void
}

function BoneMesh({
  clipX,
  clipY,
  clipEnabled,
  measureMode,
  onMeasureHit,
}: BoneMeshProps) {
  const { scene } = useGLTF(MESH_URL)
  const cloned = useMemo(() => scene.clone(true), [scene])

  const planes = useMemo(() => {
    const px = new THREE.Plane(new THREE.Vector3(-1, 0, 0), clipX)
    const py = new THREE.Plane(new THREE.Vector3(0, -1, 0), clipY)
    return [px, py]
  }, [clipX, clipY])

  useEffect(() => {
    cloned.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        const materials = Array.isArray(obj.material)
          ? obj.material
          : [obj.material]
        for (const mat of materials) {
          if (mat && 'clippingPlanes' in mat) {
            const m = mat as THREE.MeshStandardMaterial
            m.clippingPlanes = clipEnabled ? planes : []
            m.clipShadows = true
            m.side = THREE.DoubleSide
            m.needsUpdate = true
          }
        }
      }
    })
  }, [cloned, planes, clipEnabled])

  const handleClick = useCallback(
    (event: ThreeEvent<MouseEvent>) => {
      if (!measureMode) return
      event.stopPropagation()
      onMeasureHit(event.point.clone())
    },
    [measureMode, onMeasureHit],
  )

  return (
    <Center>
      <primitive
        object={cloned}
        onClick={handleClick}
        onPointerOver={() => {
          document.body.style.cursor = measureMode ? 'crosshair' : 'grab'
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'default'
        }}
      />
    </Center>
  )
}

function MeasureOverlay({
  points,
}: {
  points: MeasurePoint[]
}) {
  if (points.length === 0) return null

  return (
    <group>
      {points.map((p, i) => (
        <mesh key={i} position={p.position}>
          <sphereGeometry args={[0.25, 16, 16]} />
          <meshBasicMaterial color={i === 0 ? '#3db8a0' : '#d4a24c'} />
        </mesh>
      ))}
      {points.length === 2 && (
        <Line
          points={[points[0].position, points[1].position]}
          color="#e6eef4"
          lineWidth={2}
        />
      )}
    </group>
  )
}

function ClippingSetup({ enabled }: { enabled: boolean }) {
  const { gl } = useThree()
  useEffect(() => {
    gl.localClippingEnabled = enabled
  }, [gl, enabled])
  return null
}

function SceneContent({
  clipX,
  clipY,
  clipEnabled,
  measureMode,
  points,
  onMeasureHit,
  controlsRef,
}: {
  clipX: number
  clipY: number
  clipEnabled: boolean
  measureMode: boolean
  points: MeasurePoint[]
  onMeasureHit: (point: THREE.Vector3) => void
  controlsRef: MutableRefObject<unknown>
}) {
  return (
    <>
      <ClippingSetup enabled={clipEnabled} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[8, 12, 6]} intensity={1.1} />
      <directionalLight position={[-6, -4, -8]} intensity={0.35} />
      <BoneMesh
        clipX={clipX}
        clipY={clipY}
        clipEnabled={clipEnabled}
        measureMode={measureMode}
        onMeasureHit={onMeasureHit}
      />
      <MeasureOverlay points={points} />
      <OrbitControls
        ref={controlsRef as never}
        enableDamping
        makeDefault
        enabled={!measureMode}
      />
      <gridHelper args={[24, 24, '#2a3a48', '#1a2630']} position={[0, -7.2, 0]} />
    </>
  )
}

export function MeshViewer() {
  const [clipEnabled, setClipEnabled] = useState(true)
  const [clipX, setClipX] = useState(0)
  const [clipY, setClipY] = useState(8)
  const [measureMode, setMeasureMode] = useState(false)
  const [points, setPoints] = useState<MeasurePoint[]>([])
  const controlsRef = useRef(null)

  const distanceMm =
    points.length === 2 ? points[0].position.distanceTo(points[1].position) : null

  const onMeasureHit = useCallback((point: THREE.Vector3) => {
    setPoints((prev) => {
      if (prev.length === 0) return [{ position: point }]
      if (prev.length === 1) return [prev[0], { position: point }]
      return [{ position: point }]
    })
  }, [])

  return (
    <section className="panel mesh-panel">
      <div className="panel-header">
        <h2>Bone mesh</h2>
        <span className="muted mono">glTF · clip + measure</span>
      </div>

      <div className="mesh-stage">
        <Canvas
          camera={{ position: [16, 12, 16], fov: 42, near: 0.1, far: 200 }}
          gl={{ antialias: true, localClippingEnabled: true }}
        >
          <color attach="background" args={['#05080c']} />
          <SceneContent
            clipX={clipX}
            clipY={clipY}
            clipEnabled={clipEnabled}
            measureMode={measureMode}
            points={points}
            onMeasureHit={onMeasureHit}
            controlsRef={controlsRef}
          />
        </Canvas>
      </div>

      <div className="controls mesh-controls">
        <label className="check-row">
          <input
            type="checkbox"
            checked={clipEnabled}
            onChange={(e) => setClipEnabled(e.target.checked)}
          />
          <span>Clipping planes</span>
        </label>
        <label>
          <span>Clip X ({clipX.toFixed(1)})</span>
          <input
            type="range"
            min={-8}
            max={8}
            step={0.1}
            value={clipX}
            disabled={!clipEnabled}
            onChange={(e) => setClipX(Number(e.target.value))}
          />
        </label>
        <label>
          <span>Clip Y ({clipY.toFixed(1)})</span>
          <input
            type="range"
            min={-8}
            max={8}
            step={0.1}
            value={clipY}
            disabled={!clipEnabled}
            onChange={(e) => setClipY(Number(e.target.value))}
          />
        </label>

        <div className="wl-presets">
          <button
            type="button"
            className={measureMode ? 'active' : ''}
            onClick={() => setMeasureMode((v) => !v)}
          >
            {measureMode ? 'Measuring…' : 'Measure distance'}
          </button>
          <button
            type="button"
            onClick={() => {
              setPoints([])
              setMeasureMode(false)
            }}
          >
            Clear measure
          </button>
        </div>

        {measureMode && (
          <p className="hint">
            Click two points on the mesh. Orbit is paused while measuring.
          </p>
        )}
        {distanceMm !== null && (
          <p className="measure-result mono">
            Distance: {distanceMm.toFixed(2)} mesh units
          </p>
        )}
        <p className="hint">
          Demo mesh units are millimetre-like but not patient-space cm from the
          CT. Co-registered surgical planning would map mesh ↔ DICOM LPS/RAS
          carefully — a classic orientation failure mode.
        </p>
      </div>
    </section>
  )
}

useGLTF.preload(MESH_URL)
