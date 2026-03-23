# SSH bridge notes

Windows <- VPS <- macOS

Current user-facing entry from macOS:

```bash
ssh windows-via-vps
```

Equivalent explicit command:

```bash
ssh -p 42024 seqi@127.0.0.1
```

Components:
- Windows scheduled task: `OpenClaw-Windows-Bridge`
- Windows tunnel script: `C:\Users\seqi\.ssh\openclaw_reverse_tunnel.ps1`
- Windows key: `C:\Users\seqi\.ssh\openclaw_bridge_key`
- mac LaunchAgent: `~/Library/LaunchAgents/com.openclaw.windows-bridge.plist`
- mac tunnel script: `~/.ssh/openclaw_mac_to_vps.sh`
- mac key: `~/.ssh/openclaw_bridge_key`

To stop:
- Windows: disable scheduled task `OpenClaw-Windows-Bridge`
- macOS: `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.openclaw.windows-bridge.plist`

Security note:
- This bridge relies on SSH key material stored on both machines.
- Replacing the shared key with separate per-hop keys would be safer.

## 2026-03-23 repair log

Symptoms observed:
- macOS -> Windows via `ssh windows-via-vps` returned `connection reset by peer`
- Windows scheduled task `OpenClaw-Windows-Bridge` existed, but recent task result was abnormal
- Windows `sshd` itself was healthy and listening on `1022`

Checks performed:
- Confirmed `C:\ProgramData\ssh\sshd_config` still uses `Port 1022`
- Confirmed Windows `sshd` service was running and listening on both `0.0.0.0:1022` and `[::]:1022`
- Confirmed Windows could still log into VPS `111.229.167.172` using `C:\Users\seqi\.ssh\openclaw_bridge_key`
- Reproduced reverse tunnel creation manually and verified VPS `42022` could listen
- Observed that traffic from macOS reached VPS and was forwarded back to Windows, but the connection reset occurred after the tunnel connected to Windows `1022`

Root cause hypothesis:
- The Windows reverse tunnel script was using a non-system `ssh.exe` build and the remote forward target `localhost:1022`
- That combination likely triggered an address-family / client-implementation issue on the Windows side when handling tunneled return traffic

Fix applied on Windows:
- Updated `C:\Users\seqi\.ssh\openclaw_reverse_tunnel.ps1`
- Forced use of system OpenSSH client: `C:\Windows\System32\OpenSSH\ssh.exe`
- Changed remote forward target from `42022:localhost:1022` to `42022:127.0.0.1:1022`
- Restarted the scheduled task and verified a live SSH tunnel process using the system client

Post-fix verification:
- Windows -> VPS SSH session established successfully
- VPS confirmed listening on `0.0.0.0:42022` and `[::]:42022`
- User confirmed the bridge recovered and connection worked again

Current known-good Windows tunnel command:

```powershell
C:\Windows\System32\OpenSSH\ssh.exe -i C:\Users\seqi\.ssh\openclaw_bridge_key -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -R 42022:127.0.0.1:1022 ubuntu@111.229.167.172
```
