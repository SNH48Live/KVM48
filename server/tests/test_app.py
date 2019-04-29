import pytest

import app as kvm48_server


@pytest.fixture
def client(database):
    yield kvm48_server.app.test_client()


def test_parametrized_query(client):
    query = """\
        query perfVods($ids: [String!], $from: Int, $to: Int, $group: Group) {
          perfVods(ids: $ids, from: $from, to: $to, group: $group) {
            id
            startTime
          }
        }"""
    variables = {"ids": None, "from": 1555776000, "to": 1555840800, "group": "SNH48"}
    r = client.post("/api/graphql", json=dict(query=query, variables=variables))
    assert r.status_code == 200
    assert r.json == {
        "data": {
            "perfVods": [
                {"id": "324479006245982208", "startTime": 1555825500},
                {"id": "326091353251188736", "startTime": 1555836300},
            ]
        }
    }
