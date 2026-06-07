###############################################
# FILE: skills/system.py
# PURPOSE: Controls Windows system — WiFi, hotspot, airplane mode,
#          night light, Bluetooth, lock, sleep, shutdown, restart,
#          battery saver. Uses PowerShell for reliable control.
# DEPENDENCIES: subprocess, ctypes, os, core/speaker.py
# CONNECTED TO: core/intent.py
###############################################

import os
import ctypes
import subprocess
import tempfile
import core.speaker as speaker
import core.intent as intent


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def _run_ps(script: str, timeout: int = 12) -> int:
    """Write and run a PowerShell script, return returncode."""
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.ps1', delete=False, encoding='utf-8'
    )
    tmp.write(script)
    tmp.close()
    try:
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-NonInteractive", "-File", tmp.name],
            capture_output=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.returncode
    except Exception as e:
        print(f"[System] PS error: {e}")
        return -1
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _radio_set(kind: str, state: str, timeout: int = 15) -> bool:
    """
    Toggle a Windows radio (WiFi or Bluetooth) using the WinRT Radio API.
    kind:  'WiFi' or 'Bluetooth'
    state: 'On'  or 'Off'
    Returns True on success.
    """
    ps = f"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
    $_.Name -eq "AsTask" -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
}})[0]
[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null

# Request access
$accessTask = [Windows.Devices.Radios.Radio]::RequestAccessAsync()
$accessTyped = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus])
$accessTyped.Invoke($null, @($accessTask)).Wait()

# Get all radios
$getTask = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
$getTyped = $asTaskGeneric.MakeGenericMethod([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$getTyped.Invoke($null, @($getTask)).Wait()
$radios = $getTyped.Invoke($null, @($getTask)).Result

foreach ($radio in $radios) {{
    if ($radio.Kind -eq [Windows.Devices.Radios.RadioKind]::{kind}) {{
        $setState = $radio.SetStateAsync([Windows.Devices.Radios.RadioState]::{state})
        $setTyped = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus])
        $setTyped.Invoke($null, @($setState)).Wait()
        Write-Host "Done"
    }}
}}
"""
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.ps1', delete=False, encoding='utf-8'
    )
    tmp.write(ps)
    tmp.close()
    try:
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-NonInteractive", "-File", tmp.name],
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.returncode == 0
    except Exception as e:
        print(f"[System] Radio error: {e}")
        return False
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


# ── Elevated runner ───────────────────────────────────────────
def _run_elevated(command: str, timeout: int = 20):
    """Run a netsh command elevated silently — no visible window."""
    import tempfile
    # Write to a temp bat file
    bat = tempfile.NamedTemporaryFile(
        mode='w', suffix='.bat', delete=False, encoding='utf-8'
    )
    bat.write(f'@echo off\n{command}\n')
    bat.close()
    try:
        # ShellExecute with runas — silent, no window
        import ctypes
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "cmd.exe",
            f'/c "{bat.name}"',
            None, 0  # 0 = SW_HIDE
        )
        if ret <= 32:
            print(f"[System] ShellExecute failed: {ret}")
        else:
            import time
            time.sleep(3)  # wait for command to complete
    except Exception as e:
        print(f"[System] Elevated run error: {e}")
    finally:
        try:
            os.unlink(bat.name)
        except Exception:
            pass


# ── WiFi ──────────────────────────────────────────────────────
def wifi_on():
    speaker.speak("Turning on Wi-Fi, sir.")
    _run_elevated("netsh interface set interface Wi-Fi enabled")


def wifi_off():
    speaker.speak("Turning off Wi-Fi, sir.")
    _run_elevated("netsh interface set interface Wi-Fi disabled")


# ── Hotspot ───────────────────────────────────────────────────
def _toggle_hotspot_ui(action: str):
    """
    Toggle Mobile Hotspot by clicking the Quick Settings panel button
    using pyautogui to find and click the hotspot tile.
    """
    import time
    import pyautogui
    import subprocess

    try:
        # Step 1: Click the Quick Settings area (bottom-right clock/network area)
        # Get screen size to find taskbar
        sw, sh = pyautogui.size()

        # Click the Quick Settings button (network/volume/battery area, bottom-right)
        # Typically at about 85% from left, near bottom
        qs_x = int(sw * 0.92)
        qs_y = sh - 12
        pyautogui.click(qs_x, qs_y)
        time.sleep(0.8)

        # Step 2: Take screenshot and find "Mobile hotspot" button
        # Use UI Automation to find it now that panel is open
        ps = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, "Mobile hotspot"
)
$btn = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if ($btn) {{
    $rect = $btn.Current.BoundingRectangle
    $cx = [int]($rect.X + $rect.Width / 2)
    $cy = [int]($rect.Y + $rect.Height / 2)
    Write-Host "FOUND $cx $cy"
    $state = $btn.GetCurrentPropertyValue([System.Windows.Automation.TogglePattern]::ToggleStateProperty)
    Write-Host "STATE $state"
}} else {{
    Write-Host "NOTFOUND"
}}
"""
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.ps1', delete=False, encoding='utf-8'
        )
        tmp.write(ps)
        tmp.close()

        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-NonInteractive", "-File", tmp.name],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        os.unlink(tmp.name)

        output = result.stdout.strip()
        print(f"[Hotspot] PS output: {output}")

        if "FOUND" in output:
            lines = output.split('\n')
            for line in lines:
                if line.startswith("FOUND"):
                    parts = line.split()
                    cx, cy = int(parts[1]), int(parts[2])
                    # Get current state
                    state = 0
                    for l in lines:
                        if l.startswith("STATE"):
                            state = int(l.split()[1])

                    # Click only if state needs to change
                    if (action == 'on' and state == 0) or (action == 'off' and state == 1):
                        pyautogui.click(cx, cy)
                        time.sleep(0.3)

                    # Close Quick Settings
                    pyautogui.press('escape')
                    return True

        # Close panel
        pyautogui.press('escape')
        return False

    except Exception as e:
        print(f"[Hotspot] Error: {e}")
        try:
            pyautogui.press('escape')
        except Exception:
            pass
        return False


