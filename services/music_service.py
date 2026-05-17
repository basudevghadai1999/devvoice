import os
import shutil
import subprocess
import tempfile

_music_proc = None

TMP_MP3 = os.path.join(tempfile.gettempdir(), 'dev_music.mp3')
TMP_TPL = os.path.join(tempfile.gettempdir(), 'dev_music.%(ext)s')


def _osascript(script: str) -> str:
    r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return r.stdout.strip()


def _kill_afplay():
    """Kill all afplay processes (handles orphaned ones after server restart)."""
    subprocess.run(['pkill', '-f', 'afplay'], capture_output=True)


def _stop_yt_music():
    global _music_proc
    if _music_proc and _music_proc.poll() is None:
        _music_proc.terminate()
    _music_proc = None
    _kill_afplay()


def _spotify_running() -> bool:
    return _osascript('application "Spotify" is running') == 'true'


def _apple_music_running() -> bool:
    return _osascript('application "Music" is running') == 'true'


def play_pause() -> str:
    if _spotify_running():
        _osascript('tell application "Spotify" to playpause')
        state = _osascript('tell application "Spotify" to player state as string')
        return "Spotify resumed" if state == "playing" else "Spotify paused"
    _stop_yt_music()
    if _apple_music_running():
        _osascript('tell application "Music" to playpause')
        return "Music toggled"
    return "No music app is open"


def next_track() -> str:
    if _spotify_running():
        _osascript('tell application "Spotify" to next track')
        return "Next track"
    if _apple_music_running():
        _osascript('tell application "Music" to next track')
        return "Next track"
    return "No music app is open"


def previous_track() -> str:
    if _spotify_running():
        _osascript('tell application "Spotify" to previous track')
        return "Previous track"
    if _apple_music_running():
        _osascript('tell application "Music" to previous track')
        return "Previous track"
    return "No music app is open"


def stop_music() -> str:
    _stop_yt_music()
    if _spotify_running():
        _osascript('tell application "Spotify" to pause')
    elif _apple_music_running():
        _osascript('tell application "Music" to pause')
    return "Music stopped"


def volume_up() -> str:
    _osascript('set volume output volume (output volume of (get volume settings) + 10)')
    return "Volume up"


def volume_down() -> str:
    _osascript('set volume output volume (output volume of (get volume settings) - 10)')
    return "Volume down"


def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    _osascript(f'set volume output volume {level}')
    return f"Volume set to {level} percent"


def play_song(query: str) -> str:
    global _music_proc

    if not shutil.which('yt-dlp'):
        return "Please install yt-dlp: brew install yt-dlp"

    _stop_yt_music()

    # Clean up old file
    if os.path.exists(TMP_MP3):
        os.remove(TMP_MP3)

    print(f"  [music] Searching: {query}")

    result = subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '--audio-quality', '0',
         '-o', TMP_TPL, f'ytsearch1:{query}'],
        capture_output=True, text=True
    )

    print(f"  [music] yt-dlp returncode={result.returncode}")
    if result.returncode != 0 or not os.path.exists(TMP_MP3):
        print(f"  [music] stderr: {result.stderr[:300]}")
        return f"Sorry, I couldn't find {query}"

    _osascript('set volume output volume 90')
    _music_proc = subprocess.Popen(['afplay', '-v', '2.0', TMP_MP3])
    return f"Playing {query}"
