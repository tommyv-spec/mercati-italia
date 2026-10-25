"""One interruptible request to an existing EES or Cose di Casa resource.

The fixed local worker includes DNS, TLS and body I/O in the caller's wall
clock allowance. It does not retry or follow redirects. The caller validates
each observed redirect and spends another request slot before following it.
"""
from __future__ import annotations

import errno
import ipaddress
import json
import re
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from editorial_calendar_scope import source_identity
from eventiesagre_source_layout import MAX_BYTES

HOSTS = frozenset({"www.eventiesagre.it", "www.cosedicasa.com"})
USER_AGENT = "MercatiItaliaEditorialRefresh/1.0"
ROBOTS_BYTES = 55_000
ERROR_CODES = frozenset({"http_403", "http_404", "http_429", "http_5xx", "http_other",
    "dns_error", "tls_certificate_error", "tls_error", "transport_timeout", "deadline_exceeded",
    "connection_refused", "connection_reset", "network_unreachable", "transport_error",
    "response_validation", "worker_failure", "source_layout_changed", "robots_denied"})


def failure_code(error):
    """Keep a bounded diagnostic category, never arbitrary server/error text."""
    observed = getattr(error, "source_error_code", None)
    if observed in ERROR_CODES:
        return observed
    if isinstance(error, HTTPError):
        return ("http_" + str(error.code) if error.code in {403, 404, 429}
                else "http_5xx" if 500 <= error.code <= 599 else "http_other")
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, socket.gaierror):
        return "dns_error"
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "tls_certificate_error"
    if isinstance(reason, ssl.SSLError):
        return "tls_error"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "transport_timeout"
    if isinstance(reason, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(reason, ConnectionResetError):
        return "connection_reset"
    if getattr(reason, "errno", None) in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
        return "network_unreachable"
    if isinstance(error, (ValueError, TypeError, UnicodeError)):
        return "response_validation"
    return "transport_error"


POLICY_PATH = Path(__file__).resolve().parent / "data/editorial-detail-refresh-policy.json"
INDEX_ACCEPT = {"sitemap_xml": "text/xml", "html_links": "text/html"}


def discovery_index_url(url, *, accept=None, discovery=None):
    """A configured publisher index (sitemap or listing page), never a guess.

    The publisher's own seed URLs, or URLs matching its reviewed follow
    pattern, on the publisher's own host. Read from the policy file so the
    bounded worker process applies the same rule as its caller.
    """
    try:
        if discovery is None:
            discovery = json.loads(POLICY_PATH.read_text("utf-8")).get("discovery") or {}
        value = urlsplit(url)
        if (value.scheme != "https" or value.query or value.fragment or value.username
                or value.password or value.port not in (None, 443)):
            return False
        for policy in discovery.values():
            if (isinstance(policy, dict) and value.netloc == "www." + str(policy.get("publisher"))
                    and (accept is None or INDEX_ACCEPT.get(policy.get("index_format")) == accept)
                    and (url in (policy.get("seed_urls") or [])
                         or re.fullmatch(str(policy.get("follow_pattern")), url))):
                return True
    except (TypeError, ValueError, OSError, re.error):
        pass
    return False


def valid_url(url, *, accept):
    try:
        value = urlsplit(url)
        if (value.scheme != "https" or value.netloc not in HOSTS
                or value.query or value.fragment or value.username or value.password):
            return False
        if accept == "text/plain":
            return value.path == "/robots.txt"
        identity = source_identity(url)
        if accept == "text/html" and identity and "www." + identity[0] in HOSTS:
            return True
        return accept in INDEX_ACCEPT.values() and discovery_index_url(url, accept=accept)
    except (TypeError, ValueError):
        return False


def _validated(spec):
    if not isinstance(spec, dict) or set(spec) != {"url", "timeout", "max_bytes", "accept"}:
        raise ValueError("Invalid editorial transport request")
    maximum = ROBOTS_BYTES if spec["accept"] == "text/plain" else MAX_BYTES
    if (not valid_url(spec["url"], accept=spec["accept"])
            or type(spec["timeout"]) not in (int, float) or not 0 < spec["timeout"] <= 18
            or type(spec["max_bytes"]) is not int or not 1 <= spec["max_bytes"] <= maximum):
        raise ValueError("Unreviewed editorial transport request")
    return spec


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _direct(spec):
    spec = _validated(spec)
    url, maximum, timeout, accept = (spec[k] for k in ("url", "max_bytes", "timeout", "accept"))
    addresses = socket.getaddrinfo(urlsplit(url).hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Editorial publisher DNS is not public")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "identity"})
    with build_opener(_NoRedirect).open(request, timeout=timeout) as response:
        if (response.geturl() != url or response.status != 200
                or accept not in response.headers.get("Content-Type", "").casefold()
                or response.headers.get("Content-Encoding", "identity").casefold() not in {"", "identity"}):
            raise ValueError("Editorial response type or destination changed")
        length = response.headers.get("Content-Length")
        expected = int(length) if length is not None else None
        if expected is not None and not 1 <= expected <= maximum:
            raise ValueError("Editorial response exceeds its byte limit")
        body = response.read(maximum + 1)
        if not body or len(body) > maximum or expected is not None and expected != len(body):
            raise ValueError("Editorial response is incomplete or oversized")
    return body, url


def fetch(url, *, timeout, max_bytes, accept):
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
        error = TimeoutError("Editorial transport exceeded its remaining time allowance")
        error.source_error_code = "deadline_exceeded"
        raise error from None
    except BaseException:
        # Cancellation must not leave an HTTP worker running after its caller.
        # Preserve the original exception so an interrupted request stays
        # inflight rather than becoming a terminal source failure.
        process.kill()
        process.communicate()
        raise
    if process.returncode or len(payload) > max_bytes + 4000:
        raise OSError("Editorial bounded transport worker failed")
    header, separator, body = payload.partition(b"\n")
    if not separator or len(header) > 4000:
        raise OSError("Editorial transport result lost its framing")
    try:
        result = json.loads(header)
    except (ValueError, UnicodeError):
        raise OSError("Editorial transport result is unreadable") from None
    if result == {"ok": True, "final_url": url}:
        if not body or len(body) > max_bytes:
            raise ValueError("Editorial transport returned an invalid body bound")
        return body, url
    if (body or not isinstance(result, dict)
            or set(result) - {"ok", "error_type", "error_code", "http_status", "location"}
            or result.get("ok") is not False or result.get("error_code") not in ERROR_CODES):
        raise OSError("Editorial transport failure is invalid")
    kind, code = result.get("error_type"), result["error_code"]
    if kind == "HTTPError" and type(result.get("http_status")) is int and 100 <= result["http_status"] <= 599:
        location = result.get("location")
        if location is not None and (not isinstance(location, str) or len(location) > 1200
                                     or any(ord(char) < 32 for char in location)):
            raise ValueError("Editorial redirect response is unbounded")
        error = HTTPError(url, result["http_status"], "Editorial source response failed",
                          {"Location": location} if location else {}, None)
    elif kind in {"TimeoutError", "TimeoutExpired"}:
        error = TimeoutError("Editorial source response timed out")
    elif kind in {"ValueError", "TypeError", "UnicodeError"}:
        error = ValueError("Editorial source response failed bounded validation")
    elif kind == "URLError":
        error = URLError("Editorial source transport unavailable")
    else:
        error = OSError("Editorial source transport unavailable")
    error.source_error_code = code
    raise error


def _worker():
    body = b""
    try:
        raw = sys.stdin.buffer.read(5001)
        if len(raw) > 5000:
            raise ValueError("Unbounded editorial transport input")
        body, final = _direct(json.loads(raw))
        result = {"ok": True, "final_url": final}
    except Exception as error:
        result = {"ok": False, "error_type": type(error).__name__, "error_code": failure_code(error)}
        if isinstance(error, HTTPError):
            result["http_status"] = error.code
            location = error.headers.get("Location") if error.headers is not None else None
            if (isinstance(location, str) and len(location) <= 1200
                    and not any(ord(char) < 32 for char in location)):
                result["location"] = location
    sys.stdout.buffer.write(json.dumps(result).encode() + b"\n" + body)


if __name__ == "__main__":
    if sys.argv[1:] != ["--http-worker"]:
        raise SystemExit("Editorial transport is an internal bounded worker")
    _worker()
