import { Canvas, useFrame } from '@react-three/fiber'
import type { ThreeEvent } from '@react-three/fiber'
import {
  ContactShadows,
  Environment,
  Line,
  OrbitControls,
  useGLTF,
} from '@react-three/drei'
import {
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from 'react'
import * as THREE from 'three'
import { FullscreenButton } from './FullscreenButton'
import { usePanelFullscreen } from '../hooks/usePanelFullscreen'

const MESH_URL = '/meshes/bone.glb?v=femur-axis-z1'

// Femur GLB long axis is +Z (see fixtures bbox). Clips + shading use that.
const LONG_AXIS = new THREE.Vector3(0, 0, 1)
/** Keep planes just outside the mesh so the full bone stays visible. */
const EDGE_MARGIN = 0.08

type MeasurePoint = { position: THREE.Vector3 }

/** Clip slider limits derived from mesh AABB (axial=Z, long=X). */
export type BoneClipBounds = {
  axialMin: number
  axialMax: number
  axialCenter: number
  longMin: number
  longMax: number
  longCenter: number
}

function boundsFromGeometry(geometry: THREE.BufferGeometry): BoneClipBounds {
  geometry.computeBoundingBox()
  const bb = geometry.boundingBox ?? new THREE.Box3(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1))
  const padZ = Math.max((bb.max.z - bb.min.z) * EDGE_MARGIN, 0.15)
  const padX = Math.max((bb.max.x - bb.min.x) * EDGE_MARGIN, 0.1)
  return {
    axialMin: bb.min.z - padZ,
    axialMax: bb.max.z + padZ,
    axialCenter: 0.5 * (bb.min.z + bb.max.z),
    longMin: bb.min.x - padX,
    longMax: bb.max.x + padX,
    longCenter: 0.5 * (bb.min.x + bb.max.x),
  }
}

/** Park both planes at the far edges (full bone visible with clipping on). */
function edgeParkedClips(b: BoneClipBounds): { axial: number; long: number } {
  return { axial: b.axialMax, long: b.longMax }
}

type SectionUniforms = {
  uCenter: { value: THREE.Vector3 }
  uRadius: { value: number }
  uHalfLen: { value: number }
}

/**
 * Section fill uses distance from the shaft axis (Z), so axial cuts show a
 * cortex ring and longitudinal cuts show cortex bands — not a stamped circle.
 */
