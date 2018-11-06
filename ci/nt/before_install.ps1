Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
choco install -y aria2 ffmpeg python
refreshenv
pip install wheel
ffmpeg -version
python --version
