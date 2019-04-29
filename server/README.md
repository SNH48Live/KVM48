# Server component of KVM48

![Powered by Flask](https://img.shields.io/badge/powered%20by-Flask-blue.svg?logo=flask&maxAge=86400)

Starting from KVM48 v1.4, due to significant limitations introduced in Koudai48 API v6, a third-party (or first-party from KVM48's POV) server-assisted mode is introduced to restore and even improve the performance and quality of KVM48's crawler.

The server component consists of a crawler and a simple Flask app serving a GraphQL API. The API can be accessed at <https://kvm48.momo0v0.club/api/graphql>. You can use GraphiQL's builtin documentaion explorer to access API docs.

---

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Crawler](#crawler)
- [API server](#api-server)
- [Infrequently asked questions](#infrequently-asked-questions)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Crawler

When crawling for the first time, run

```console
$ ./crawler.py --full --legacy
```

A SQLite database should be automatically created and populated at `data/data.db`.

```console
$ ./crawler.py
```

should be sufficient for subsequent crawls.

I run the crawler in a cron job every 5 minutes. While the crawler itself lacks direct error notifications, I use <https://healthchecks.io/> with Pushover integration to notify myself in case the crawler fails.

## API server

Entry point to the API server is `app.py`. The WSGI object is `app.app`, and `./app.py` launches a development server. The following environment variables are supported:

- `RATELIMIT_STORAGE_URL`: If set, rate limit the API endpoint. Example: `redis://localhost:6379/15`. See [Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/#configuration) documentation for details.
- `RATELIMIT`: If rate limiting is enabled (through `RATELIMIT_STORAGE_URL`), the limit can be customized via this variable. The default is `1/second`. Again, see [Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/#ratelimit-string) documentation for details.

## Infrequently asked questions

- *Q: Why don't you serve the API on kvm48.snh48live.org?*

  A: For crawler performance and reliability, I need to host the database on a Chinese server. I use Alibaba Cloud for my Chinese VPS needs. And somehow some way, they decided to drop (?) all connections to `*.snh48live.org:443`. Initially I thought something was wrong with my nginx configs, but all evidence points to something sinister happening at Alibaba Cloud's boundary:

  - All external requests to `*.snh48live.org:443` (from multiple nodes around the world) fail with `SSL_ERROR_SYSCALL`; in nginx debug logs we always see

    ```
    SSL_do_handshake: -1
    SSL_get_error: 5
    peer closed connection in SSL handshake (104: Connection reset by peer) while SSL handshaking
    ```

  - Internal requests work just fine.

  - Other domains with similar vhost configs and listening on the exact same host and port work just fine, and have been working for years.

  - Serving the same config on a different port work just fine (e.g., `*.snh48live.org:8443`).

  - Serving the same config on a different domain work just fine (as evidenced by `kvm48.momo0v0.club`).

  - The certs for all my domains are LE certs, and I manually inspected the `snh48live.org, *.snh48live.org` cert at question with `openssl` and even force-renewed once.

  - I've been writing nginx vhost config (with SSL) for years and this is the first time I encountered the mysterious problem.

  In short, it appears only `*.snh48live.org:443` is blocked by Alibaba Cloud and I have zero idea why. If someone has relevant information, please let me know.
