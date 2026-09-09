Write-Host "=== Procesos de navegadores ==="
$browsers = @("chrome", "brave", "msedge", "firefox")
foreach ($browser in $browsers) {
    $processes = Get-Process -Name $browser -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        Write-Host "$($proc.ProcessName) | PID: $($proc.Id) | Titulo: $($proc.MainWindowTitle)"
    }
}
Write-Host "================================"

Write-Host "=== Ventanas visibles ==="
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
}
"@

[Win32]::EnumWindows({
    param($hWnd, $lParam)
    $title = New-Object System.Text.StringBuilder 256
    [Win32]::GetWindowText($hWnd, $title, 256) | Out-Null
    $titleStr = $title.ToString()
    $isVisible = [Win32]::IsWindowVisible($hWnd)
    $isMinimized = [Win32]::IsIconic($hWnd)
    
    if ($titleStr -ne "") {
        Write-Host "$titleStr | Visible: $isVisible | Minimized: $isMinimized"
    }
    return $true
}, [IntPtr]::Zero) | Out-Null

Write-Host "================================"
