#!/usr/bin/env python3

import os

import flask
import flask_graphql
import flask_limiter
import flask_limiter.util
from werkzeug.middleware.proxy_fix import ProxyFix

from schema import schema


app = flask.Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
# Example RATELIMIT_STORAGE_URL: redis://localhost:6379/0
RATELIMIT_ON = bool(os.getenv("RATELIMIT_STORAGE_URL"))
if RATELIMIT_ON:
    RATELIMIT = os.getenv("RATELIMIT", default="1/s")
    app.config.update({"RATELIMIT_STORAGE_URL": os.getenv("RATELIMIT_STORAGE_URL")})
    limiter = flask_limiter.Limiter(app, key_func=flask_limiter.util.get_remote_address)

api_view_func = flask_graphql.GraphQLView.as_view(
    "graphql", schema=schema, graphiql=True
)
if RATELIMIT_ON:
    api_view_func = limiter.limit(
        # GraphiQL's HTML UI is exempt.
        RATELIMIT,
        exempt_when=lambda: flask.request.method == "GET",
    )(api_view_func)
app.add_url_rule("/api/graphql", view_func=api_view_func)


@app.route("/")
def index():
    return flask.redirect("https://github.com/SNH48Live/KVM48#readme")


@app.route("/api/")
def api_index():
    return flask.redirect(flask.url_for("graphql"))


def main():
    app.config["ENV"] = "development"
    app.run(debug=True, threaded=True)


if __name__ == "__main__":
    main()
