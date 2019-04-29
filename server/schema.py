import logging

import graphene
import peewee
from graphql import GraphQLError

from database import PerfVOD as PerfVODModel, db


SCHEMA_REVISION_NUMBER = "20190429.1"


class GraphQLErrorFilter(logging.Filter):
    def filter(self, record):
        if record.exc_info:
            _, exc, _ = record.exc_info
            return not isinstance(exc, GraphQLError)
        else:
            return True


# Disable GraphQLError logging.
logging.getLogger("graphql.execution.executor").addFilter(GraphQLErrorFilter())
# Disable reprinting of error tracebacks in
# https://github.com/graphql-python/graphql-core/blob/d8e9d3abe7c209eb2f51cf001402783bfd480596/graphql/execution/utils.py#L150-L156
logging.getLogger("graphql.execution.utils").setLevel(logging.CRITICAL)


class Group(graphene.Enum):
    SNH48 = 1
    BEJ48 = 2
    GNZ48 = 3
    SHY48 = 4
    CKG48 = 5


class PerfVOD(graphene.ObjectType):
    id = graphene.NonNull(
        graphene.String, description='Canonical VOD ID, e.g., `"324479006245982208"`.'
    )
    l4c_club_id = graphene.NonNull(
        graphene.Int,
        description="Club ID used on live.48.cn, e.g., `1` in <https://live.48.cn/Index/invedio/club/1/id/2772>. "
        "`1` for SNH48, `2` for BEJ48, `3` for GNZ48, `4` for SHY48, `5` for CKG48.",
    )
    l4c_id = graphene.NonNull(
        graphene.Int,
        description="CMS-assigned VOD index used on live.48.cn, e.g., `2772` in <https://live.48.cn/Index/invedio/club/1/id/2772>.",
    )
    l4c_url = graphene.NonNull(
        graphene.String,
        description="live.48.cn page URL, e.g. <https://live.48.cn/Index/invedio/club/1/id/2772>.",
    )
    group = graphene.NonNull(Group, description="Group corresponding to `club_id`.")
    title = graphene.NonNull(graphene.String)
    subtitle = graphene.String()
    start_time = graphene.NonNull(
        graphene.Int,
        description="Epoch timestamp of the performance/event's starting time.",
    )
    sd_stream = graphene.String(description="URL of 普清 stream, usually 480p.")
    hd_stream = graphene.String(description="URL of 高清 stream, usually 720p.")
    fhd_stream = graphene.String(
        description="URL of 超清 stream, supposedly 1080p. Obselete and basically an alias for `hd_stream` as of November, 2018."
    )
    best_stream = graphene.NonNull(
        graphene.String, description="URL of the highest quality stream."
    )

    @classmethod
    def from_database_model(cls, v: PerfVODModel):
        return cls(
            id=v.canon_id,
            l4c_club_id=v.l4c_club_id,
            l4c_id=v.l4c_id,
            l4c_url=v.l4c_url,
            group=Group.get(v.l4c_club_id),
            title=v.title,
            subtitle=v.subtitle,
            start_time=v.start_time,
            sd_stream=v.sd_stream,
            hd_stream=v.hd_stream,
            fhd_stream=v.fhd_stream,
            best_stream=v.fhd_stream or v.hd_stream or v.sd_stream,
        )

    class Meta:
        description = "A VOD entry on <https://live.48.cn>."


@db.atomic()
def resolve_vods_by_canon_ids(ids):
    vods = []
    for batch in peewee.chunked(ids, 100):
        results = list(PerfVODModel.select().where(PerfVODModel.canon_id << batch))
        if results:
            vmap = {v.canon_id: v for v in results}
        else:
            vmap = {}
        for canon_id in batch:
            vods.append(vmap.get(canon_id))
    return [PerfVOD.from_database_model(v) if v else None for v in vods]


@db.atomic()
def resolve_vods_by_time_range(from_, to_, group=None):
    query = PerfVODModel.select().where(
        (PerfVODModel.start_time >= from_) & (PerfVODModel.start_time < to_)
    )
    if group is not None:
        query = query.where(PerfVODModel.l4c_club_id == group)
    query = query.order_by(
        PerfVODModel.start_time, PerfVODModel.l4c_club_id, PerfVODModel.l4c_id
    )
    return [PerfVOD.from_database_model(v) for v in query]


# It's possible to return a non-200 status code on custom exceptions,
# see my comment at
# https://github.com/graphql-python/flask-graphql/issues/49#issuecomment-487349723.
# Seems to be an overkill at the moment, though.
class InvalidQuery(GraphQLError):
    pass


class Query(graphene.ObjectType):
    revision = graphene.NonNull(
        graphene.String, description="Revision number of the schema."
    )
    perf_vod = graphene.Field(
        PerfVOD,
        id=graphene.String(
            required=True, description='Canonical VOD ID, e.g., `"324479006245982208"`.'
        ),
        description="Look up one VOD by ID.",
    )
    perf_vods = graphene.Field(
        graphene.List(PerfVOD),
        ids=graphene.List(
            graphene.String,
            description='Canonical VOD IDs, e.g., `"324479006245982208"`.',
        ),
        from_=graphene.Int(
            name="from", description="Time range lower bound (inclusive)."
        ),
        to_=graphene.Int(name="to", description="Time range upper bound (exclusive)."),
        group=Group(description="Optionally limit group affiliation."),
        description="""Look up a list of VODs by IDs or time range (optionally filtered by group
        affiliation). Either specify `ids`, or `from` and `to` (`group` is optional), but not
        both.""",
    )

    def resolve_revision(self, info):
        return SCHEMA_REVISION_NUMBER

    def resolve_perf_vod(self, info, id):
        return resolve_vods_by_canon_ids([id])[0]

    def resolve_perf_vods(self, info, **args):
        ids = args.get("ids")
        from_ = args.get("from_")
        to_ = args.get("to_")
        group = args.get("group")
        if ids is not None and (
            from_ is not None or to_ is not None or group is not None
        ):
            raise InvalidQuery(
                "'from', 'to' and 'group' are not allowed when 'ids' is specified."
            )
        if ids is None and (from_ is None or to_ is None):
            raise InvalidQuery("Either 'ids', or 'from' and 'to' must be specified.")
        if ids is not None:
            return resolve_vods_by_canon_ids(ids)
        if from_ is not None and to_ is not None:
            return resolve_vods_by_time_range(from_, to_, group=group)
        # The following code path shouldn't be possible.
        raise NotImplementedError("Cannot resolve VODs with the given args.")


schema = graphene.Schema(query=Query)
