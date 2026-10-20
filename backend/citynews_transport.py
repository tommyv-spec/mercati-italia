"""One bounded public HTTP attempt, interruptible across DNS/TLS/body reads.

The fixed local worker is killed and reaped when its caller's remaining time
expires. This adds no retries, redirect following, service or dependency.
"""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from citynews_urls import HOSTS, source_identity

USER_AGENT = "MercatiItaliaEditorialRefresh/1.0"
MAX_BYTES = 2_500_000
ROBOTS_BYTES = 55_000


def valid_url(url, kind):
    if kind == "detail":
        return source_identity(url) is not None
    try:
        value = urlsplit(url)
        return bool(kind == "robots" and value.scheme == "https" and value.netloc in {"www." + h for h in HOSTS}
                    and value.path == "/robots.txt" and not value.query and not value.fragment)
    except (TypeError, ValueError):
        return False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validated(spec):
    if not isinstance(spec, dict) or set(spec) != {"url", "timeout", "max_bytes", "accept"}:
        raise ValueError("Invalid Citynews transport request")
    kind = {"text/plain": "robots", "text/html": "detail"}.get(spec["accept"])
    maximum = ROBOTS_BYTES if kind == "robots" else MAX_BYTES
    if (kind is None or not valid_url(spec["url"], kind)
            or type(spec["timeout"]) not in (int, float) or not 0 < spec["timeout"] <= 60
            or type(spec["max_bytes"]) is not int or not 1 <= spec["max_bytes"] <= maximum):
        raise ValueError("Unreviewed Citynews transport request")
    return spec


def _direct(spec):
    spec = _validated(spec)
    url, maximum, timeout, accept = (spec[k] for k in ("url", "max_bytes", "timeout", "accept"))
    host = urlsplit(url).hostname
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(v[4][0]).is_global for v in addresses):
        raise ValueError("Citynews publisher DNS is not public")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "identity"})
    with build_opener(_NoRedirect).open(request, timeout=timeout) as response:
        if (response.status != 200 or response.geturl() != url
                or accept not in response.headers.get("Content-Type", "").casefold()
                or response.headers.get("Content-Encoding", "identity").casefold() not in {"", "identity"}):
            raise ValueError("Citynews response type or exact URL changed")
        size = response.headers.get("Content-Length")
        size = int(size) if size is not None else None
        if size is not None and not 1 <= size <= maximum:
            raise ValueError("Citynews response exceeds its byte limit")
        body = response.read(maximum + 1)
        if not body or len(body) > maximum or size is not None and size != len(body):
            raise ValueError("Citynews response is incomplete or oversized")
    return body, url


def fetch(url, *, timeout, max_bytes, accept):
    """Make exactly one attempt; timeout covers process startup and all I/O."""
    spec = _validated({"url": url, "timeout": timeout, "max_bytes": max_bytes, "accept": accept})
    started = time.monotonic()
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--http-worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=False)
    try:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        payload, _ = process.communicate(json.dumps(spec).encode(), timeout=remaining)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise TimeoutError("Citynews transport exceeded its remaining time allowance") from None
    if process.returncode or len(payload) > max_bytes + 4000:
        raise OSError("Citynews bounded transport worker failed")
    header, separator, body = payload.partition(b"\n")
    if not separator or len(header) > 4000:
        raise OSError("Citynews transport result lost its framing")
    try:
        result = json.loads(header)
    except (ValueError, UnicodeError):
        raise OSError("Citynews transport result is unreadable") from None
    if result == {"ok": True, "final_url": url}:
        if not body or len(body) > max_bytes:
            raise ValueError("Citynews transport returned an invalid body bound")
        return body, url
    if body or not isinstance(result, dict) or set(result) - {"ok", "error_type", "http_status"} or result.get("ok") is not False:
        raise OSError("Citynews transport failure is invalid")
    error = result.get("error_type")
    if error == "HTTPError" and type(result.get("http_status")) is int and 100 <= result["http_status"] <= 599:
        raise HTTPError(url, result["http_status"], "Citynews source response failed", {}, None)
    if error in {"TimeoutError", "TimeoutExpired"}:
        raise TimeoutError("Citynews source response timed out")
    if error == "ValueError":
        raise ValueError("Citynews source response failed bounded validation")
    if error == "URLError":
        raise URLError("Citynews source transport unavailable")
    raise OSError("Citynews source transport unavailable")


def _worker():
    body = b""
    try:
        raw = sys.stdin.buffer.read(5001)
        if len(raw) > 5000:
            raise ValueError("Unbounded Citynews transport input")
        body, final = _direct(json.loads(raw))
        result = {"ok": True, "final_url": final}
    except Exception as error:
        result = {"ok": False, "error_type": type(error).__name__}
        if isinstance(error, HTTPError): result["http_status"] = error.code
    sys.stdout.buffer.write(json.dumps(result).encode() + b"\n" + body)


if __name__ == "__main__":
    if sys.argv[1:] != ["--http-worker"]:
        raise SystemExit("Citynews transport is an internal bounded worker")
    _worker()
