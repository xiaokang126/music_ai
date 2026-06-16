import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_ROOT = Path("/tmp/musecut_flow_tests")
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
TEST_ROOT.mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'musecut_test.db'}"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["EXPORT_DIR"] = str(TEST_ROOT / "exports")
os.environ["GENERATED_DIR"] = str(TEST_ROOT / "generated")
os.environ["GLM_API_KEY"] = ""
os.environ["ACESTEP_MOCK_MODE"] = "always"
os.environ["JWT_SECRET"] = "test_secret"

from app.config import settings  # noqa: E402
from app.main import app, on_startup  # noqa: E402
from app.services.acestep_service import _concat_fitted_segments, _normalize_ace_segment  # noqa: E402
from app.services.exporter import render_mixed_audio, render_synthetic_bgm, render_video_with_mixed_audio  # noqa: E402
from app.services.llm_service import generate_timeline  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_ace_generation(monkeypatch):
    from app.routers import generation as generation_router
    from app.services import acestep_service

    async def fake_available():
        return True

    async def fake_generate_bgm_for_timeline(timeline_data: dict, project_id: str) -> dict:
        output_path = os.path.join(settings.GENERATED_DIR, f"{project_id}_bgm_full.mp3")
        render_synthetic_bgm(timeline_data, output_path, "mp3")
        return {
            "success": True,
            "audio_path": output_path,
            "segment_count": len(timeline_data.get("timeline", [])),
            "total_segments": len(timeline_data.get("timeline", [])),
        }

    monkeypatch.setattr(acestep_service, "ace_service_available", fake_available)
    monkeypatch.setattr(generation_router, "ace_service_available", fake_available)
    monkeypatch.setattr(acestep_service, "generate_bgm_for_timeline", fake_generate_bgm_for_timeline)


