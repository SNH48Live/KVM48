import datetime
import json
import re
import sys
import time
import urllib.parse
from typing import Any, Dict, Generator, List, Union

import arrow
import attrdict
import requests


# Types
Datetime = Union[datetime.datetime, arrow.Arrow]
VOD = attrdict.AttrDict

# API constants
MEMBER_VOD_LIST_URL = "https://pocketapi.48.cn/live/api/v1/live/getLiveList"
MEMBER_VOD_RESOLVE_URL = "https://pocketapi.48.cn/live/api/v1/live/getLiveOne"
PERF_VOD_LIST_URL = "https://pocketapi.48.cn/live/api/v1/live/getOpenLiveList"
PERF_VOD_RESOLVE_URL = "https://pocketapi.48.cn/live/api/v1/live/getOpenLiveOne"
API_HEADERS = {"Content-Type": "application/json"}
RESOURCE_BASE_URL = "https://source.48.cn/"


class APIException(Exception):
    def __init__(self, endpoint: str, payload: Dict[str, Any], exc: Exception):
        self._endpoint = endpoint
        self._payload = payload
        self._exc = exc

    def __str__(self) -> str:
        http_part = "POST %s %s" % (
            self._endpoint,
            json.dumps(self._payload, separators=(",", ":")),
        )
        exc_part = "%s: %s" % (type(self._exc).__name__, str(self._exc))
        return "%s: %s" % (http_part, exc_part)


class ProgressReporter:
    disabled = False
    threshold = 5  # show progress threshold, in seconds

    def __init__(self):
        self.count = 0
        self.pos = 0
        self.initiated = 0
        self.finalized = 0

    def __enter__(self):
        if self.disabled:
            return
        self.initiated = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.disabled:
            return
        self.finalize()

    def report(self, msg=None, force_msg=False):
        if (
            self.disabled
            or not self.initiated
            or (time.time() - self.initiated < self.threshold)
        ):
            return
        self.count += 1
        self.pos += 1
        sys.stderr.write(".")
        if msg and (force_msg or self.pos >= 30):
            sys.stderr.write("\n%s\n" % msg)
            self.pos = 0
        sys.stderr.flush()

    def finalize(self):
        if self.disabled or not self.initiated or self.finalized or self.count == 0:
            return
        sys.stderr.write("\n")
        sys.stderr.flush()
        self.finalized = time.time()


def call_api(endpoint, payload):
    # Gradually increase timeout, and only raise on the third
    # consecutive timeout.
    for attempt in range(3):
        try:
            return requests.post(
                endpoint, headers=API_HEADERS, json=payload, timeout=5 + 2 * attempt
            )
        except requests.Timeout:
            if attempt == 2:
                raise


def _resolve_resource_url(url: str) -> str:
    return urllib.parse.urljoin(RESOURCE_BASE_URL, url)


# Generator function for VOD objects, each containing the following attributes:
# - id: str, server-assigned alphanumeric ID of the VOD;
# - member_id: int;
# - type: str, '直播' or '电台';
# - name: str, name of member;
# - title: str;
# - start_time: arrow.Arrow, starting time in Asia/Shanghai zone (UTC+08:00);
# - vod_url: str, to be populated by resolve_member_vods;
# - danmaku_url: str, to be populated by resolve_member_vods.
# VODs are generated in reverse chronological order.
def list_member_vods(
    from_: Datetime,
    to_: Datetime,
    *,
    member_id: int = 0,
    team_id: int = 0,
    group_id: int = 0,
) -> Generator[VOD, None, None]:
    from_ = arrow.get(from_).to("Asia/Shanghai")
    to_ = arrow.get(to_).to("Asia/Shanghai")
    next_id = 0
    earliest_start_time = to_
    with ProgressReporter() as reporter:
        while earliest_start_time > from_:
            reporter.report(
                "Searching for VODs before %s"
                % earliest_start_time.strftime("%Y-%m-%d %H:%M:%S")
            )

            try:
                r = call_api(
                    MEMBER_VOD_LIST_URL,
                    {
                        "type": 0,
                        "memberId": member_id,
                        "teamId": team_id,
                        "groupId": group_id,
                        "next": next_id,
                    },
                )
                content = r.json()["content"]
                vod_objs = content["liveList"]
                next_id = content["next"]
            except Exception as exc:
                reporter.finalize()
                raise APIException(MEMBER_VOD_LIST_URL, payload, exc)

            if not vod_objs:
                break

            for vod_obj in vod_objs:
                v = attrdict.AttrDict(vod_obj)
                start_time = arrow.get(int(v.ctime) / 1000).to("Asia/Shanghai")
                earliest_start_time = min(earliest_start_time, start_time)
                if not from_ <= start_time < to_:
                    continue

                m = re.match(r"^(?P<group>\w+)-(?P<member>\w+)$", v.userInfo.nickname)
                if not m:
                    continue
                name = m.group("member")
                yield attrdict.AttrDict(
                    {
                        "id": v.liveId,
                        "member_id": int(v.userInfo.userId),
                        "type": "直播" if v.liveType == 1 else "电台",
                        "name": name,
                        "title": v.title,
                        "start_time": start_time,
                        "vod_url": None,
                        "danmaku_url": None,
                    }
                )


