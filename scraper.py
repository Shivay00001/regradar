"""
RegRadar — Offline Regulatory Scraper
Scrapes official Indian government regulatory sites for latest circulars/notifications.
Works without any API key — just needs internet for fetching pages.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json
import traceback

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 15


def safe_get(url, **kwargs):
    """Safe HTTP GET with error handling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"[SCRAPER] Failed to fetch {url}: {e}")
        return None


def clean_text(text):
    """Clean scraped text."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]


# ─── RBI Scraper ────────────────────────────────────────────────────────────────

def scrape_rbi():
    """Scrape RBI press releases and notifications."""
    results = []

    # RBI Press Releases
    urls = [
        "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
    ]

    for url in urls:
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find tables or links with notifications
        for link in soup.find_all("a", href=True):
            title = clean_text(link.get_text())
            if len(title) < 15 or len(title) > 300:
                continue

            href = link.get("href", "")
            if not href or href == "#":
                continue

            if not href.startswith("http"):
                href = f"https://www.rbi.org.in{href}" if href.startswith("/") else f"https://www.rbi.org.in/Scripts/{href}"

            # Look for date near the link
            parent = link.find_parent("tr") or link.find_parent("div")
            date_text = ""
            if parent:
                text = parent.get_text()
                date_match = re.search(r'(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', text)
                if date_match:
                    date_text = date_match.group(1)

            # Filter for regulatory keywords
            keywords = ['circular', 'notification', 'direction', 'guideline', 'regulation',
                       'amendment', 'policy', 'norms', 'compliance', 'kyc', 'aml', 'nbfc',
                       'bank', 'lending', 'credit', 'deposit', 'payment', 'reserve']
            title_lower = title.lower()
            if any(k in title_lower for k in keywords) or "rbi" in url.lower():
                results.append({
                    "source": "RBI",
                    "title": title,
                    "date": date_text or datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "raw_text": title,
                })

            if len(results) >= 8:
                break

    return results[:6]


# ─── SEBI Scraper ───────────────────────────────────────────────────────────────

def scrape_sebi():
    """Scrape SEBI circulars and orders."""
    results = []

    urls = [
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=2&smid=0",
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=1&smid=0",
    ]

    for url in urls:
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # SEBI lists items in table rows or divs
        for item in soup.find_all(["tr", "div", "li"]):
            links = item.find_all("a", href=True)
            for link in links:
                title = clean_text(link.get_text())
                if len(title) < 15 or len(title) > 300:
                    continue

                href = link.get("href", "")
                if not href.startswith("http"):
                    href = f"https://www.sebi.gov.in{href}"

                # Date extraction
                text = item.get_text()
                date_match = re.search(r'(\w+ \d{1,2},?\s*\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', text)
                date_text = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

                keywords = ['circular', 'order', 'notification', 'regulation', 'amendment',
                           'guideline', 'listing', 'disclosure', 'mutual fund', 'broker',
                           'demat', 'trading', 'investor', 'compliance']
                if any(k in title.lower() for k in keywords) or len(results) < 3:
                    results.append({
                        "source": "SEBI",
                        "title": title,
                        "date": date_text,
                        "url": href,
                        "raw_text": title,
                    })

            if len(results) >= 6:
                break

    return results[:6]


# ─── MCA Scraper ────────────────────────────────────────────────────────────────

def scrape_mca():
    """Scrape MCA (Ministry of Corporate Affairs) notifications."""
    results = []

    resp = safe_get("https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks/acts.html")
    if not resp:
        resp = safe_get("https://www.mca.gov.in/MinistryV2/homepage.html")

    if resp:
        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=True):
            title = clean_text(link.get_text())
            if len(title) < 10 or len(title) > 300:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://www.mca.gov.in{href}"

            keywords = ['notification', 'circular', 'companies act', 'amendment', 'rule',
                       'order', 'gazette', 'compliance', 'director', 'auditor', 'csr']
            if any(k in title.lower() for k in keywords):
                results.append({
                    "source": "MCA",
                    "title": title,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "raw_text": title,
                })

            if len(results) >= 6:
                break

    return results[:6]


# ─── GST Scraper ────────────────────────────────────────────────────────────────

def scrape_gst():
    """Scrape CBIC/GST circulars and notifications."""
    results = []

    urls = [
        "https://taxinformation.cbic.gov.in/content-page/explore-notification",
        "https://www.cbic.gov.in/entities/cbec_entity_whats_new",
    ]

    for url in urls:
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=True):
            title = clean_text(link.get_text())
            if len(title) < 10 or len(title) > 300:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                base = url.rsplit("/", 1)[0]
                href = f"{base}/{href}"

            keywords = ['gst', 'circular', 'notification', 'cgst', 'sgst', 'igst',
                       'tax', 'rate', 'exemption', 'amendment', 'return', 'invoice',
                       'input tax', 'e-way', 'refund']
            if any(k in title.lower() for k in keywords):
                results.append({
                    "source": "GST",
                    "title": title,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "raw_text": title,
                })

            if len(results) >= 6:
                break

    return results[:6]


# ─── Labour Scraper ─────────────────────────────────────────────────────────────

def scrape_labour():
    """Scrape Labour Ministry notifications."""
    results = []

    urls = [
        "https://labour.gov.in/whatsnew",
        "https://labour.gov.in/latest-notifications",
    ]

    for url in urls:
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=True):
            title = clean_text(link.get_text())
            if len(title) < 10 or len(title) > 300:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://labour.gov.in{href}"

            keywords = ['notification', 'amendment', 'code', 'wage', 'labour',
                       'safety', 'social security', 'industrial', 'employment',
                       'pf', 'esi', 'gratuity', 'bonus', 'minimum wage']
            if any(k in title.lower() for k in keywords):
                results.append({
                    "source": "LABOUR",
                    "title": title,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "raw_text": title,
                })

            if len(results) >= 6:
                break

    return results[:6]


# ─── Main Scraper Function ──────────────────────────────────────────────────────

SCRAPERS = {
    "RBI": scrape_rbi,
    "SEBI": scrape_sebi,
    "MCA": scrape_mca,
    "GST": scrape_gst,
    "LABOUR": scrape_labour,
}


def scrape_source(source="All"):
    """
    Scrape regulatory updates from specified source(s).
    Returns list of raw scraped items for AI to process.
    """
    print(f"[SCRAPER] Starting scrape for: {source}")
    all_results = []

    if source == "All":
        for name, scraper_fn in SCRAPERS.items():
            try:
                items = scraper_fn()
                all_results.extend(items)
                print(f"[SCRAPER] {name}: found {len(items)} items")
            except Exception as e:
                print(f"[SCRAPER] {name} error: {e}")
                traceback.print_exc()
    else:
        scraper_fn = SCRAPERS.get(source)
        if scraper_fn:
            try:
                items = scraper_fn()
                all_results.extend(items)
                print(f"[SCRAPER] {source}: found {len(items)} items")
            except Exception as e:
                print(f"[SCRAPER] {source} error: {e}")
                traceback.print_exc()

    print(f"[SCRAPER] Total scraped: {len(all_results)} items")
    return all_results


def scrape_url_content(url):
    """Scrape full text content from a specific URL for deep analysis."""
    resp = safe_get(url)
    if not resp:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove scripts and styles
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Clean up
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    return text[:3000]  # Limit to 3000 chars for AI context


if __name__ == "__main__":
    # Test run
    import warnings
    warnings.filterwarnings("ignore")

    print("Testing RegRadar Scraper...\n")
    results = scrape_source("All")
    for r in results[:10]:
        print(f"[{r['source']}] {r['title'][:80]}")
        print(f"  URL: {r['url'][:80]}")
        print()
    print(f"\nTotal: {len(results)} items scraped")
