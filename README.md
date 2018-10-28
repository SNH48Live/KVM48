<h1 align="center"><img src="https://raw.githubusercontent.com/SNH48Live/KVM48/master/assets/logo.png" width="150" height="150" alt="KVM48"></h1>

<p align="center">
  <a href="https://pypi.python.org/pypi/KVM48"><img src="https://img.shields.io/pypi/v/KVM48.svg?maxAge=3600" alt="pypi"></a>
  <img src="https://img.shields.io/badge/python-3.6,%203.7-blue.svg?maxAge=86400" alt="python: 3.6, 3.7">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg?maxAge=2592000" alt="license: MIT">
  <img src="https://travis-ci.org/SNH48Live/KVM48.svg?branch=master" alt="build status">
</p>

KVM48, the Koudai48 VOD Manager. It is capable of downloading all streaming VODs of a set of monitored members in a specified date range.

Not to be confused with [KVM for kernel version 4.8](https://git.kernel.org/pub/scm/virt/kvm/kvm.git/tag/?h=kvm-4.8-3).

KVM48 is supported on macOS, Linux, other Unix-like systems, and Windows 10.

## Contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Invocation examples](#invocation-examples)
- [Privacy](#privacy)
- [Roadmap](#roadmap)
- [Reporting bugs](#reporting-bugs)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- Python 3.6 or later;
- [`aria2`](https://aria2.github.io/), KVM48's downloader of choice;
- [`caterpillar`](https://github.com/zmwangx/caterpillar), optional dependency for downloading M3U8/HLS VODs (`pip install caterpillar-hls`).

## Installation

```
pip install KVM48
```

## Usage

```console
$ kvm48 --help
usage: kvm48 [-h] [-f FROM] [-t TO] [-s SPAN] [-n] [--config CONFIG] [--edit]
             [--version] [--debug]

KVM48, the Koudai48 VOD Manager.

KVM48 downloads all streaming VODs of monitored members in a specified
date range. Monitored members and other options are configured through
the YAML configuration file

  <An OS and environment dependent path ending in config.yml>

or through a different configuration file specified with the --config
option.

The date range is determined as follows. All date and time are processed
in China Standard Time (UTC+08:00). --from and --to are specified in the
YYYY-MM-DD or MM-DD format.

- If both --from and --to are specified, use those;

- If --to is specified and --from is not, determine the date span
  through --span and the `span' config option (the former takes
  priority), then let the date range be `span' number of days
  (inclusive) ending in the --to date.

  For instance, if --to is 2018-02-18 and span is 7, then the date range
  is 2018-02-12 to 2018-02-18.

- If --from is specified and --to is not, then

  - If --span is explicitly specified on the command line, let the date
    range be `span' number of days starting from the --from date.

  - Otherwise, let the date range be the --from date to today (in
    UTC+08:00).

- If neither --from nor --to is specified, use today (in UTC+08:00) as
  the to date, and determine span in the same way as above.

KVM48 uses aria2 for direct downloads. Certain aria2c options, e.g.,
--max-connection-per-server=16, are enforced within kvm48; most options
should be configured directly in the aria2 config file.

KVM48 optionally uses caterpillar[1] as the M3U8/HLS downloader.
caterpillar is built on top of FFmpeg, the Swiss army knife of
multimedia processing, but it is specifically engineered to not produce
scrambled files when there are timestamp discontinuities or
irregularities in the source, which is all too common with Koudai48's
livestreaming infrastructure. If M3U8 streams are detected and
caterpillar is either not found or does not meet the minimum version
requirement, the URLs and supposed paths are written to disk for
postprocessing at the user's discretion.

[1] https://github.com/zmwangx/caterpillar

optional arguments:
  -h, --help            show this help message and exit
  -f FROM, --from FROM  starting day of date range
  -t TO, --to TO        ending day of date range
  -s SPAN, --span SPAN  number of days in date range
  -n, --dry             print URL & filename combos but do not download
  --config CONFIG       use this config file instead of the default
  --edit                open text editor to edit the config file
  --version             show program's version number and exit
  --debug
```

## Configuration

Configuration options are explained in the configuration template dumped
to `~/.config/kvm48/config.yml` upon first execution:

```yml
# ID of group to monitor, if all members you monitor are in a single
# group (this may save you a few API requests each time). Leave as 0 if
# you want to monitor multiple groups.
#
# Group IDs:
# - SNH48: 10;
# - BEJ48: 11;
# - GNZ48: 12;
# - SHY48: 13;
# - CKG48: 14.
group_id: 0

# Names of members to monitor and download.
#
# Example:
# names:
# - 莫寒
# - 张语格
names:

# Default time span (inclusive), in days, to check for VODs.
#
# By default, the last day to check is today, and the default time span
# is 1 day (inclusive), which means only VODs from today are checked. If
# the span is set to 2, then VODs from both yesterday and today are
# checked. So on and so forth.
#
# The date range could be customized on the command line via --from,
# --to, and --span.
span: 1

# Destination directory for downloaded VODs. Tilde expansion is allowed.
# The default is the current working directory.
#
# Example:
# directory: ~/Downloads
directory:

# File naming pattern. The following replacement strings are available:
# - %(date)s: date in the form YYYY-MM-DD, e.g. 2018-02-11;
# - %(date_c)s: compact date in the form YYYYMMDD, e.g., 20180211;
# - %(datetime)s: starting datetime in the form YYYY-MM-DD HH.MM.SS, e.g. 2018-02-11 18.57.32;
# - %(datetime_c)s: compact starting datetime in the form YYYYMMDDHHMMSS, e.g., 20180211185732;
# - %(id)s: server-assigned alphanumeric VOD ID, 5a80219c0cf29aa343fbe009;
# - %(name)s: member name, e.g., 莫寒;
# - %(type)s: type of the VOD, either 直播 or 电台;
# - %(title)s: title of the VOD, e.g. "一人吃火锅的人生成就(๑˙ー˙๑)";
# - %(ext)s: extension of the file (without leading dot), e.g. mp4;
# - %%: a literal percent sign should be escaped like this.
#
# Note that kvm48 handles filename conflicts automatically by appending
# numbers to filenames.
#
# The default pattern is
#   %(date_c)s %(name)s口袋%(type)s %(title)s.%(ext)s
# An example file name produced by this pattern is
#   20180211 莫寒口袋直播 一人吃火锅的人生成就(๑˙ー˙๑).mp4
naming:

# Whether to put VODs in named subdirectories. If turned on, each member
# will have her own subdirectory named after her where all her VODs will
# go. Default is off.
#
# New in v0.3.
# named_subdirs: off

# Whether to allow daily update checks for KVM48. Default is on.
# update_checks: on
```

Here is a sample configuration for downloading the VODs of Team SⅡ members daily:

```yml
# SNH48
group_id: 10
# Team SⅡ members
names:
- 陈观慧
- 陈思
- 成珏
- 戴萌
- 蒋芸
- 孔肖吟
- 李宇琪
- 刘增艳
- 吕一
- 莫寒
- 潘燕琦
- 钱蓓婷
- 邱欣怡
- 邵雪聪
- 孙芮
- 温晶婕
- 吴哲晗
- 徐晨辰
- 许佳琪
- 徐伊人
- 徐子轩
- 袁丹妮
- 袁雨桢
- 张语格
- 赵晔
# Download VODs from the same day and the day before by default.
span: 2
# Current working directory by default; might want to customize to a fixed destination.
directory:
# Just use the default naming scheme.
naming:
named_subdirs: on
```

## Invocation examples

We assume the sample configuration above (in particular, `span` is 2) in the following examples.

- The default (yesterday and today):

  ```console
  $ kvm48
  Searching for VODs in the date range 2018-10-27 to 2018-10-28 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  http://live.us.sinaimg.cn/004p0w5ijx07oJdYVaXm070d010001YY0k01.m3u8	陈思/20181027 陈思口袋直播 在飞去养生前的一小会直播～.mp4	*
  http://live.us.sinaimg.cn/004xES4bjx07oJHuTXfW070d010004sz0k01.m3u8	戴萌/20181027 戴萌口袋直播 嘿~~.mp4	*
  No new direct downloads.
  2 M3U8 VODs to download, total size unknown

  Processing M3U8 downloads with caterpillar...
  ...

  All is well.
  ```

- A rerun, with no new VODs to download:

  ```console
  $ kvm48
  Searching for VODs in the date range 2018-10-27 to 2018-10-28 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  http://live.us.sinaimg.cn/004p0w5ijx07oJdYVaXm070d010001YY0k01.m3u8	陈思/20181027 陈思口袋直播 在飞去养生前的一小会直播～.mp4
  http://live.us.sinaimg.cn/004xES4bjx07oJHuTXfW070d010004sz0k01.m3u8	戴萌/20181027 戴萌口袋直播 嘿~~.mp4
  No new direct downloads.
  No new M3U8 downloads.
  All is well.
  ```

- Past seven days (including today):

  ```console
  $ kvm48 -s 7
  Searching for VODs in the date range 2018-10-22 to 2018-10-28 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/4162b95b-b669-4fae-98ed-ab43d5e20a12.mp4	莫寒/20181022 莫寒口袋直播 随时准备关的缘分直播.mp4	*
  https://mp4.48.cn/live/b7f0a71d-1bd4-4aba-aae9-3e9e30757f64.mp4	莫寒/20181022 莫寒口袋直播 随时准备关的缘分直播 (1).mp4	*
  https://mp4.48.cn/live/985e8fb8-9977-41ec-90e0-35e51bf2b5d4.mp4	莫寒/20181022 莫寒口袋直播 随时准备关的缘分直播 (2).mp4	*
  https://mp4.48.cn/live/2051c9c0-4ff0-4d6e-948d-1c0b79e22ce9.mp4	莫寒/20181022 莫寒口袋直播 随时准备关的缘分直播 (3).mp4	*
  http://live.us.sinaimg.cn/001gGvxvjx07oBw9B0NG070d010002DL0k01.m3u8	吴哲晗/20181022 吴哲晗口袋直播 comeon.mp4	*
  http://live.us.sinaimg.cn/003N7ccljx07oBASLvzN070d010008G80k01.m3u8	戴萌/20181022 戴萌口袋直播 我正在看你看我.mp4	*
  https://mp4.48.cn/live/85f20272-b4bc-47f9-ae51-adab38e503f9.mp4	刘增艳/20181022 刘增艳口袋直播 等待.mp4	*
  https://mp4.48.cn/live/cbc5b0a7-f0fc-44a2-8a19-392bc0b9ceeb.mp4	徐子轩/20181022 徐子轩口袋直播 突然出现.mp4	*
  https://mp4.48.cn/live/f87b01ba-ed45-4efd-bc40-90e1f7ed9aa7.mp4	孔肖吟/20181023 孔肖吟口袋直播 嘻嘻.mp4	*
  https://mp4.48.cn/live/0f22303c-864e-4c5b-8564-207e12525e73.mp4	徐子轩/20181023 徐子轩口袋电台 回家路上随便聊？.mp4	*
  https://mp4.48.cn/live/d763badd-5c44-451d-9b8e-8a89aff03521.mp4	徐子轩/20181024 徐子轩口袋电台 晚上好啊.mp4	*
  https://mp4.48.cn/live/3d9a1576-3a7f-4744-9d54-30221b7c9b25.mp4	徐子轩/20181024 徐子轩口袋电台 晚上好啊 (1).mp4	*
  https://mp4.48.cn/live/95a52feb-0045-4790-99c7-64653b9c576f.mp4	徐子轩/20181024 徐子轩口袋电台 晚上好啊 (2).mp4	*
  https://mp4.48.cn/live/52c8d150-638d-4991-a85f-af203045c4a8.mp4	徐子轩/20181024 徐子轩口袋电台 晚上好啊 (3).mp4	*
  https://mp4.48.cn/live/008e8544-06f3-46e3-8908-b1bddd29441a.mp4	徐子轩/20181024 徐子轩口袋电台 晚上好啊 (4).mp4	*
  https://mp4.48.cn/live/c5d8793a-e977-436b-b780-2fa12c4290cf.mp4	徐子轩/20181025 徐子轩口袋电台 晚上好啊.mp4	*
  http://live.us.sinaimg.cn/002LOZmTjx07oGlxZ5xC070d010006Dg0k01.m3u8	徐伊人/20181025 徐伊人口袋直播 聊会.mp4	*
  https://mp4.48.cn/live/29764e24-9d7e-4b3a-8a7f-68a40544c2b4.mp4	吴哲晗/20181025 吴哲晗口袋直播 comeon.mp4	*
  http://live.us.sinaimg.cn/004p0w5ijx07oJdYVaXm070d010001YY0k01.m3u8	陈思/20181027 陈思口袋直播 在飞去养生前的一小会直播～.mp4	*
  http://live.us.sinaimg.cn/004xES4bjx07oJHuTXfW070d010004sz0k01.m3u8	戴萌/20181027 戴萌口袋直播 嘿~~.mp4	*
  15 direct downloads, total size: 3,596,660,076 bytes
  5 M3U8 VODs to download, total size unknown

  Processing direct downloads with aria2...
  ...

  Processing M3U8 downloads with caterpillar...
  ...

  All is well.
  ```

- Since the beginning of the year:

  ```console
  $ kvm48 -f 01-01
  Searching for VODs in the date range 2018-01-01 to 2018-10-28 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  ..............................
  Searching for VODs before 2018-02-04 20:53:59
  ....
  https://mp6.48.cn/live/f13925de-b8ee-4e8b-97fa-6fb37e8db403.mp4	张语格/20180101 张语格口袋电台 2018.mp4	*
  ...
  http://live.us.sinaimg.cn/004xES4bjx07oJHuTXfW070d010004sz0k01.m3u8	戴萌/20181027 戴萌口袋直播 嘿~~.mp4	*
  844 direct downloads, total size: 315,911,948,927 bytes (size of 27 files could not be determined)
  172 M3U8 VODs to download, total size unknown
  ...
  ```

- An absolute date range:

  ```console
  $ kvm48 --from 10-20 --to 10-21
  Searching for VODs in the date range 2018-10-20 to 2018-10-21 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/47ffcd2b-d8cd-4ee4-8317-bc488f250aa3.mp4	张语格/20181020 张语格口袋电台 深夜电台.mp4	*
  https://mp4.48.cn/live/a7f03d65-2eed-418a-a203-9fce7c2b1698.mp4	莫寒/20181020 莫寒口袋直播 随时准备关的缘分直播.mp4	*
  https://mp4.48.cn/live/16f05a05-a49f-436f-a7a2-04210a67b46a.mp4	刘增艳/20181020 刘增艳口袋直播 每周增情实感问答.mp4	*
  https://mp4.48.cn/live/ebb8a02c-97f5-48d1-8b4b-b2c5aa7400ba.mp4	戴萌/20181020 戴萌口袋直播 我正在看你看我.mp4	*
  https://mp4.48.cn/live/43a7b44a-d303-4ace-b478-4ca444c4d923.mp4	陈观慧/20181021 陈观慧口袋电台 🌙minilive要唱什么눈_눈.mp4	*
  https://mp4.48.cn/live/12b76ba9-1350-496a-bc94-a9c59a3f5038.mp4	刘增艳/20181021 刘增艳口袋直播 每周增情实感问答.mp4	*
  https://mp4.48.cn/live/973e8957-ff37-45f7-8e6d-82a250cdf451.mp4	钱蓓婷/20181021 钱蓓婷口袋直播 你倒是进来看看啊.mp4	*
  https://mp4.48.cn/live/a74b3083-8158-4dfb-ae28-f25a4957b1b6.mp4	钱蓓婷/20181021 钱蓓婷口袋直播 你倒是进来看看啊 (1).mp4	*
  8 direct downloads, total size: 2,302,573,126 bytes
  No new M3U8 downloads.
  ...
  ```

- Dry run (print URL & filename combos, but do not download):

  ```console
  $ kvm48 --dry --from 10-20 --to 10-21
  Searching for VODs in the date range 2018-10-20 to 2018-10-21 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/47ffcd2b-d8cd-4ee4-8317-bc488f250aa3.mp4	张语格/20181020 张语格口袋电台 深夜电台.mp4	*
  https://mp4.48.cn/live/a7f03d65-2eed-418a-a203-9fce7c2b1698.mp4	莫寒/20181020 莫寒口袋直播 随时准备关的缘分直播.mp4	*
  https://mp4.48.cn/live/16f05a05-a49f-436f-a7a2-04210a67b46a.mp4	刘增艳/20181020 刘增艳口袋直播 每周增情实感问答.mp4	*
  https://mp4.48.cn/live/ebb8a02c-97f5-48d1-8b4b-b2c5aa7400ba.mp4	戴萌/20181020 戴萌口袋直播 我正在看你看我.mp4	*
  https://mp4.48.cn/live/43a7b44a-d303-4ace-b478-4ca444c4d923.mp4	陈观慧/20181021 陈观慧口袋电台 🌙minilive要唱什么눈_눈.mp4	*
  https://mp4.48.cn/live/12b76ba9-1350-496a-bc94-a9c59a3f5038.mp4	刘增艳/20181021 刘增艳口袋直播 每周增情实感问答.mp4	*
  https://mp4.48.cn/live/973e8957-ff37-45f7-8e6d-82a250cdf451.mp4	钱蓓婷/20181021 钱蓓婷口袋直播 你倒是进来看看啊.mp4	*
  https://mp4.48.cn/live/a74b3083-8158-4dfb-ae28-f25a4957b1b6.mp4	钱蓓婷/20181021 钱蓓婷口袋直播 你倒是进来看看啊 (1).mp4	*
  8 direct downloads, total size: 2,302,573,126 bytes
  No new M3U8 downloads.
  ```

## Privacy

Starting with KVM48 v0.3, the application checks for update the first time you launch it on a calendar day so that improvements are adopted more quickly. This does mean hitting the update server, where your IP address may be anonymized (by stripping at least the last octet of an IPv4 address, or at least the last five hextets of an IPv6 address) and recorded to guage interest. Nothing else (other than the current version and possible new version) is transfered or recorded.

You may permanently turn off the update checks by adding `update_checks: off` to your config file.

## Roadmap

No plans at the moment.

## Reporting bugs

Please follow the instructions carefully.

- Run your problematic command **with the `--debug` option**. It is included for a reason. Without `--debug`, my hands are tied.
- Copy your **full command line**, as well as **the full output** (that is, from the first line to the last), and make a [gist](https://gist.github.com/) out of that. Report the URL of the gist.
- Copy the **full content of your configuration file** (the path can be found in `kvm48 --help`; look for `config.yml`), and make a gist out of that, too. Report the URL of the gist. (You may combine the two files in a single gist.)

**Note: Screenshots of your terminal are not acceptable for bug reports, especially not incomplete ones (95% of the case, unfortunately), and worse still if the font is awful** (notorious example: default font of Windows cmd.exe; also, I have to report that Ubuntu Mono isn't much better in my eyes). These waste everyone's time (guesswork, back and forth, etc.) and generally annoy the hell out of developers.

## License

Copyright © 2018 Zhiming Wang <pypi@snh48live.org>

The MIT License.
