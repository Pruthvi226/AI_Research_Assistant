"""Bounded public metadata retrieval. Upstream URLs are never supplied by clients."""
import html
import json
import re
import time
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def clean(value):
    return html.unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).strip()


def normalize(work):
    parts = (work.get("published") or work.get("issued") or {}).get("date-parts", [[]])
    doi = work.get("DOI", "")
    return {
        "id": doi,
        "title": clean((work.get("title") or ["Untitled"])[0]),
        "authors": [clean(" ".join(filter(None, [a.get("given"), a.get("family")]))) or a.get("name", "") for a in work.get("author", [])],
        "year": parts[0][0] if parts and parts[0] else None,
        "abstract": clean(work.get("abstract"))[:14000],
        "url": f"https://doi.org/{doi}",
        "source": "Crossref publisher metadata",
    }


def _request(url):
    for attempt in range(2):
        try:
            req = Request(url, headers={"User-Agent": "Scientia-Research/2.0", "Accept": "application/json"})
            with urlopen(req, timeout=12) as response:
                return json.loads(response.read(3_000_000))
        except HTTPError as exc:
            if exc.code in {429, 503} and attempt == 0:
                time.sleep(1)
                continue
            raise RuntimeError("The publication index is unavailable. Please retry later.") from None
        except (URLError, TimeoutError, ValueError):
            raise RuntimeError("Could not retrieve publication metadata. Please retry later.") from None


@lru_cache(maxsize=128)
def search_papers(query, time_bucket=None):
    # time_bucket is passed by callers to expire the bounded cache every 10 minutes.
    data = _request("https://api.crossref.org/works?" + urlencode({"query.bibliographic": query[:300], "rows": 6}))
    return [normalize(work) for work in data.get("message", {}).get("items", [])]


@lru_cache(maxsize=128)
def paper_by_doi(doi, time_bucket=None):
    if not isinstance(doi, str) or not re.fullmatch(r"10\.\d{4,9}/\S{1,200}", doi):
        raise ValueError("Each paper must have a valid DOI.")
    return normalize(_request("https://api.crossref.org/works/" + quote(doi, safe=""))["message"])
