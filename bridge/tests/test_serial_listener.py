import os

from bridge.core.serial_listener import prune_debug_wavs, save_debug_wav


def test_prune_debug_wavs_keeps_newest_files(tmp_path) -> None:
    debug_dir = tmp_path / "captures"
    debug_dir.mkdir()

    for index in range(5):
        path = debug_dir / f"segment-{index}.wav"
        path.write_bytes(b"old")
        mtime = 1000 + index
        os.utime(path, (mtime, mtime))

    prune_debug_wavs(debug_dir, "segment", retain_count=2)

    remaining = sorted(debug_dir.glob("segment-*.wav"), key=lambda path: path.stat().st_mtime)
    assert len(remaining) == 2
    assert [path.stat().st_mtime for path in remaining] == [1003.0, 1004.0]


def test_save_debug_wav_prunes_after_write(tmp_path) -> None:
    debug_dir = tmp_path / "captures"

    for index in range(3):
        path = debug_dir / f"segment-{index}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"old")
        mtime = 1000 + index
        os.utime(path, (mtime, mtime))

    saved = save_debug_wav(debug_dir, "segment", b"\x00\x00" * 256, retain_count=2)

    remaining = sorted(debug_dir.glob("segment-*.wav"), key=lambda path: path.stat().st_mtime)
    assert saved.exists()
    assert len(remaining) == 2
    assert saved in remaining