def hotspot_on():
    speaker.speak("Turning on mobile hotspot, sir.")
    if not _toggle_hotspot_ui("on"):
        os.startfile("ms-settings:network-mobilehotspot")
        speaker.speak("Opening hotspot settings for you, sir.")


def hotspot_off():
    speaker.speak("Turning off mobile hotspot, sir.")
    if not _toggle_hotspot_ui("off"):
        os.startfile("ms-settings:network-mobilehotspot")
        speaker.speak("Opening hotspot settings for you, sir.")


# ── Airplane Mode ─────────────────────────────────────────────
def airplane_mode_on():
    speaker.speak("Enabling airplane mode, sir.")
    # Use elevated cmd to write HKLM registry key
    _run_elevated(
        "reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\RadioManagement\\SystemRadioState\" "
        "/v \"(Default)\" /t REG_DWORD /d 1 /f"
    )
    # Disable wireless adapters (doesn't need elevation via netsh)
    _run_ps("""
Get-NetAdapter | Where-Object {$_.PhysicalMediaType -in @("802.11","Native 802.11")} |
    Disable-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue
""")


def airplane_mode_off():
    speaker.speak("Disabling airplane mode, sir.")
    _run_elevated(
        "reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\RadioManagement\\SystemRadioState\" "
        "/v \"(Default)\" /t REG_DWORD /d 0 /f"
    )
    _run_ps("""
Get-NetAdapter | Where-Object {$_.PhysicalMediaType -in @("802.11","Native 802.11")} |
    Enable-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue
""")


# ── Night Light ───────────────────────────────────────────────
def night_light_on():
    speaker.speak("Turning on night light, sir.")
    # Use Settings URI — most reliable, no explorer restart needed
    ps = r"""
# Try registry method first (no explorer restart)
$base = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
$key = "$base\default`$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
if (Test-Path $key) {
    try {
        $data = (Get-ItemProperty -Path $key -Name "Data" -ErrorAction Stop).Data
        if ($data -and $data.Length -gt 18) {
            $data[18] = 0x13
            Set-ItemProperty -Path $key -Name "Data" -Value ([byte[]]$data) -Type Binary -Force
            Write-Host "Night light ON via registry"
        }
    } catch {
        Write-Host "Registry method failed: $_"
    }
}
"""
    result = _run_ps(ps)
    if result != 0:
        # Fallback: open night light settings
        os.startfile("ms-settings:display")
        speaker.speak("Please enable night light manually in the settings that just opened, sir.")


