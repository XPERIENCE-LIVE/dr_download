Add-Type -AssemblyName System.Drawing
$size = 512
$bitmap = New-Object System.Drawing.Bitmap($size, $size)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::FromArgb(11, 13, 16))
$panel = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(25, 31, 39))
$border = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(99, 133, 255), 18)
$graphics.FillRectangle($panel, 58, 58, 396, 396)
$graphics.DrawRectangle($border, 58, 58, 396, 396)
$font = New-Object System.Drawing.Font("Segoe UI", 210, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$ivory = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(241, 238, 230))
$graphics.DrawString("D", $font, $ivory, 108, 112)
$amberPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(244, 184, 96), 24)
$amberPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$amberPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$graphics.DrawLine($amberPen, 345, 170, 345, 340)
$graphics.DrawLine($amberPen, 294, 292, 345, 343)
$graphics.DrawLine($amberPen, 396, 292, 345, 343)
$output = Join-Path $PSScriptRoot "..\electron\build\icon.png"
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($output)) | Out-Null
$bitmap.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bitmap.Dispose(); $panel.Dispose(); $border.Dispose(); $font.Dispose(); $ivory.Dispose(); $amberPen.Dispose()
