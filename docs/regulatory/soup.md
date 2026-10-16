# SOUP (Software of Unknown Provenance)

Third-party components used by this demo. Versions are pinned in lockfiles (`uv.lock`, `package-lock.json`) at build time.

| Component | Role | License (typical) | Risk | Justification / control |
|-----------|------|-------------------|------|-------------------------|
| pydicom | DICOM parse | MIT | Medium — tag/VR edge cases | Unit tests on fixtures; pin major version |
| nibabel | NIfTI I/O | MIT | Medium — affine/header | Round-trip tests; pin version |
| numpy | Arrays | BSD | Low | Ubiquitous; pin version |
| FastAPI / Starlette / Uvicorn | HTTP API | MIT | Low | OpenAPI smoke; pin versions |
| Pydantic | Request/response models | MIT | Low | Schema validation |
| React / Vite | SPA | MIT | Low | Build-time typecheck |
| three / @react-three/fiber / drei | 3D viewer | MIT | Medium — graphics correctness | Manual visual checks; disclaimer on units |
| nginx | Static + reverse proxy (Docker) | BSD-2 | Low | Official image; proxy `/api` only |

**Anomaly handling:** Dependency CVEs reviewed before demo releases; upgrade via lockfile refresh. No runtime auto-update of SOUP in the demo image.
