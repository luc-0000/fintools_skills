#!/usr/bin/env python3
"""Discover and query public FinTools website resources via the public discovery endpoint."""

import argparse
import json
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


DEFAULT_DISCOVERY_PATH = "/api/v1/public/info"


def fail(message):
    raise SystemExit(message)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Discover and query public FinTools website resources."
    )
    parser.add_argument("--site-url", required=True, help="Website root URL, for example https://example.trycloudflare.com/")
    parser.add_argument(
        "--subject",
        default="resources",
        choices=[
            "info",
            "resources",
            "agents",
            "agent",
            "skills",
            "skill",
            "stocks",
            "candles",
            "news",
            "user",
            "thoughts",
        ],
    )
    parser.add_argument("--repo-id")
    parser.add_argument("--ticker")
    parser.add_argument("--author")
    parser.add_argument("--page", type=int)
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--keyword")
    return parser.parse_args()


def normalize_site_origin(site_url):
    parsed = urllib_parse.urlparse(str(site_url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        fail("site_url must be an absolute http(s) URL")
    return "{0}://{1}".format(parsed.scheme, parsed.netloc)


def discovery_url(site_url):
    return normalize_site_origin(site_url) + DEFAULT_DISCOVERY_PATH


def build_url(base_url, params=None):
    if not params:
        return base_url
    query = urllib_parse.urlencode({k: v for k, v in params.items() if v is not None})
    if not query:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return "{0}{1}{2}".format(base_url, separator, query)


def fetch_json(url, params=None):
    request = urllib_request.Request(build_url(url, params), method="GET")
    try:
        with urllib_request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail("HTTP {0} while fetching {1}: {2}".format(exc.code, url, body))
    except urllib_error.URLError as exc:
        fail("Failed to fetch {0}: {1}".format(url, exc.reason))


def normalize_service_url(value, site_origin):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if text.startswith("/"):
        return urllib_parse.urljoin(site_origin, text)
    parsed = urllib_parse.urlparse(text)
    if parsed.scheme and parsed.netloc and parsed.path.startswith(("/api/", "/gitea/")):
        return urllib_parse.urlunparse(
            (urllib_parse.urlparse(site_origin).scheme, urllib_parse.urlparse(site_origin).netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
        )
    return value


def rewrite_urls(payload, site_origin):
    if isinstance(payload, dict):
        rewritten = {}
        for key, value in payload.items():
            if key == "path":
                rewritten[key] = value
            else:
                rewritten[key] = rewrite_urls(normalize_service_url(value, site_origin), site_origin)
        return rewritten
    if isinstance(payload, list):
        return [rewrite_urls(item, site_origin) for item in payload]
    return payload


def normalize_endpoints(discovery_doc, site_origin):
    normalized = []
    for endpoint in discovery_doc.get("endpoints", []):
        row = dict(endpoint)
        path = row.get("path")
        if path:
            row["resolved_url"] = urllib_parse.urljoin(site_origin, path)
        elif row.get("url"):
            row["resolved_url"] = normalize_service_url(row["url"], site_origin)
        normalized.append(row)
    return normalized


def fetch_discovery(site_url):
    site_origin = normalize_site_origin(site_url)
    document = rewrite_urls(fetch_json(discovery_url(site_url)), site_origin)
    document["requested_site_url"] = site_origin
    document["discovery_url"] = discovery_url(site_url)
    document["endpoints"] = normalize_endpoints(document, site_origin)
    return document


def endpoint_index(discovery_doc):
    index = {}
    for endpoint in discovery_doc.get("endpoints", []):
        path = endpoint.get("path")
        if path:
            index[path] = endpoint["resolved_url"]
    return index


def require_arg(name, value, subject):
    if value:
        return value
    fail("{0} is required for subject={1}".format(name, subject))


def resources_payload(discovery_doc):
    return {
        "requested_site_url": discovery_doc["requested_site_url"],
        "discovery_url": discovery_doc["discovery_url"],
        "service": discovery_doc.get("service"),
        "purpose": discovery_doc.get("purpose"),
        "capabilities": discovery_doc.get("capabilities", {}),
        "public_data": discovery_doc.get("public_data", []),
        "recommended_flow": discovery_doc.get("recommended_flow", []),
        "endpoints": discovery_doc.get("endpoints", []),
    }


def resolve_subject_url(subject, discovery_doc, args):
    endpoints = endpoint_index(discovery_doc)
    if subject == "agents":
        return endpoints["/api/v1/public/agents"], {"page": args.page, "page_size": args.page_size, "keyword": args.keyword}
    if subject == "agent":
        repo_id = require_arg("repo_id", args.repo_id, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/agents/{0}".format(repo_id)), None
    if subject == "skills":
        return endpoints["/api/v1/public/skills"], {"page": args.page, "page_size": args.page_size, "keyword": args.keyword}
    if subject == "skill":
        repo_id = require_arg("repo_id", args.repo_id, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/skills/{0}".format(repo_id)), None
    if subject == "stocks":
        return endpoints["/api/v1/public/stocks"], {"keyword": args.keyword}
    if subject == "candles":
        ticker = require_arg("ticker", args.ticker, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/stocks/{0}/candles".format(urllib_parse.quote(ticker, safe=""))), None
    if subject == "news":
        ticker = require_arg("ticker", args.ticker, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/stocks/{0}/news".format(urllib_parse.quote(ticker, safe=""))), None
    if subject == "user":
        author = require_arg("author", args.author, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/users/{0}".format(urllib_parse.quote(author, safe=""))), None
    if subject == "thoughts":
        author = require_arg("author", args.author, subject)
        return urllib_parse.urljoin(discovery_doc["requested_site_url"], "/api/v1/public/users/{0}/thoughts".format(urllib_parse.quote(author, safe=""))), None
    fail("Unsupported subject: {0}".format(subject))


def run_query(args):
    discovery_doc = fetch_discovery(args.site_url)
    if args.subject in ("info", "resources"):
        payload = discovery_doc if args.subject == "info" else resources_payload(discovery_doc)
        return {
            "subject": args.subject,
            "site_url": discovery_doc["requested_site_url"],
            "data": payload,
        }

    url, params = resolve_subject_url(args.subject, discovery_doc, args)
    payload = rewrite_urls(fetch_json(url, params), discovery_doc["requested_site_url"])
    return {
        "subject": args.subject,
        "site_url": discovery_doc["requested_site_url"],
        "discovery_url": discovery_doc["discovery_url"],
        "resolved_url": build_url(url, params),
        "data": payload,
    }


def main():
    args = parse_args()
    result = run_query(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
