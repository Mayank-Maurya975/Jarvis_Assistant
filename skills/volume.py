###############################################
# FILE: skills/volume.py
# PURPOSE: Full system volume control using pycaw Windows audio API.
#          Updated for new pycaw API where GetSpeakers() returns AudioDevice
#          with .EndpointVolume property directly.
# DEPENDENCIES: pycaw, core/speaker.py
# CONNECTED TO: core/intent.py
###############################################

import core.speaker as speaker

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _PYCAW = True
except Exception:
    _PYCAW = False


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def _get_vol():
    """Return IAudioEndpointVolume interface using new pycaw API."""
    if not _PYCAW:
        return None
    try:
        device = AudioUtilities.GetSpeakers()
        # New pycaw: AudioDevice has .EndpointVolume directly
        if hasattr(device, 'EndpointVolume'):
            return device.EndpointVolume
        # Old pycaw fallback
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        iface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        from ctypes import cast, POINTER
        return cast(iface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        print(f"[Volume] Interface error: {e}")
        return None


def get_volume() -> int:
    vol = _get_vol()
    if vol:
        try:
            return int(vol.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            pass
    return 50


def set_volume(level: int):
    level = max(0, min(100, int(level)))
    vol = _get_vol()
    if vol:
        try:
            vol.SetMasterVolumeLevelScalar(level / 100, None)
            speaker.speak(f"Volume set to {level} percent, sir.")
            _emit("volume_update", {"value": level})
            return
        except Exception as e:
            print(f"[Volume] Set error: {e}")
    # Fallback: use PowerShell nircmd-style via SoundVolumeView or built-in
    _set_volume_ps(level)


def _set_volume_ps(level: int):
    """PowerShell fallback for volume control."""
    import subprocess, tempfile, os
    ps = f"""
$obj = New-Object -ComObject WScript.Shell
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}}
'@
"""
    # Simpler: use nircmd if available, else just speak error
    try:
        result = subprocess.run(
            ["nircmd", "setsysvolume", str(int(level * 655.35))],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            speaker.speak(f"Volume set to {level} percent, sir.")
            _emit("volume_update", {"value": level})
            return
    except Exception:
        pass
    speaker.speak(f"Volume control encountered an issue, sir. Current level may not have changed.")


def increase_volume(amount: int = 10):
    set_volume(get_volume() + amount)


def decrease_volume(amount: int = 10):
    set_volume(get_volume() - amount)


def mute():
    vol = _get_vol()
    if vol:
        try:
            vol.SetMute(1, None)
            speaker.speak("Audio muted, sir.")
            _emit("volume_update", {"value": 0, "muted": True})
            return
        except Exception as e:
            print(f"[Volume] Mute error: {e}")
    speaker.speak("Mute control unavailable, sir.")


def unmute():
    vol = _get_vol()
    if vol:
        try:
            vol.SetMute(0, None)
            current = get_volume()
            speaker.speak("Audio unmuted, sir.")
            _emit("volume_update", {"value": current, "muted": False})
            return
        except Exception as e:
            print(f"[Volume] Unmute error: {e}")
    speaker.speak("Unmute control unavailable, sir.")