function createBoneSectionMaterial(
  otherPlanes: THREE.Plane[],
  center: THREE.Vector3,
  radius: number,
  halfLen: number,
): THREE.MeshStandardMaterial {
  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color('#e8d7c0'),
    roughness: 0.85,
    metalness: 0.0,
    clippingPlanes: otherPlanes,
    clipShadows: true,
    stencilWrite: true,
    stencilRef: 0,
    stencilFunc: THREE.NotEqualStencilFunc,
    stencilFail: THREE.ReplaceStencilOp,
    stencilZFail: THREE.ReplaceStencilOp,
    stencilZPass: THREE.ReplaceStencilOp,
  })

  const sectionUniforms: SectionUniforms = {
    uCenter: { value: center.clone() },
    uRadius: { value: Math.max(radius, 0.5) },
    uHalfLen: { value: Math.max(halfLen, 1) },
  }
  ;(mat.userData as { sectionUniforms: SectionUniforms }).sectionUniforms =
    sectionUniforms

  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, sectionUniforms)

    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        /* glsl */ `
        #include <common>
        varying vec3 vWorldPos;
        `,
      )
      .replace(
        '#include <worldpos_vertex>',
        /* glsl */ `
        #include <worldpos_vertex>
        vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        `,
      )

    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        /* glsl */ `
        #include <common>
        varying vec3 vWorldPos;
        uniform vec3 uCenter;
        uniform float uRadius;
        uniform float uHalfLen;

        float hash31(vec3 p) {
          p = fract(p * 0.1031);
          p += dot(p, p.yzx + 33.33);
          return fract((p.x + p.y) * p.z);
        }

        float valueNoise3(vec3 p) {
          vec3 i = floor(p);
          vec3 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          float n000 = hash31(i);
          float n100 = hash31(i + vec3(1.0, 0.0, 0.0));
          float n010 = hash31(i + vec3(0.0, 1.0, 0.0));
          float n110 = hash31(i + vec3(1.0, 1.0, 0.0));
          float n001 = hash31(i + vec3(0.0, 0.0, 1.0));
          float n101 = hash31(i + vec3(1.0, 0.0, 1.0));
          float n011 = hash31(i + vec3(0.0, 1.0, 1.0));
          float n111 = hash31(i + vec3(1.0, 1.0, 1.0));
          float nx00 = mix(n000, n100, f.x);
          float nx10 = mix(n010, n110, f.x);
          float nx01 = mix(n001, n101, f.x);
          float nx11 = mix(n011, n111, f.x);
          return mix(mix(nx00, nx10, f.y), mix(nx01, nx11, f.y), f.z);
        }

        float trabeculae3(vec3 p) {
          float n1 = valueNoise3(p * 2.8);
          float n2 = valueNoise3(p * 5.6 + 9.0);
          float n3 = valueNoise3(p * 11.0 - 4.0);
          float lattice = smoothstep(0.32, 0.78, n1) * smoothstep(0.28, 0.82, n2);
          float pores = smoothstep(0.5, 0.95, n3);
          return clamp(lattice * 0.7 + pores * 0.4, 0.0, 1.0);
        }
        `,
      )
      .replace(
        '#include <color_fragment>',
        /* glsl */ `
        #include <color_fragment>
        // Anatomical frame: long axis = +Z for this femur asset
        vec3 rel = vWorldPos - uCenter;
        float along = rel.z;
        vec2 radial = rel.xy;
        float r = length(radial) / max(uRadius, 0.001);

        float t = clamp(0.5 + along / (uHalfLen * 2.0), 0.0, 1.0);
        float epiphysis = 1.0 - (smoothstep(0.0, 0.22, t) * smoothstep(1.0, 0.78, t));
        float shaft = 1.0 - epiphysis;

        float localRadius = mix(1.0, 1.5, epiphysis);
        r /= localRadius;

        vec3 vol = vec3(radial.x, radial.y, along);

        float cortexStart = mix(0.55, 0.78, shaft);
        float cortex = smoothstep(cortexStart, 0.97, r);
        float endosteum = smoothstep(cortexStart - 0.22, cortexStart, r);

        vec3 cortexColor = vec3(0.93, 0.87, 0.77);
        vec3 endosteumColor = vec3(0.80, 0.64, 0.54);
        vec3 marrowDark = mix(vec3(0.58, 0.30, 0.24), vec3(0.42, 0.20, 0.16), shaft);
        vec3 marrowLight = vec3(0.84, 0.60, 0.50);
        vec3 trabecula = vec3(0.91, 0.82, 0.72);

        float trab = trabeculae3(vol * mix(1.3, 2.1, epiphysis) + 3.0);
        trab = mix(trab * 0.5 + 0.12, trab, epiphysis);
        vec3 marrow = mix(marrowDark, marrowLight, trab * 0.7);
        marrow = mix(marrow, trabecula, smoothstep(0.5, 0.95, trab) * mix(0.2, 0.55, epiphysis));

        float rings = 0.5 + 0.5 * sin(r * 58.0 + valueNoise3(vol * 0.4) * 5.0);
        cortexColor = mix(cortexColor, vec3(0.84, 0.74, 0.62), rings * 0.28 * shaft);

        vec3 section = mix(marrow, endosteumColor, endosteum * 0.5);
        section = mix(section, cortexColor, cortex);

        float canal = (1.0 - smoothstep(0.0, mix(0.08, 0.2, shaft), r)) * shaft;
        section = mix(section, marrowDark * 0.65, canal * 0.55);

        diffuseColor.rgb = section;
        `,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        /* glsl */ `
        #include <roughnessmap_fragment>
        vec2 rad = (vWorldPos - uCenter).xy;
        float rR = length(rad) / max(uRadius, 0.001);
        roughnessFactor = mix(0.95, 0.5, smoothstep(0.65, 0.95, rR));
        `,
      )
  }

  mat.customProgramCacheKey = () => 'bone-section-shaft-z-v1'
  return mat
}

