import datetime
import json
import re
import urllib.parse
from typing import Any, Dict, List, Union

import arrow
import attrdict
import requests


# Types
Datetime = Union[datetime.datetime, arrow.Arrow]
VOD = attrdict.AttrDict

# API constants
API_ENDPOINT = 'https://plive.48.cn/livesystem/api/live/v1/memberLivePage'
API_HEADERS = {
    'Content-Type': 'application/json',
    'os': 'ios',
    'version': '5.2.0',
}
API_LIMIT = 100
RESOURCE_BASE_URL = 'https://source.48.cn/'


class APIException(Exception):

    def __init__(self, payload: Dict[str, Any], exc: Exception):
        self._payload = payload
        self._exc = exc

    def __str__(self) -> str:
        http_part = 'POST %s %s' % (API_ENDPOINT, json.dumps(self._payload, separators=(',', ':')))
        exc_part = '%s: %s' % (type(self._exc).__name__, str(self._exc))
        return '%s: %s' % (http_part, exc_part)


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
def list_vods(from_: Datetime, to_: Datetime, *,
              member_id: int = 0, group_id: int = 0) -> List[VOD]:
    from_ms = _epoch_ms(from_)
    to_ms = _epoch_ms(to_)
    while from_ms < to_ms:
        try:
            payload = {
                'type': 0,
                'memberId': member_id,
                'groupId': group_id,
                'lastTime': to_ms,
                'limit': API_LIMIT,
            }
            r = requests.post(API_ENDPOINT, headers=API_HEADERS, json=payload, timeout=5)
            vod_objs = r.json()['content']['reviewList']
        except Exception as exc:
            raise APIException(payload, exc)

        if not vod_objs:
            break

        for vod_obj in vod_objs:
            v = attrdict.AttrDict(vod_obj)
            to_ms = v.startTime
            if v.startTime < from_ms:
                continue

            m = re.match(r'^(.+)(的直播间|的电台)', v.title)
            if not m:
                continue
            yield attrdict.AttrDict({
                'id': v.liveId,
                'member_id': int(v.memberId),
                'room_id': int(v.roomId),
                'type': '直播' if '直播' in m.group(2) else '电台',
                'name': m.group(1),
                'title': v.subTitle,
                'start_time': arrow.get(v.startTime / 1000).to('Asia/Shanghai'),
                'vod_url': _resolve_resource_url(v.streamPath),
                'danmaku_url': _resolve_resource_url(v.lrcPath),
            })
