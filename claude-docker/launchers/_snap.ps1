# cd-up's window snap, run in Windows PowerShell 5.1 (powershell.exe) from
# WSL. cd-up prepends one line setting $Mode, $Before (window handles),
# $X, $Y, $W, $H (pixels) and passes the lot as -EncodedCommand, so no
# execution policy or Windows path is involved.
#
#   list   print the handle of every visible Windows Terminal window
#   snap   wait up to 4 s for a terminal window not in $Before, place it at
#          $X,$Y size $W x $H and print its handle; none appeared = exit 3
#          (the group's window already existed, nothing to move)
#
# Placement is exact: SetWindowPos sizes the whole window, including the
# invisible resize border Windows adds on the left, right and bottom (7 px
# each at 100 %), so the window is placed once, its visible frame measured
# (DWMWA_EXTENDED_FRAME_BOUNDS), and placed again grown by the borders.
# Per-monitor DPI awareness on the thread keeps both in physical pixels.
# Any error: one line on stderr, exit 1.
#
# -EncodedCommand makes powershell.exe write its other streams to stderr as
# CLIXML for a calling PowerShell; the progress bar Windows PowerShell shows
# while loading a module ("Preparing modules for first use") would land in
# cd-up's output as an XML blob. So no progress, and errors go out as text.
$ProgressPreference = 'SilentlyContinue'
trap { [Console]::Error.WriteLine($_.ToString()); exit 1 }
$ErrorActionPreference = 'Stop'

Add-Type @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class CdUpSnap {
  public struct RECT { public int L, T, R, B; }
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", SetLastError = true)] static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int ht, uint f);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int a, out RECT r, int n);
  [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c);
  public static List<long> Terminals() {
    var l = new List<long>();
    EnumWindows((h, p) => {
      var s = new StringBuilder(64); GetClassName(h, s, 64);
      if (IsWindowVisible(h) && s.ToString() == "CASCADIA_HOSTING_WINDOW_CLASS") l.Add(h.ToInt64());
      return true;
    }, IntPtr.Zero);
    return l;
  }
  static void Move(IntPtr h, int x, int y, int w, int ht) {
    // 0x14: SWP_NOZORDER | SWP_NOACTIVATE
    if (!SetWindowPos(h, IntPtr.Zero, x, y, w, ht, 0x14)) throw new System.ComponentModel.Win32Exception();
  }
  public static void Place(long hl, int x, int y, int w, int ht) {
    var h = new IntPtr(hl);
    SetThreadDpiAwarenessContext((IntPtr)(-4));  // per-monitor aware v2
    Move(h, x, y, w, ht);
    RECT r, f;
    if (!GetWindowRect(h, out r)) throw new Exception("GetWindowRect failed");
    if (DwmGetWindowAttribute(h, 9, out f, 16) != 0) throw new Exception("DwmGetWindowAttribute failed");
    int l = f.L - r.L, t = f.T - r.T, rr = r.R - f.R, b = r.B - f.B;
    Move(h, x - l, y - t, w + l + rr, ht + t + b);
  }
}
'@

if ($Mode -eq 'list') {
  [CdUpSnap]::Terminals()
  exit 0
}
if ($Mode -ne 'snap') { throw "unknown mode '$Mode'" }
$new = $null
for ($i = 0; $i -lt 40 -and -not $new; $i++) {
  Start-Sleep -Milliseconds 100
  $new = [CdUpSnap]::Terminals() | Where-Object { $Before -notcontains $_ } | Select-Object -First 1
}
if (-not $new) { exit 3 }
# Let the new window finish its own first layout before moving it.
Start-Sleep -Milliseconds 300
[CdUpSnap]::Place($new, $X, $Y, $W, $H)
$new
