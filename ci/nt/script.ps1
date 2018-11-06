Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
refreshenv

chcp 65001
$env:PYTHONIOENCODING = "utf-8"

@'
group_id: 10
names:
- 陈观慧
- 陈思
- 戴萌
- 孔肖吟
- 李宇琪
- 莫寒
- 钱蓓婷
- 邱欣怡
- 吴哲晗
- 徐晨辰
- 许佳琪
- 张语格
span: 3
named_subdirs: true
update_checks: off
editor: cat
perf:
  span: 7
'@ | Out-File -Encoding UTF8 kvm48-config.yml

kvm48 --debug --config kvm48-config.yml
if (!$?) { throw "kvm48 failed with status $LastExitCode" }
kvm48 --debug --config kvm48-config.yml --from 2018-10-25 --to 2018-10-27
if (!$?) { throw "kvm48 failed with status $LastExitCode" }
kvm48 --debug --config kvm48-config.yml --mode perf --dry
if (!$?) { throw "kvm48 failed with status $LastExitCode" }
kvm48 --debug --config kvm48-config.yml --mode perf --from 2018-06-09 --to 2018-06-09
if (!$?) { throw "kvm48 failed with status $LastExitCode" }
