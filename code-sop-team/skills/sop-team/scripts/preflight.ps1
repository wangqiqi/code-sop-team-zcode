# 工程 SOP 专家团 · 第 0 步环境自检（Windows / PowerShell）
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File preflight.ps1 [-Root <代码目录>]
# 退出码：0 可开工 / 1 有阻塞项
param([string]$Root = "")

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$fail = @()
$warn = @()

# 脚本位于 <插件根>\skills\sop-team\scripts\ → 插件根 = 上三级
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

function Test-Py([string]$exe) {
  if (-not $exe -or -not (Test-Path -LiteralPath $exe)) { return $false }
  $v = (& $exe -V 2>&1) -join " "
  return ($v -match '^Python 3\.(8|9|1[0-9])')
}

# 用 UTF-8 读取子进程输出：sop_gate.py 的管道输出是 UTF-8，按控制台代码页读会乱码
function Invoke-Utf8([string]$exe, [string[]]$argv) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $exe
  $psi.Arguments = ($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join " "
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
  $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
  $p = [System.Diagnostics.Process]::Start($psi)
  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  $p.WaitForExit()
  return @{ Code = $p.ExitCode; Out = ($out + $err) }
}

# ---- 1) 定位闸门脚本：环境变量优先，其次插件根相对定位 ----
$gate = $env:SOP_GATE
if (-not $gate -or -not (Test-Path -LiteralPath $gate)) {
  $gate = Join-Path $pluginRoot "bin\sop_gate.py"
}
if ($gate -and (Test-Path -LiteralPath $gate)) { "OK   闸门: $gate" }
else { "FAIL 闸门: 未找到 sop_gate.py（检查插件是否已安装；或设 SOP_GATE=<绝对路径>）"; $fail += "gate" }

# ---- 2) 定位 Python：PATH → 常见安装位置 ----
$py = $null
$where = ""

foreach ($n in @("python", "py", "python3")) {
  $c = Get-Command $n -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($c -and (Test-Py $c.Source)) { $py = $c.Source; $where = "PATH"; break }
}

if (-not $py) {
  $found = @()
  foreach ($pat in @("$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe", "C:\Python3*\python.exe")) {
    $found += Get-ChildItem $pat -ErrorAction SilentlyContinue
  }
  foreach ($c in ($found | Sort-Object FullName -Descending)) {
    if (Test-Py $c.FullName) { $py = $c.FullName; $where = "常见安装位置"; break }
  }
}

if ($py) {
  "OK   解释器: $py"
  "      来源: $where · 版本: $((& $py -V 2>&1) -join ' ')"
} else {
  "FAIL 解释器: 未找到 Python 3.8+（PATH 与常见安装位置都没有）"
  "      安装: winget install -e --id Python.Python.3.12    或    https://www.python.org/downloads/"
  $fail += "python"
}

# ---- 3) 可选：项目侧自检 ----
if ($Root) {
  if (-not (Test-Path -LiteralPath $Root)) {
    "FAIL 目录: $Root 不存在"
    $fail += "root"
  } elseif ($py -and $gate) {
    $r = Invoke-Utf8 $py @($gate, "doctor", "--root", $Root)
    $lines = ($r.Out -split "`r?`n") | Where-Object { $_ -ne "" }
    $bad = $lines | Where-Object { $_ -match '^FAIL' }
    $wn = $lines | Where-Object { $_ -match '^WARN' }
    if ($bad) { $bad | ForEach-Object { "FAIL doctor: $_" }; $fail += "doctor" }
    if ($wn) { $wn | ForEach-Object { "WARN doctor: $_" }; $warn += "doctor" }
    if (-not $bad -and -not $wn) { "OK   doctor: 全项通过（rc=$($r.Code)）" }
  }
}

# ---- 4) 结论 ----
""
"      插件根: $pluginRoot"
""
if ($fail.Count -gt 0) {
  "结论: BLOCK（$($fail -join ', ')）—— 修完再开工；确实无法启用硬闸时必须明说「软约束降级模式」"
  exit 1
}
if ($warn.Count -gt 0) { "结论: OK(有告警) —— 可开工，但要向用户说明告警影响" }
else { "结论: OK —— 后续统一用 `"$py`" 调用闸门，不要假设 PATH 里有 python" }
exit 0