function createPlaneStencilGroup(
  geometry: THREE.BufferGeometry,
  plane: THREE.Plane,
  renderOrder: number,
): THREE.Group {
  const group = new THREE.Group()
  const baseMat = new THREE.MeshBasicMaterial()
  baseMat.depthWrite = false
  baseMat.depthTest = false
  baseMat.colorWrite = false
  baseMat.stencilWrite = true
  baseMat.stencilFunc = THREE.AlwaysStencilFunc

  const matBack = baseMat.clone()
  matBack.side = THREE.BackSide
  matBack.clippingPlanes = [plane]
  matBack.stencilFail = THREE.IncrementWrapStencilOp
  matBack.stencilZFail = THREE.IncrementWrapStencilOp
  matBack.stencilZPass = THREE.IncrementWrapStencilOp
  const meshBack = new THREE.Mesh(geometry, matBack)
  meshBack.renderOrder = renderOrder
  meshBack.raycast = () => undefined
  group.add(meshBack)

  const matFront = baseMat.clone()
  matFront.side = THREE.FrontSide
  matFront.clippingPlanes = [plane]
  matFront.stencilFail = THREE.DecrementWrapStencilOp
  matFront.stencilZFail = THREE.DecrementWrapStencilOp
  matFront.stencilZPass = THREE.DecrementWrapStencilOp
  const meshFront = new THREE.Mesh(geometry, matFront)
  meshFront.renderOrder = renderOrder
  meshFront.raycast = () => undefined
  group.add(meshFront)

  return group
}

function extractGeometry(scene: THREE.Object3D): THREE.BufferGeometry {
  const geoms: THREE.BufferGeometry[] = []
  scene.updateMatrixWorld(true)
  scene.traverse((obj) => {
    if (obj instanceof THREE.Mesh && obj.geometry) {
      const g = obj.geometry.clone()
      g.applyMatrix4(obj.matrixWorld)
      geoms.push(g)
    }
  })
  if (geoms.length === 0) return new THREE.BoxGeometry(1, 1, 1)
  if (geoms.length === 1) return geoms[0]

  const positions: number[] = []
  const normals: number[] = []
  const indices: number[] = []
  let indexOffset = 0
  for (const geom of geoms) {
    const pos = geom.getAttribute('position')
    const nrm = geom.getAttribute('normal')
    if (!pos) continue
    for (let i = 0; i < pos.count; i++) {
      positions.push(pos.getX(i), pos.getY(i), pos.getZ(i))
      if (nrm) normals.push(nrm.getX(i), nrm.getY(i), nrm.getZ(i))
      else normals.push(0, 1, 0)
    }
    const idx = geom.getIndex()
    if (idx) {
      for (let i = 0; i < idx.count; i++) indices.push(idx.getX(i) + indexOffset)
    } else {
      for (let i = 0; i < pos.count; i++) indices.push(i + indexOffset)
    }
    indexOffset += pos.count
  }
  const merged = new THREE.BufferGeometry()
  merged.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  merged.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
  merged.setIndex(indices)
  merged.computeBoundingBox()
  merged.computeBoundingSphere()
  return merged
}

