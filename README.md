<h1 align="center"><img src="https://raw.githubusercontent.com/SNH48Live/KVM48/master/assets/logo.png" width="150" height="150" alt="KVM48"></h1>

<p align="center">
  <a href="https://pypi.python.org/pypi/KVM48"><img src="https://img.shields.io/pypi/v/KVM48.svg?maxAge=3600" alt="pypi"></a>
  <img src="https://img.shields.io/badge/python-3.4,%203.5,%203.6,%203.7-blue.svg?maxAge=86400" alt="python: 3.4, 3.5, 3.6, 3.7">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg?maxAge=2592000" alt="license: MIT">
</p>

KVM48, the Koudai48 VOD Manager. It is capable of downloading all streaming VODs of a set of monitored members in a specified date range.

Not to be confused with [KVM for kernel version 4.8](https://git.kernel.org/pub/scm/virt/kvm/kvm.git/tag/?h=kvm-4.8-3).

KVM48 is supported on macOS, Linux, and other Unix-like systems (including Windows Subsystem for Linux, aka WSL); it is neither tested nor supported on Windows NT.

## Contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Invocation examples](#invocation-examples)
- [Roadmap](#roadmap)
  - [Native M3U8 VOD support](#native-m3u8-vod-support)
  - [Livestream monitoring and recording](#livestream-monitoring-and-recording)
- [Reporting bugs](#reporting-bugs)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- Python 3.4 or later;
- [`aria2`](https://aria2.github.io/), KVM48's downloader of choice.

## Installation

```
pip install KVM48
```

## Usage

```console
$ kvm48 --help
usage: kvm48 [-h] [-f FROM] [-t TO] [-s SPAN] [--dry] [--config CONFIG]
             [--version] [--debug]

KVM48, the Koudai48 VOD Manager.

KVM48 downloads all streaming VODs of monitored members in a specified
date range. Monitored members and other options are configured through
the YAML configuration file

  $HOME/.config/kvm48/config.yml

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

KVM48 uses aria2 as the downloader. Certain aria2c options, e.g.,
--max-connection-per-server=16, are enforced within kvm48; most options
should be configured directly in the aria2 config file.

optional arguments:
  -h, --help            show this help message and exit
  -f FROM, --from FROM  starting day of date range
  -t TO, --to TO        ending day of date range
  -s SPAN, --span SPAN  number of days in date range
  --dry                 print URL & filename combos but do not download
  --config CONFIG       use this config file instead of the default
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
```

## Invocation examples

We assume the sample configuration above (in particular, `span` is 2) in the following examples.

- The default (yesterday and today):

  ```console
  $ kvm48
  Searching for VODs in the date range 2018-02-17 to 2018-02-18 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  http://live.us.sinaimg.cn/002Z5UtSjx07ifo9IbeD070d010002Xi0k01.m3u8	20180217 徐伊人口袋直播 。.m3u8
  https://mp4.48.cn/live/9227d780-2b0c-4d01-9c3d-8e37b6bbb2e4.mp4	20180217 徐伊人口袋直播 。.mp4
  http://live.us.sinaimg.cn/003gnLPMjx07ifGVgAfS070d01000cU60k01.m3u8	20180217 邵雪聪口袋直播 美丽的小公举聪聪来给你包大饺子了！.m3u8
  https://mp4.48.cn/live/e25a29a8-5cd0-46a7-a905-37e60d732593.mp4	20180217 赵晔口袋直播 直播龙猫十分钟.mp4
  https://mp4.48.cn/live/688579e2-4422-48af-8713-c1b0a525a686.mp4	20180217 徐子轩口袋电台 晚间电台.mp4
  https://mp4.48.cn/live/3982ee31-4985-4c67-8b4a-5139958b8d05.mp4	20180217 徐子轩口袋电台 晚间电台 (1).mp4
  https://mp4.48.cn/live/4b37e94a-dcd3-4b77-8136-b0569e0de25f.mp4	20180217 徐子轩口袋电台 晚间电台 (2).mp4
  https://mp4.48.cn/live/895845c6-bcdc-4cd6-9d6b-2f958bdd9c3c.mp4	20180218 温晶婕口袋直播 聊一小时.mp4
  ...
  ```

- Past seven days (including today):

  ```console
  $ kvm48 -s 7
  Searching for VODs in the date range 2018-02-12 to 2018-02-18 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  ...
  ```

- Since the beginning of the year:

  ```console
  $ kvm48 -f 01-01
  Searching for VODs in the date range 2018-01-01 to 2018-02-18 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/f13925de-b8ee-4e8b-97fa-6fb37e8db403.mp4	20180101 张语格口袋电台 2018.mp4
  ...
  https://mp4.48.cn/live/895845c6-bcdc-4cd6-9d6b-2f958bdd9c3c.mp4	20180218 温晶婕口袋直播 聊一小时.mp4
  ...
  ```

- An absolute date range:

  ```console
  $ kvm48 -f 02-10 -t 02-11
  Searching for VODs in the date range 2018-02-10 to 2018-02-11 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/e4d0dc08-abd1-468b-b8fe-2ee831709ecd.mp4	20180210 温晶婕口袋直播 duangduang洗澡.mp4
  ...
  https://mp4.48.cn/live/ffcfca63-e37f-4dcc-bc68-639ef223a648.mp4	20180211 戴萌口袋直播 尬聊一会会儿🤝.mp4
  ...
  ```

- Dry run (print URL & filename combos, but do not download):

  ```console
  $ kvm48 --dry -f 02-11 -t 02-11
  Searching for VODs in the date range 2018-02-11 to 2018-02-11 for: 陈观慧, 陈思, 成珏, 戴萌, 蒋芸, 孔肖吟, 李宇琪, 刘增艳, 吕一, 莫寒, 潘燕琦, 钱蓓婷, 邱欣怡, 邵雪聪, 孙芮, 温晶婕, 吴哲晗, 徐晨辰, 许佳琪, 徐伊人, 徐子轩, 袁丹妮, 袁雨桢, 张语格, 赵晔
  https://mp4.48.cn/live/a7f0ee95-b05d-439f-b0b0-67117ecb8aa3.mp4	20180211 莫寒口袋直播 一人吃火锅的人生成就(๑˙ー˙๑).mp4
  https://mp4.48.cn/live/82b50b91-28f8-4182-8ac0-3ca4d0202636.mp4	20180211 莫寒口袋直播 一人吃火锅的人生成就(๑˙ー˙๑) (1).mp4
  https://mp4.48.cn/live/4d846e49-4d51-4b39-8dda-742b459e2484.mp4	20180211 吕一口袋电台 到达重庆，来个电台抒发一下感情.mp4
  https://mp4.48.cn/live/637fc861-713f-4824-9c98-cb030c8e0cc3.mp4	20180211 温晶婕口袋直播 走进科学之duang去哪里了.mp4
  https://mp4.48.cn/live/be5d3a46-8638-4850-a4e3-10f029dd01ff.mp4	20180211 孙芮口袋直播 哈哈哈精致girl.mp4
  https://mp4.48.cn/live/ffcfca63-e37f-4dcc-bc68-639ef223a648.mp4	20180211 戴萌口袋直播 尬聊一会会儿🤝.mp4
  ```

## Roadmap

### Native M3U8 VOD support

Currently, when encountering M3U8 VOD URLs (from Yizhibo), KVM48 simply downloads them to disk like the MP4 VODs, rendering them useless. This is apparently not ideal.

I have already written an HLS downloader, [caterpillar](https://github.com/zmwangx/caterpillar) (which is based on FFmpeg, but parallelized and more resilient to crappy streams), in the past. The problem is integration: aria2c and caterpillar both produce helpful progress bars, but mixing the output streams of these two would be a nightmare.

A basic plan here is to implement multiplexing through tmux.

**Update.** Since v0.1.4, M3U8 entries are written to a manifest file, suitable for direct consumption with [caterpillar](https://github.com/zmwangx/caterpillar). Native support with duplexing won't come in the forseeable future.

### Livestream monitoring and recording

This is somewhat out of scope, but not hard to implement once we've figured out multiplexing.

## Reporting bugs

Please follow the instructions carefully.

- Run your problematic command **with the `--debug` option**. It is included for a reason. Without `--debug`, my hands are tied.
- Copy your **full command line**, as well as **the full output** (that is, from the first line to the last), and make a [gist](https://gist.github.com/) out of that. Report the URL of the gist.
- Copy the **full content of your configuration file** (the path can be found in `kvm48 --help`; look for `config.yml`), and make a gist out of that, too. Report the URL of the gist. (You may combine the two files in a single gist.)

**Note: Screenshots of your terminal are not acceptable for bug reports, especially not incomplete ones (95% of the case, unfortunately), and worse still if the font is awful** (notorious example: default font of Windows cmd.exe; also, I have to report that Ubuntu Mono isn't much better in my eyes). These waste everyone's time (guesswork, back and forth, etc.) and generally annoy the hell out of developers.

## License

Copyright © 2018 Zhiming Wang <pypi@snh48live.org>

The MIT License.
