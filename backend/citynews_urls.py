"""Reviewed Citynews origins and exact existing event-detail URL identities."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

# Origins inventoried in the source-format audit. A matching URL still needs
# the event layout, exact title, geography and edition proof before any write.
HOSTS = frozenset({
    "arezzonotizie.it", "baritoday.it", "bolognatoday.it", "bresciatoday.it",
    "cagliaritoday.it", "casertanews.it", "cataniatoday.it", "cesenatoday.it",
    "ferraratoday.it", "firenzetoday.it", "forlitoday.it", "frosinonetoday.it",
    "genovatoday.it", "leccotoday.it", "modenatoday.it", "monzatoday.it",
    "novaratoday.it", "padovatoday.it", "palermotoday.it", "parmatoday.it",
    "ravennatoday.it", "riminitoday.it", "romatoday.it", "torinotoday.it",
    "trevisotoday.it", "veneziatoday.it", "vicenzatoday.it", "viterbotoday.it",
})


def source_identity(url):
    if not isinstance(url, str) or not 20 <= len(url) <= 1200:
        return None
    try:
        value = urlsplit(url)
        host = (value.hostname or "").removeprefix("www.")
        if (host not in HOSTS or value.netloc != "www." + host
                or value.scheme != "https" or value.username or value.password
                or value.query or value.fragment or not re.fullmatch(
                    r"/eventi/(?!tipo/|location/)[A-Za-z0-9][A-Za-z0-9_/-]*\.html", value.path)):
            return None
        return host, "citynews-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    except ValueError:
        return None