function SolidClippedBone({
  clipAxial,
  clipLong,
  clipEnabled,
  measureMode,
  onMeasureHit,
  onBounds,
}: {
  clipAxial: number
  clipLong: number
  clipEnabled: boolean
  measureMode: boolean
  onMeasureHit: (point: THREE.Vector3) => void
  onBounds: (bounds: BoneClipBounds) => void
}) {
  const { scene } = useGLTF(MESH_URL)
  const rootRef = useRef<THREE.Group>(null)
  const capAxialRef = useRef<THREE.Mesh>(null)
  const capLongRef = useRef<THREE.Mesh>(null)

  const geometry = useMemo(() => extractGeometry(scene), [scene])

  useLayoutEffect(() => {
    onBounds(boundsFromGeometry(geometry))
  }, [geometry, onBounds])

  // 0 = axial (⊥ Z shaft), 1 = longitudinal (⊥ X)
  const planes = useMemo(
    () => [
      new THREE.Plane(new THREE.Vector3(0, 0, -1), 0),
      new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0),
    ],
    [],
  )

  planes[0].constant = clipAxial
  planes[1].constant = clipLong

  useLayoutEffect(() => {
    const root = rootRef.current
    if (!root) return

    while (root.children.length) root.remove(root.children[0])
    capAxialRef.current = null
    capLongRef.current = null

    if (!clipEnabled) {
      const mat = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color('#e6d3b8'),
        roughness: 0.55,
        metalness: 0,
        clearcoat: 0.15,
        clearcoatRoughness: 0.6,
        sheen: 0.3,
        sheenColor: new THREE.Color('#f3e6d4'),
        side: THREE.DoubleSide,
      })
      const mesh = new THREE.Mesh(geometry, mat)
      mesh.castShadow = true
      mesh.receiveShadow = true
      root.add(mesh)
      return
    }

    geometry.computeBoundingBox()
    geometry.computeBoundingSphere()
    const center = geometry.boundingSphere?.center.clone() ?? new THREE.Vector3()
    const bb = geometry.boundingBox!
    // Shaft radius from X/Y extents (long axis is Z)
    const shaftRadius =
      0.5 * Math.max(bb.max.x - bb.min.x, bb.max.y - bb.min.y) * 0.92
    const halfLen = 0.5 * (bb.max.z - bb.min.z)

    for (let i = 0; i < planes.length; i++) {
      const stencil = createPlaneStencilGroup(geometry, planes[i], i + 1)
      root.add(stencil)

      const otherPlanes = planes.filter((_, j) => j !== i)
      const capMat = createBoneSectionMaterial(
        otherPlanes,
        center,
        shaftRadius,
        halfLen,
      )
      const cap = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), capMat)
      cap.renderOrder = i + 1.1
      cap.onAfterRender = (renderer) => {
        renderer.clearStencil()
      }
      if (i === 0) capAxialRef.current = cap
      else capLongRef.current = cap
      root.add(cap)
    }

    const boneMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color('#e6d3b8'),
      roughness: 0.55,
      metalness: 0,
      clearcoat: 0.12,
      clearcoatRoughness: 0.65,
      sheen: 0.25,
      sheenColor: new THREE.Color('#f3e6d4'),
      clippingPlanes: planes,
      clipShadows: true,
      shadowSide: THREE.DoubleSide,
      side: THREE.FrontSide,
    })
    const bone = new THREE.Mesh(geometry, boneMat)
    bone.castShadow = true
    bone.receiveShadow = true
    bone.renderOrder = 6
    root.add(bone)
  }, [geometry, clipEnabled, planes])

  useFrame(() => {
    if (!clipEnabled) return
    const caps = [capAxialRef.current, capLongRef.current]
    for (let i = 0; i < planes.length; i++) {
      const po = caps[i]
      if (!po) continue
      const plane = planes[i]
      plane.coplanarPoint(po.position)
      po.lookAt(
        po.position.x - plane.normal.x,
        po.position.y - plane.normal.y,
        po.position.z - plane.normal.z,
      )
    }
  })

  const handleClick = useCallback(
    (event: ThreeEvent<MouseEvent>) => {
      if (!measureMode) return
      event.stopPropagation()
      onMeasureHit(event.point.clone())
    },
    [measureMode, onMeasureHit],
  )

  return (
    <group
      ref={rootRef}
      onClick={handleClick}
      onPointerOver={() => {
        document.body.style.cursor = measureMode ? 'crosshair' : 'grab'
      }}
      onPointerOut={() => {
        document.body.style.cursor = 'default'
      }}
    />
  )
}

