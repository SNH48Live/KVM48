import os

import pytest


def pytest_configure():
    os.environ["TEST"] = "1"


@pytest.fixture(scope="session")
def database():
    from database import PerfVOD, db, init_database

    try:
        init_database()
        PerfVOD.create(
            canon_id="324479006241787906",
            l4c_club_id=1,
            l4c_id=2777,
            title="X队出道四周年",
            subtitle="TEAM X剧场公演",
            start_time=1555843500,
            sd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-liuchang/324479006241787906.m3u8",
            hd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006241787906.m3u8",
            fhd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006241787906.m3u8",
        )
        PerfVOD.create(
            canon_id="326091353251188736",
            l4c_club_id=1,
            l4c_id=2774,
            title="莫寒咖啡店生日会",
            subtitle="参加成员：莫寒",
            start_time=1555836300,
            sd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-liuchang/326091353251188736.m3u8",
            hd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/326091353251188736.m3u8",
            fhd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/326091353251188736.m3u8",
        )
        PerfVOD.create(
            canon_id="324479006245982208",
            l4c_club_id=1,
            l4c_id=2772,
            title="《重生计划》剧场公演",
            subtitle="莫寒生日公演",
            start_time=1555825500,
            sd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-liuchang/324479006245982208.m3u8",
            hd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006245982208.m3u8",
            fhd_stream="http://cychengyuan-vod.48.cn/snh/20190421/9999-gaoqing/324479006245982208.m3u8",
        )
        PerfVOD.create(
            canon_id="324918581187645440",
            l4c_club_id=2,
            l4c_id=2775,
            title="《UNIVERSE》剧场公演",
            subtitle="TeamE剧场公演",
            start_time=1555845900,
            sd_stream="http://cychengyuan-vod.48.cn/bej/20190421/9999-liuchang/324918581187645440.m3u8",
            hd_stream="http://cychengyuan-vod.48.cn/bej/20190421/9999-gaoqing/324918581187645440.m3u8",
            fhd_stream="http://cychengyuan-vod.48.cn/bej/20190421/9999-gaoqing/324918581187645440.m3u8",
        )
        PerfVOD.create(
            canon_id="324479006241787904",
            l4c_club_id=3,
            l4c_id=2773,
            title="《Fiona.N》剧场公演",
            subtitle="孙馨生日公演",
            start_time=1555826400,
            sd_stream="http://cychengyuan-vod.48.cn/gnz/20190421/9999-liuchang/324479006241787904.m3u8",
            hd_stream="http://cychengyuan-vod.48.cn/gnz/20190421/9999-gaoqing/324479006241787904.m3u8",
            fhd_stream="http://cychengyuan-vod.48.cn/gnz/20190421/9999-gaoqing/324479006241787904.m3u8",
        )
        yield
    finally:
        PerfVOD.delete().execute()
