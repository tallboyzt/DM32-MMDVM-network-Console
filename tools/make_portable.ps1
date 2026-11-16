# 打包 Windows 便携版：内置 Python + 已编译的 MMDVMHost/DMRGateway + 配置
# 用法: powershell -ExecutionPolicy Bypass -File tools\make_portable.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist\MMDVM-Console-Portable"
$cache = Join-Path $root "tools\cache"
$zip = Join-Path $root "MMDVM-Console-Portable-win64.zip"
$pyVer = "3.13.17"
$pyZip = Join-Path $cache "python-$pyVer-embed-amd64.zip"
$pyUrls = @(
    "https://registry.npmmirror.com/-/binary/python/$pyVer/python-$pyVer-embed-amd64.zip",
    "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-amd64.zip"
)

Write-Host "== clean dist"
if (Test-Path (Join-Path $root "dist")) { Remove-Item (Join-Path $root "dist") -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dist | Out-Null

Write-Host "== copy app / bin / mmdvm"
Copy-Item (Join-Path $root "app") $dist -Recurse
Copy-Item (Join-Path $root "bin") $dist -Recurse
Copy-Item (Join-Path $root "mmdvm") $dist -Recurse
Copy-Item (Join-Path $root "LICENSE") $dist -ErrorAction SilentlyContinue

Write-Host "== ensure RadioFoundry debug tools"
$rf = Join-Path $root "tools\radiofoundry"
if (-not (Test-Path (Join-Path $rf "tools"))) {
    git clone --depth 1 --filter=blob:none --sparse https://github.com/RadioFoundry/RadioFoundry.git $rf
    git -C $rf sparse-checkout set tools stub
    if ($LASTEXITCODE -ne 0) { throw "RadioFoundry clone failed" }
}

Write-Host "== copy tools (RadioFoundry debug link + portable launcher)"
New-Item -ItemType Directory -Force -Path (Join-Path $dist "tools") | Out-Null
robocopy (Join-Path $root "tools\radiofoundry") (Join-Path $dist "tools\radiofoundry") /E /XD ".git" /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }
Copy-Item (Join-Path $root "tools\portable\launch.py") (Join-Path $dist "tools") -Force
Copy-Item (Join-Path $root "tools\portable\init_config.py") (Join-Path $dist "tools") -Force

Write-Host "== fetch Python $pyVer embeddable"
New-Item -ItemType Directory -Force -Path $cache | Out-Null
if (-not (Test-Path $pyZip)) {
    foreach ($u in $pyUrls) {
        try {
            Write-Host "   downloading $u"
            Invoke-WebRequest -Uri $u -OutFile $pyZip -UseBasicParsing -TimeoutSec 180
            break
        } catch {
            Write-Host "   failed: $($_.Exception.Message)"
        }
    }
}
$runtime = Join-Path $dist "runtime"
Expand-Archive -Path $pyZip -DestinationPath $runtime -Force

Write-Host "== enable site-packages / pyserial inside runtime"
$pth = Get-ChildItem $runtime -Filter "python*._pth" | Select-Object -First 1
$content = "python313.zip`r`n.`r`nLib\site-packages`r`nimport site`r`n"
[System.IO.File]::WriteAllText($pth.FullName, $content, (New-Object System.Text.UTF8Encoding($false)))

$spDst = Join-Path $runtime "Lib\site-packages\serial"
New-Item -ItemType Directory -Force -Path (Split-Path $spDst) | Out-Null
$serialLocal = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\Lib\site-packages\serial"
if (Test-Path $serialLocal) {
    Copy-Item $serialLocal $spDst -Recurse -Force
} else {
    Write-Host "   pyserial: download from PyPI"
    $meta = Invoke-RestMethod "https://pypi.org/pypi/pyserial/json"
    $wheel = $meta.urls | Where-Object { $_.packagetype -eq "bdist_wheel" } | Select-Object -First 1
    $whl = Join-Path $cache "pyserial.whl"
    Invoke-WebRequest $wheel.url -OutFile $whl -UseBasicParsing
    $unpack = Join-Path $cache "pyserial-unpack"
    Expand-Archive $whl -DestinationPath $unpack -Force
    Copy-Item (Join-Path $unpack "serial") $spDst -Recurse -Force
}

Write-Host "== write launcher files"
Copy-Item (Join-Path $root "tools\portable\launch.bat") $dist -Force
Get-ChildItem (Join-Path $root "tools\portable") -Filter "*.txt" | Copy-Item -Destination $dist -Force

Write-Host "== verify runtime"
& (Join-Path $runtime "python.exe") -c "import sys, serial, http.server; print(sys.version.split()[0], 'pyserial', serial.__version__)"

Write-Host "== zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $dist "*") -DestinationPath $zip -CompressionLevel Optimal

$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
$files = (Get-ChildItem $dist -Recurse -File | Measure-Object).Count
Write-Host "DONE: $zip  ($mb MB, $files files)"