function MeasureOverlay({ points }: { points: MeasurePoint[] }) {
  if (points.length === 0) return null
  return (
    <group>
      {points.map((p, i) => (
        <mesh key={i} position={p.position}>
          <sphereGeometry args={[0.18, 20, 20]} />
          <meshStandardMaterial
            color={i === 0 ? '#3db8a0' : '#d4a24c'}
            emissive={i === 0 ? '#146058' : '#6a4a10'}
            emissiveIntensity={0.35}
            roughness={0.35}
          />
        </mesh>
      ))}
      {points.length === 2 && (
        <Line
          points={[points[0].position, points[1].position]}
          color="#f2f6f8"
          lineWidth={2}
        />
      )}
    </group>
  )
}

function SceneContent({
  clipAxial,
  clipLong,
  clipEnabled,
  measureMode,
  points,
  onMeasureHit,
  onBounds,
  controlsRef,
}: {
  clipAxial: number
  clipLong: number
  clipEnabled: boolean
  measureMode: boolean
  points: MeasurePoint[]
  onMeasureHit: (point: THREE.Vector3) => void
  onBounds: (bounds: BoneClipBounds) => void
  controlsRef: MutableRefObject<unknown>
}) {
  return (
    <>
      <hemisphereLight args={['#f7f1e8', '#1a222c', 0.55]} />
      <directionalLight
        castShadow
        position={[10, 16, 8]}
        intensity={1.35}
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0002}
      />
      <directionalLight position={[-8, 4, -6]} intensity={0.35} color="#9eb6ff" />
      <Environment preset="warehouse" />
      <SolidClippedBone
        clipAxial={clipAxial}
        clipLong={clipLong}
        clipEnabled={clipEnabled}
        measureMode={measureMode}
        onMeasureHit={onMeasureHit}
        onBounds={onBounds}
      />
      <MeasureOverlay points={points} />
      <ContactShadows
        position={[0, -9.4, 0]}
        opacity={0.5}
        scale={30}
        blur={2.8}
        far={22}
      />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -9.45, 0]} receiveShadow>
        <circleGeometry args={[14, 64]} />
        <meshStandardMaterial color="#121820" roughness={0.95} metalness={0.05} />
      </mesh>
      <OrbitControls
        ref={controlsRef as never}
        enableDamping
        dampingFactor={0.06}
        makeDefault
        enabled={!measureMode}
        minDistance={6}
        maxDistance={40}
      />
    </>
  )
}