def night_light_off():
    speaker.speak("Turning off night light, sir.")
    ps = r"""
$base = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
$key = "$base\default`$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
if (Test-Path $key) {
    try {
        $data = (Get-ItemProperty -Path $key -Name "Data" -ErrorAction Stop).Data
        if ($data -and $data.Length -gt 18) {
            $data[18] = 0x12
            Set-ItemProperty -Path $key -Name "Data" -Value ([byte[]]$data) -Type Binary -Force
            Write-Host "Night light OFF via registry"
        }
    } catch {
        Write-Host "Registry method failed: $_"
    }
}
"""
    result = _run_ps(ps)
    if result != 0:
        os.startfile("ms-settings:display")
        speaker.speak("Please disable night light manually in the settings that just opened, sir.")


# ── Bluetooth ─────────────────────────────────────────────────
def bluetooth_on():
    speaker.speak("Turning on Bluetooth, sir.")
    ok = _radio_set("Bluetooth", "On")
    if not ok:
        speaker.speak("I could not turn on Bluetooth, sir.")


def bluetooth_off():
    speaker.speak("Turning off Bluetooth, sir.")
    ok = _radio_set("Bluetooth", "Off")
    if not ok:
        speaker.speak("I could not turn off Bluetooth, sir.")


# ── Battery Saver ─────────────────────────────────────────────
def battery_saver_on():
    speaker.speak("Enabling battery saver mode, sir.")
    try:
        # Power Saver GUID
        subprocess.run(
            ["powercfg", "/setactive", "a1841308-3541-4fab-bc81-f71556f20b4a"],
            capture_output=True, timeout=8,
        )
    except Exception:
        speaker.speak("I could not enable battery saver, sir.")


def battery_saver_off():
    speaker.speak("Disabling battery saver, switching to balanced power, sir.")
    try:
        # Balanced GUID
        subprocess.run(
            ["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
            capture_output=True, timeout=8,
        )
    except Exception:
        speaker.speak("I could not disable battery saver, sir.")


# ── Screen / System ───────────────────────────────────────────
def lock_screen():
    speaker.speak("Locking the screen now, sir.")
    try:
        ctypes.windll.user32.LockWorkStation()
    except Exception:
        speaker.speak("I could not lock the screen, sir.")


def sleep_pc():
    speaker.speak("Putting the system to sleep now, sir.")
    try:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception:
        speaker.speak("I could not initiate sleep mode, sir.")


def open_settings():
    speaker.speak("Opening Windows Settings, sir.")
    try:
        os.startfile("ms-settings:")
    except Exception:
        speaker.speak("I could not open Settings, sir.")


def open_task_manager():
    speaker.speak("Opening Task Manager, sir.")
    try:
        subprocess.Popen(["taskmgr"])
    except Exception:
        speaker.speak("I could not open Task Manager, sir.")


def shutdown_pc():
    speaker.speak("Are you sure you want to shut down, sir? Please confirm.")
    intent.set_pending("shutdown")
    _emit("confirmation_required", {"action": "shutdown"})


def restart_pc():
    speaker.speak("Are you sure you want to restart, sir? Please confirm.")
    intent.set_pending("restart")
    _emit("confirmation_required", {"action": "restart"})


def confirm_shutdown():
    speaker.speak("Shutting down the system in 5 seconds, sir. Goodbye.")
    try:
        os.system("shutdown /s /t 5")
    except Exception:
        speaker.speak("I could not initiate shutdown, sir.")


def confirm_restart():
    speaker.speak("Restarting the system in 5 seconds, sir.")
    try:
        os.system("shutdown /r /t 5")
    except Exception:
        speaker.speak("I could not initiate restart, sir.")