# Populate vod_url and danmaku_url attributes to each VOD object, given
# a list of performance VOD objects.
def resolve_member_vods(vods: List[VOD]) -> None:
    with ProgressReporter() as reporter:
        for vod in vods:
            reporter.report()

            try:
                r = call_api(MEMBER_VOD_RESOLVE_URL, {"liveId": vod.id})
                content = r.json()["content"]
            except Exception as exc:
                reporter.finalize()
                raise APIException(PERF_VOD_RESOLVE_URL, payload, exc)

            vod.vod_url = _resolve_resource_url(content["playStreamPath"])
            if "msgFilePath" in content:
                vod.danmaku_url = _resolve_resource_url(content["msgFilePath"])


# Generator function for performance VOD objects, each containing the
# following attributes: id, teams, title, name, start_time, and
# vod_url. vod_url is initially None and needs to be resolved with
# resolve_perf_vods.
#
# "name" is the title of the stage (None if cannot be determined), e.g.,
# "美丽48区".
def list_perf_vods(
    from_: Datetime, to_: Datetime, *, group_id: int = 0
) -> Generator[VOD, None, None]:
    from_ = arrow.get(from_).to("Asia/Shanghai")
    to_ = arrow.get(to_).to("Asia/Shanghai")
    next_id = 0
    earliest_start_time = to_
    seen_ids = set()  # used for deduplication, because the API is crap
    with ProgressReporter() as reporter:
        while earliest_start_time > from_:
            reporter.report(
                "Searching for VODs before %s"
                % earliest_start_time.strftime("%Y-%m-%d %H:%M:%S")
            )

            try:
                r = call_api(
                    PERF_VOD_LIST_URL,
                    {"groupId": group_id, "next": next_id, "record": True},
                )
                content = r.json()["content"]
                vod_objs = content["liveList"]
                next_id = content["next"]
            except Exception as exc:
                reporter.finalize()
                raise APIException(PERF_VOD_LIST_URL, payload, exc)

            if not vod_objs:
                break

            for vod_obj in vod_objs:
                v = attrdict.AttrDict(vod_obj)
                if v.liveId in seen_ids:
                    continue
                start_time = arrow.get(int(v.stime) / 1000).to("Asia/Shanghai")
                earliest_start_time = min(earliest_start_time, start_time)
                if not from_ <= start_time < to_:
                    continue

                m = re.search(r"《(?P<name>.*?)》", v.title)
                name = m.group("name") if m else None
                # TODO: refine teams attribute.
                yield attrdict.AttrDict(
                    {
                        "id": v.liveId,
                        "teams": [t.teamName for t in v.teamList],
                        "title": v.title.strip(),
                        "name": name,
                        "start_time": start_time,
                    }
                )
                seen_ids.add(v.liveId)


# Add vod_url attribute to each VOD object, given a list of performance
# VOD objects.
def resolve_perf_vods(vods: List[VOD]) -> None:
    with ProgressReporter() as reporter:
        for vod in vods:
            reporter.report()

            try:
                r = call_api(PERF_VOD_RESOLVE_URL, {"liveId": vod.id})
                content = r.json()["content"]
            except Exception as exc:
                reporter.finalize()
                raise APIException(PERF_VOD_RESOLVE_URL, payload, exc)

            streams = {s["streamName"]: s["streamPath"] for s in content["playStreams"]}
            vod.vod_url = _resolve_resource_url(
                streams.get("超清") or streams.get("高清") or streams.get("标清")
            )