export function MeshViewer() {
  const [clipEnabled, setClipEnabled] = useState(false)
  const [bounds, setBounds] = useState<BoneClipBounds | null>(null)
  const [clipAxial, setClipAxial] = useState(0)
  const [clipLong, setClipLong] = useState(0)
  const [measureMode, setMeasureMode] = useState(false)
  const [points, setPoints] = useState<MeasurePoint[]>([])
  const controlsRef = useRef(null)
  const boundsReady = useRef(false)
  const { active: fullscreen, toggle: toggleFullscreen } = usePanelFullscreen()

  const distanceMm =
    points.length === 2 ? points[0].position.distanceTo(points[1].position) : null

  const onMeasureHit = useCallback((point: THREE.Vector3) => {
    setPoints((prev) => {
      if (prev.length === 0) return [{ position: point }]
      if (prev.length === 1) return [prev[0], { position: point }]
      return [{ position: point }]
    })
  }, [])

  const onBounds = useCallback((next: BoneClipBounds) => {
    setBounds(next)
    // First time we know the mesh size: park planes at the edges (full bone).
    if (!boundsReady.current) {
      boundsReady.current = true
      const parked = edgeParkedClips(next)
      setClipAxial(parked.axial)
      setClipLong(parked.long)
    }
  }, [])

  const axialMin = bounds?.axialMin ?? -9
  const axialMax = bounds?.axialMax ?? 9
  const longMin = bounds?.longMin ?? -4
  const longMax = bounds?.longMax ?? 4

  return (
    <section className={`panel mesh-panel${fullscreen ? ' is-fullscreen' : ''}`}>
      <div className="panel-header">
        <h2>Bone mesh</h2>
        <div className="panel-header-actions">
          <span className="muted mono">femur · axial / long</span>
          <FullscreenButton active={fullscreen} onToggle={toggleFullscreen} />
        </div>
      </div>

      <div className="mesh-stage">
        <Canvas
          shadows
          camera={{ position: [16, 5, 6], fov: 38, near: 0.1, far: 200 }}
          gl={{
            antialias: true,
            stencil: true,
            localClippingEnabled: true,
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.08,
          }}
          onCreated={({ gl }) => {
            gl.localClippingEnabled = true
          }}
        >
          <color attach="background" args={['#070b10']} />
          <fog attach="fog" args={['#070b10', 26, 65]} />
          <SceneContent
            clipAxial={clipAxial}
            clipLong={clipLong}
            clipEnabled={clipEnabled}
            measureMode={measureMode}
            points={points}
            onMeasureHit={onMeasureHit}
            onBounds={onBounds}
            controlsRef={controlsRef}
          />
        </Canvas>
      </div>

      <div className="controls mesh-controls">
        <label className="check-row">
          <input
            type="checkbox"
            checked={clipEnabled}
            onChange={(e) => {
              const on = e.target.checked
              setClipEnabled(on)
              if (on && bounds) {
                const parked = edgeParkedClips(bounds)
                setClipAxial(parked.axial)
                setClipLong(parked.long)
              }
            }}
          />
          <span>Clipping planes</span>
        </label>
        <div className="wl-presets">
          <button
            type="button"
            onClick={() => {
              setClipEnabled(false)
              if (bounds) {
                const parked = edgeParkedClips(bounds)
                setClipAxial(parked.axial)
                setClipLong(parked.long)
              }
            }}
          >
            Show full bone
          </button>
          <button
            type="button"
            disabled={!bounds}
            onClick={() => {
              if (!bounds) return
              setClipEnabled(true)
              setClipAxial(bounds.axialCenter)
              setClipLong(bounds.longMax)
            }}
          >
            Mid-shaft cut
          </button>
        </div>
        <label>
          <span>
            Axial (⊥ shaft) · {clipAxial.toFixed(1)}
            {bounds && (
              <span className="muted">
                {' '}
                [{axialMin.toFixed(1)} … {axialMax.toFixed(1)}]
              </span>
            )}
          </span>
          <input
            type="range"
            min={axialMin}
            max={axialMax}
            step={0.05}
            value={Math.min(axialMax, Math.max(axialMin, clipAxial))}
            disabled={!clipEnabled || !bounds}
            onChange={(e) => setClipAxial(Number(e.target.value))}
          />
        </label>
        <label>
          <span>
            Longitudinal (side) · {clipLong.toFixed(1)}
            {bounds && (
              <span className="muted">
                {' '}
                [{longMin.toFixed(1)} … {longMax.toFixed(1)}]
              </span>
            )}
          </span>
          <input
            type="range"
            min={longMin}
            max={longMax}
            step={0.05}
            value={Math.min(longMax, Math.max(longMin, clipLong))}
            disabled={!clipEnabled || !bounds}
            onChange={(e) => setClipLong(Number(e.target.value))}
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
          Slider ranges follow the mesh bounding box (with a small edge margin).
          Planes park at the bone edges until you drag them. Axial ⊥ shaft (Z);
          longitudinal ⊥ X. Fill uses distance from the shaft axis
          {` (${LONG_AXIS.x},${LONG_AXIS.y},${LONG_AXIS.z})`}.
        </p>
      </div>
    </section>
  )
}

useGLTF.preload(MESH_URL)
