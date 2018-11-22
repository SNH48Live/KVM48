$ErrorActionPreference = "Stop"
Get-WindowsFeature
Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
ls C:\Windows\System32
choco install -y aria2 python
# Download and install a static build of FFmpeg due to DLL loading difficulties:
# https://github.com/SNH48Live/KVM48/issues/4
# At the moment the downloaded build is a nightly; I've contacted the packager
# to see if he could provide a static URL for the latest stable.
Invoke-WebRequest "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip" -OutFile ffmpeg.zip
Expand-Archive ffmpeg.zip .
Copy-Item "ffmpeg-latest-win32-static\bin\ffmpeg.exe" "$env:ChocolateyInstall\bin"
refreshenv
pip install wheel
Get-Command ffmpeg
ffmpeg -version
if ($LastExitCode -ne 0) {
    throw "ffmpeg failed with $LastExitCode"
}
Get-Command python
python --version
