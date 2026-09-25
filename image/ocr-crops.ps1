$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($WinRtTask, [Type]$ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

function Get-OcrText([string]$Path, [Windows.Media.Ocr.OcrEngine]$Engine) {
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($Engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $bitmap.Dispose()
    $stream.Dispose()
    return $result.Text
}

$engineHans = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
if (-not $engineHans) { throw "no zh-Hans-CN engine" }
$engineHant = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hant-TW'))

$scale = 3
$overlapRatio = 0.15
$tempDir = Join-Path $env:TEMP 'ocr_crops'
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

$files = Get-ChildItem -LiteralPath $args[0] -Filter '*.png' | Sort-Object Name
$idx = 0
foreach ($f in $files) {
    $idx++
    "`n===== " + $f.Name + " ====="
    $bmp = [System.Drawing.Bitmap]::FromFile($f.FullName)
    $w = $bmp.Width; $h = $bmp.Height
    "size: ${w}x${h}"
    for ($qx = 0; $qx -lt 2; $qx++) {
        for ($qy = 0; $qy -lt 2; $qy++) {
            $ox = [int]($w * $overlapRatio); $oy = [int]($h * $overlapRatio)
            $cw = [int]($w / 2) + $ox; $ch = [int]($h / 2) + $oy
            $cx = [Math]::Max(0, [int]($qx * $w / 2) - $ox)
            $cy = [Math]::Max(0, [int]($qy * $h / 2) - $oy)
            if ($cx + $cw -gt $w) { $cw = $w - $cx }
            if ($cy + $ch -gt $h) { $ch = $h - $cy }
            $rect = New-Object System.Drawing.Rectangle($cx, $cy, $cw, $ch)
            $crop = $bmp.Clone($rect, $bmp.PixelFormat)
            $big = New-Object System.Drawing.Bitmap([int]($cw * $scale), [int]($ch * $scale))
            $g = [System.Drawing.Graphics]::FromImage($big)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.DrawImage($crop, 0, 0, $big.Width, $big.Height)
            $g.Dispose()
            $crop.Dispose()
            $idx2 = "{0:d2}" -f $idx
            $tmp = Join-Path $tempDir ("crop_" + $idx2 + "_" + $qx + $qy + ".png")
            $big.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
            $big.Dispose()
            "--- Q($qx,$qy) Hans ---"
            $txt = Get-OcrText $tmp $engineHans
            if ($txt) { $txt } else { "(empty)" }
            if ($engineHant) {
                "--- Q($qx,$qy) Hant ---"
                $txt2 = Get-OcrText $tmp $engineHant
                if ($txt2) { $txt2 } else { "(empty)" }
            }
            Remove-Item -LiteralPath $tmp -Force
        }
    }
    $bmp.Dispose()
}
