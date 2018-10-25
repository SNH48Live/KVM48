import datetime
import json
import re
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Union

import arrow
import attrdict
import requests


# Types
Datetime = Union[datetime.datetime, arrow.Arrow]
VOD = attrdict.AttrDict

# API constants
API_ENDPOINT = "https://plive.48.cn/livesystem/api/live/v1/memberLivePage"
API_HEADERS = {"Content-Type": "application/json", "os": "ios", "version": "5.2.0"}
API_LIMIT = 100
RESOURCE_BASE_URL = "https://source.48.cn/"


class APIException(Exception):
    def __init__(self, payload: Dict[str, Any], exc: Exception):
        self._payload = payload
        self._exc = exc

    def __str__(self) -> str:
        http_part = "POST %s %s" % (
            API_ENDPOINT,
            json.dumps(self._payload, separators=(",", ":")),
        )
        exc_part = "%s: %s" % (type(self._exc).__name__, str(self._exc))
        return "%s: %s" % (http_part, exc_part)


def _epoch_ms(dt: Datetime) -> int:
    try:
        epoch_sec = dt.timestamp()
    except TypeError:
        epoch_sec = dt.timestamp
    return int(epoch_sec * 1000)


def _resolve_resource_url(url: str) -> str:
    return urllib.parse.urljoin(RESOURCE_BASE_URL, url)


# Generator function for VOD objects, each containing the following attributes:
# - id: str, server-assigned alphanumeric ID of the VOD;
# - member_id: int;
# - room_id: int;
# - type: str, '直播' or '电台';
# - name: str, name of member;
# - title: str;
# - start_time: arrow.Arrow, starting time in Asia/Shanghai zone (UTC+08:00);
# - vod_url: str;
# - danmaku_url: str.
# VODs are generated in reverse chronological order.
#
# - show_progress: whether to print progress info (currently just a dot
#   for each API request);
# - show_progress_threshold: how many seconds to wait before showing
#   progress info (because people don't care about progress if the call
#   returns before they're bored).
def list_vods(
    from_: Datetime,
    to_: Datetime,
    *,
    member_id: int = 0,
    group_id: int = 0,
    show_progress: bool = False,
    show_progress_threshold: float = 0
) -> List[VOD]:
    from_ms = _epoch_ms(from_)
    to_ms = _epoch_ms(to_)
    start_time = time.time()
    progress_written = False
    progress_dots = 0
    while from_ms < to_ms:
        try:
            if show_progress and time.time() - start_time >= show_progress_threshold:
                if progress_dots > 0 and progress_dots % 30 == 0:
                    sys.stderr.write(
                        "\nSearching for VODs before %s\n"
                        % (arrow.get(to_ms / 1000).to("Asia/Shanghai")).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )
                sys.stderr.write(".")
                sys.stderr.flush()
                progress_written = True
                progress_dots += 1
            payload = {
                "type": 0,
                "memberId": member_id,
                "groupId": group_id,
                "lastTime": to_ms,
                "limit": API_LIMIT,
            }
            # Gradually increase timeout, and only raise on the third
            # consecutive timeout.
            for attempt in range(3):
                try:
                    r = requests.post(
                        API_ENDPOINT,
                        headers=API_HEADERS,
                        json=payload,
                        timeout=5 + 2 * attempt,
                    )
                    break
                except requests.Timeout:
                    if attempt == 2:
                        raise
            vod_objs = r.json()["content"]["reviewList"]
        except Exception as exc:
            raise APIException(payload, exc)

        if not vod_objs:
            break

        for vod_obj in vod_objs:
            v = attrdict.AttrDict(vod_obj)
            to_ms = v.startTime
            if v.startTime < from_ms:
                continue

            m = re.match(r"^(.+)(的直播间|的电台)", v.title)
            if not m:
                continue
            yield attrdict.AttrDict(
                {
                    "id": v.liveId,
                    "member_id": int(v.memberId),
                    "room_id": int(v.roomId),
                    "type": "直播" if "直播" in m.group(2) else "电台",
                    "name": m.group(1),
                    "title": v.subTitle,
                    "start_time": arrow.get(v.startTime / 1000).to("Asia/Shanghai"),
                    "vod_url": _resolve_resource_url(v.streamPath),
                    "danmaku_url": _resolve_resource_url(v.lrcPath),
                }
            )
    if progress_written:
        sys.stderr.write("\n")
        sys.stderr.flush()
