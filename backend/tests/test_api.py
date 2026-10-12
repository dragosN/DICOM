"""API ingest, validation report, slice PNG, NIfTI download."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import studies as studies_routes
from app.store import StudyStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"
MESH = ROOT / "fixtures" / "meshes" / "bone.glb"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    test_store = StudyStore(root=tmp_path / "data")
    monkeypatch.setattr(studies_routes, "store", test_store)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_root_lists_endpoints(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["docs"] == "/docs"
    assert "POST /studies" in body["endpoints"]


@pytest.mark.req_geo
def test_upload_good_series_round_trip(client: TestClient) -> None:
    zip_path = FIXTURES / "good_series.zip"
    with zip_path.open("rb") as f:
        res = client.post(
            "/studies",
            params={"deidentify": True},
            files={"file": ("good_series.zip", f, "application/zip")},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["nifti_ready"] is True
    assert body["slice_count"] == 8
    assert body["spacing_mm"] == pytest.approx([1.0, 1.0, 2.0])
    assert body["deidentified"] is True
    study_id = body["id"]

    meta = client.get(f"/studies/{study_id}")
    assert meta.status_code == 200
    assert meta.json()["id"] == study_id

    nifti = client.get(f"/studies/{study_id}/nifti")
    assert nifti.status_code == 200
    assert nifti.content[:2] == b"\x1f\x8b"  # gzip

    slice_res = client.get(f"/studies/{study_id}/slices/3")
    assert slice_res.status_code == 200
    assert slice_res.headers["content-type"] == "image/png"
    assert slice_res.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.req_val
def test_upload_missing_slice_reports_gap(client: TestClient, tmp_path: Path) -> None:
    # Zip the missing_slice directory on the fly
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted((FIXTURES / "missing_slice").glob("*.dcm")):
            zf.write(path, arcname=path.name)
    buf.seek(0)
    res = client.post(
        "/studies",
        files={"file": ("missing.zip", buf, "application/zip")},
    )
    assert res.status_code == 200
    body = res.json()
    codes = {i["code"] for i in body["issues"]}
    assert "MISSING_SLICE_GAP" in codes
    # Gap is non-blocking for conversion — volume still produced
    assert body["nifti_ready"] is True
    assert body["ok"] is False


@pytest.mark.req_val
def test_upload_mixed_series_blocks_conversion(client: TestClient) -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted((FIXTURES / "mixed_series").glob("*.dcm")):
            zf.write(path, arcname=path.name)
    buf.seek(0)
    res = client.post(
        "/studies",
        files={"file": ("mixed.zip", buf, "application/zip")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["nifti_ready"] is False
    assert any(i["code"] == "MIXED_SERIES" for i in body["issues"])


def test_bone_mesh_endpoint(client: TestClient) -> None:
    if not MESH.exists():
        pytest.skip("bone.glb missing")
    res = client.get("/meshes/bone")
    assert res.status_code == 200
    assert res.content[:4] == b"glTF"
