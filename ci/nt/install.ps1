Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
refreshenv
pip install --pre caterpillar-hls
pip install .
caterpillar --version
kvm48 --version