def _make_video(path: Path, duration: int = 3) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=160x90:rate=8",
        "-c:v",
        "mpeg4",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def _auth_headers(client: httpx.AsyncClient) -> dict:
    res = await client.post("/api/auth/register", json={"username": "flow_user", "password": "secret123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


async def _auth_headers_for(client: httpx.AsyncClient, username: str) -> dict:
    res = await client.post("/api/auth/register", json={"username": username, "password": "secret123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.mark.anyio
async def test_full_musecut_flow_with_mocked_generation_and_mixed_export(fake_ace_generation):
    await on_startup()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await _auth_headers(client)
        video_path = TEST_ROOT / "demo.mp4"
        _make_video(video_path)

        upload = await client.post(
            "/api/video/upload",
            headers=headers,
            data={"video_type": "campus_memory", "user_description": "毕业操场傍晚的朋友回忆"},
            files={"video": ("demo.mp4", video_path.read_bytes(), "video/mp4")},
        )
        assert upload.status_code == 200, upload.text
        project_id = upload.json()["id"]
        metadata = json.loads(upload.json()["metadata_json"])
        assert 2.5 <= metadata["duration"] <= 3.5

        marks = await client.post(
            f"/api/video/{project_id}/keypoints",
            headers=headers,
            json={
                "keypoints": [
                    {"time": 0, "type": "scene_start", "label": "开场", "importance": "normal", "description": ""},
                    {"time": 1.2, "type": "highlight", "label": "挥手", "importance": "critical", "description": ""},
                    {"time": 2.8, "type": "ending", "label": "结尾", "importance": "high", "description": ""},
                ],
                "voice_regions": [{"start": 0.5, "end": 1.4, "type": "voiceover", "content": "那一年夏天"}],
                "caption_events": [{"time": 1.5, "text": "毕业快乐", "style": "big_title"}],
            },
        )
        assert marks.status_code == 200, marks.text

        profile = await client.get(f"/api/video/{project_id}/profile", headers=headers)
        assert profile.status_code == 200, profile.text
        assert profile.json()["voice_regions"][0]["content"] == "那一年夏天"

        timeline = await client.post(
            "/api/timeline/generate",
            headers=headers,
            json={"project_id": project_id, "style": "campus_memory"},
        )
        assert timeline.status_code == 200, timeline.text
        timeline_json = json.loads(timeline.json()["timeline_json"])
        assert timeline_json["style"] == "campus_memory"
        assert timeline_json["duration"] == metadata["duration"]
        assert len(timeline_json["timeline"]) == 3
        assert timeline_json["ducking_schedule"]

        health = await client.get("/api/generate/acestep/health", headers=headers)
        assert health.status_code == 200, health.text
        assert health.json()["available"] is True
        assert health.json()["mode"] == "ace_only"
        assert health.json()["fallback_enabled"] is False

        generation = await client.post("/api/generate/bgm", headers=headers, json={"project_id": project_id})
        assert generation.status_code == 200, generation.text
        session_id = generation.json()["session_id"]

        status_res = await client.get(f"/api/generate/status/{session_id}", headers=headers)
        assert status_res.status_code == 200, status_res.text
        assert status_res.json()["status"] == "completed"
        assert status_res.json()["progress"] == 100

        audio = await client.get(f"/api/generate/audio/{session_id}", headers=headers)
        assert audio.status_code == 200, audio.text
        assert len(audio.content) > 1000

        export_audio = await client.post("/api/export/audio", headers=headers, json={"project_id": project_id, "format": "wav"})
        assert export_audio.status_code == 200, export_audio.text
        export_id = export_audio.json()["export_id"]
        export_status = await client.get(f"/api/export/status/{export_id}", headers=headers)
        assert export_status.status_code == 200, export_status.text
        assert export_status.json()["status"] == "completed"
        exported = await client.get(f"/api/export/download/{export_id}", headers=headers)
        assert exported.status_code == 200, exported.text
        assert exported.headers["content-type"].startswith("audio/")

        export_video = await client.post("/api/export/audio", headers=headers, json={"project_id": project_id, "format": "mp4"})
        assert export_video.status_code == 200, export_video.text
        export_video_id = export_video.json()["export_id"]
        export_video_status = await client.get(f"/api/export/status/{export_video_id}", headers=headers)
        assert export_video_status.status_code == 200, export_video_status.text
        assert export_video_status.json()["status"] == "completed"
        exported_video = await client.get(f"/api/export/download/{export_video_id}", headers=headers)
        assert exported_video.status_code == 200, exported_video.text
        assert exported_video.headers["content-type"].startswith("video/")
        assert len(exported_video.content) > 1000

        export_json = await client.post("/api/export/audio", headers=headers, json={"project_id": project_id, "format": "json"})
        assert export_json.status_code == 200, export_json.text
        json_status = await client.get(f"/api/export/status/{export_json.json()['export_id']}", headers=headers)
        assert json_status.json()["status"] == "completed"

        post = await client.post(
            "/api/community/posts",
            headers=headers,
            json={"project_id": project_id, "title": "毕业操场", "story_tags": ["毕业", "友情"], "description": "一次完整模拟发布", "is_anonymous": True},
        )
        assert post.status_code == 201, post.text
        post_id = post.json()["id"]
        assert post.json()["is_anonymous"] is True
        assert post.json()["username"] == "匿名创作者"

        post_detail = await client.get(f"/api/community/posts/{post_id}", headers=headers)
        assert post_detail.status_code == 200, post_detail.text
        assert post_detail.json()["username"] == "匿名创作者"

        collect_1 = await client.post(f"/api/community/posts/{post_id}/collect", headers=headers)
        collect_2 = await client.post(f"/api/community/posts/{post_id}/collect", headers=headers)
        assert collect_1.json()["collected"] is True
        assert collect_2.json()["collected"] is False

        featured = await client.post(f"/api/community/posts/{post_id}/featured", headers=headers, json={"is_featured": True})
        assert featured.status_code == 200, featured.text
        featured_list = await client.get("/api/community/featured")
        assert any(item["id"] == post_id for item in featured_list.json())


@pytest.mark.anyio
async def test_ace_generation_failure_does_not_use_local_fallback(monkeypatch):
    from app.services import acestep_service

    async def unavailable():
        return False

    monkeypatch.setattr(acestep_service, "ace_service_available", unavailable)
    timeline = generate_timeline({"metadata": {"duration": 3.0}}, "campus_memory")
    output = Path(settings.GENERATED_DIR) / "ace_unavailable_probe_bgm_full.mp3"
    if output.exists():
        output.unlink()

    with pytest.raises(acestep_service.AceStepError) as exc:
        await acestep_service.generate_bgm_for_timeline(timeline, "ace_unavailable_probe")

    assert "使用 ACE 调用失败" in str(exc.value)
    assert "未换用本地合成" in str(exc.value)
    assert not output.exists()


@pytest.mark.parametrize(
    "style",
    ["healing_vlog", "product_promo", "hype_edit", "campus_memory", "emotional_story", "knowledge_edu"],
)
def test_fallback_timeline_for_all_styles(style: str):
    profile = {
        "metadata": {"duration": 9.0},
        "voice_regions": [{"start": 1.0, "end": 2.5, "type": "voiceover"}],
        "key_events": [{"time": 4.0, "type": "highlight", "importance": "critical"}],
    }
    timeline = generate_timeline(profile, style)
    assert timeline["style"] == style
    assert timeline["duration"] == 9.0
    assert len(timeline["timeline"]) == 3
    assert timeline["timeline"][0]["start"] == 0
    assert timeline["timeline"][-1]["end"] == 9.0
    assert timeline["ducking_schedule"] == [{"start": 1.0, "end": 2.5, "reduce_db": 8}]


@pytest.mark.parametrize("fmt", ["wav", "mp3", "flac"])
def test_offline_exporter_renders_audio_formats(fmt: str):
    timeline = generate_timeline({"metadata": {"duration": 3.0}}, "hype_edit")
    output = TEST_ROOT / f"offline_mix.{fmt}"
    render_mixed_audio(timeline, None, str(output), fmt)
    assert output.exists()
    assert output.stat().st_size > 1000


def test_offline_exporter_renders_video_with_musecut_music():
    timeline = generate_timeline({"metadata": {"duration": 3.0}}, "campus_memory")
    video_path = TEST_ROOT / "offline_video.mp4"
    output = TEST_ROOT / "offline_video_export.mp4"
    _make_video(video_path)
    render_video_with_mixed_audio(timeline, None, str(video_path), str(output))
    assert output.exists()
    assert output.stat().st_size > 1000


def test_ace_segments_are_fitted_to_full_timeline_duration():
    short_raw = TEST_ROOT / "ace_short_raw.mp3"
    fitted = TEST_ROOT / "ace_short_fitted.mp3"
    full = TEST_ROOT / "ace_full_fitted.mp3"
    render_synthetic_bgm({"duration": 1.0, "timeline": [{"start": 0, "end": 1}]}, str(short_raw), "mp3")

    _normalize_ace_segment(str(short_raw), str(fitted), 3.0)
    _concat_fitted_segments([str(fitted)], str(full), 5000)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(full)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert float(probe.stdout.strip()) >= 4.8


def test_default_frontend_sfx_assets_exist():
    sfx_dir = BACKEND_ROOT.parent / "frontend" / "public" / "sfx"
    expected = [
        "whoosh_short.wav",
        "hit_impact.wav",
        "impact_cinematic.wav",
        "riser_short.wav",
        "riser_reverse.wav",
    ]
    for filename in expected:
        path = sfx_dir / filename
        assert path.exists(), filename
        assert path.stat().st_size > 1000


@pytest.mark.anyio
async def test_community_privacy_settings_and_delete_post():
    await on_startup()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        alice = await _auth_headers_for(client, "privacy_alice")
        bob = await _auth_headers_for(client, "privacy_bob")

        post = await client.post(
            "/api/community/posts",
            headers=alice,
            json={"title": "给好友看的作品", "description": "一段故事", "story_tags": ["友情"]},
        )
        assert post.status_code == 201, post.text
        post_id = post.json()["id"]
        assert post.json()["can_delete"] is True

        bob_feed = await client.get("/api/community/posts?recent_days=3", headers=bob)
        assert any(item["id"] == post_id for item in bob_feed.json()["posts"])

        hide = await client.post("/api/community/settings/hidden-authors", headers=bob, json={"username": "privacy_alice"})
        assert hide.status_code == 200, hide.text
        assert hide.json()["hidden_authors"][0]["username"] == "privacy_alice"
        bob_feed = await client.get("/api/community/posts?recent_days=3", headers=bob)
        assert all(item["id"] != post_id for item in bob_feed.json()["posts"])

        remove_hide = await client.delete(
            f"/api/community/settings/hidden-authors/{hide.json()['hidden_authors'][0]['user_id']}",
            headers=bob,
        )
        assert remove_hide.status_code == 200, remove_hide.text

        block = await client.post("/api/community/settings/blocked-viewers", headers=alice, json={"username": "privacy_bob"})
        assert block.status_code == 200, block.text
        bob_feed = await client.get("/api/community/posts?recent_days=3", headers=bob)
        assert all(item["id"] != post_id for item in bob_feed.json()["posts"])
        blocked_detail = await client.get(f"/api/community/posts/{post_id}", headers=bob)
        assert blocked_detail.status_code == 404

        deleted = await client.delete(f"/api/community/posts/{post_id}", headers=alice)
        assert deleted.status_code == 200, deleted.text
        alice_feed = await client.get("/api/community/posts", headers=alice)
        assert all(item["id"] != post_id for item in alice_feed.json()["posts"])
