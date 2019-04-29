import graphene.test
import pytest

from schema import schema


@pytest.fixture(scope="module")
def client(database):
    return graphene.test.Client(schema)


def test_query_perfvod(client):
    assert client.execute(
        '{ perfVod(id: "324479006245982208") { id l4cClubId l4cId l4cUrl group title subtitle startTime sdStream hdStream fhdStream bestStream } }'
    ) == {
        "data": {
            "perfVod": {
                "id": "324479006245982208",
                "l4cClubId": 1,
                "l4cId": 2772,
                "l4cUrl": "https://live.48.cn/Index/invedio/club/1/id/2772",
                "group": "SNH48",
                "title": "《重生计划》剧场公演",
                "subtitle": "莫寒生日公演",
                "startTime": 1555825500,
                "sdStream": "http://cychengyuan-vod.48.cn/snh/20190421/9999-liuchang/324479006245982208.m3u8",
                "hdStream": "http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006245982208.m3u8",
                "fhdStream": "http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006245982208.m3u8",
                "bestStream": "http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006245982208.m3u8",
            }
        }
    }
    assert client.execute('{ perfVod(id: "0") { title subtitle } }') == {
        "data": {"perfVod": None}
    }


def test_query_perfvods_by_ids(client):
    assert client.execute(
        '{ perfVods(ids: ["324479006241787906", "326091353251188736", "324479006245982208", "0"]) { title subtitle } }'
    ) == {
        "data": {
            "perfVods": [
                {"title": "X队出道四周年", "subtitle": "TEAM X剧场公演"},
                {"title": "莫寒咖啡店生日会", "subtitle": "参加成员：莫寒"},
                {"title": "《重生计划》剧场公演", "subtitle": "莫寒生日公演"},
                None,
            ]
        }
    }


def test_query_perfvods_by_time_range(client):
    assert client.execute("{ perfVods(from: 0, to: 0) { id startTime } }") == {
        "data": {"perfVods": []}
    }
    assert client.execute(
        "{ perfVods(from: 1555776000, to: 1555840800) { id startTime } }"
    ) == {
        "data": {
            "perfVods": [
                {"id": "324479006245982208", "startTime": 1555825500},
                {"id": "324479006241787904", "startTime": 1555826400},
                {"id": "326091353251188736", "startTime": 1555836300},
            ]
        }
    }
    assert client.execute(
        "{ perfVods(from: 1555776000, to: 1555840800, group: SNH48) { id startTime } }"
    ) == {
        "data": {
            "perfVods": [
                {"id": "324479006245982208", "startTime": 1555825500},
                {"id": "326091353251188736", "startTime": 1555836300},
            ]
        }
    }
    assert client.execute(
        "{ perfVods(from: 1555776000, to: 1555840800, group: BEJ48) { id startTime } }"
    ) == {"data": {"perfVods": []}}
    assert client.execute(
        "{ perfVods(from: 1555776000, to: 1555840800, group: GNZ48) { id startTime } }"
    ) == {"data": {"perfVods": [{"id": "324479006241787904", "startTime": 1555826400}]}}
