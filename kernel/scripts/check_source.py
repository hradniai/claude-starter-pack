#!/usr/bin/env python3
"""Deterministic source reachability check for research agents.

A research agent's URL is a claim until something that is not a model has looked at the page.
This script is that something: it fetches the raw HTML, follows redirects, records where it
landed, looks for the quoted excerpt, and classifies what came back. It never judges meaning;
that stays with the model, and only for a source this script reports as read.

Why a script and not WebFetch: a paywall, a login wall and a soft 404 all answer HTTP 200 with
their own page, so a model reading that page tends to call the claim "unsupported" when nobody
ever saw the source. A fixed rule set is cheaper than a model call per link and gives the same
answer every time.

What counts as read text: the text of the page, rebuilt the way a reader sees it (an inline tag
such as <b> does not split a word), with HTML comments, <script>, <style>, <template>, <noscript>
and <head> removed, and every element the markup itself hides: the hidden attribute (except
hidden="until-found", which find-in-page reveals), aria-hidden="true", and an inline style that
sets display:none or visibility:hidden. Raw or hidden markup never counts, so a quote in a comment
or a hidden div is not evidence that the page was read. This is HTML text extraction, not a
browser: hiding done by a stylesheet class or by script is not seen, so that text still counts.

Verdicts
  REACHED                the page was read and the quoted excerpt is on it word for word, or no quote
                         was given and the page has readable main text
  REACHED_QUOTE_FUZZY    the page was read; the excerpt is not on it word for word, but a passage
                         matches it closely (FUZZY_THRESHOLD below): reformatted or lightly
                         paraphrased. Never reported as an exact match.
  REACHED_QUOTE_MISSING  the whole page was read and the excerpt is not in its readable text
  REACHED_UNCHECKED      the address answered with content this script cannot read inside (a PDF, an
                         image, any other non-text type): reached, but neither the content nor the
                         excerpt was checked, so it is not a read source
  TRUNCATED              only part of the page was read (size cap, time cap or capped decompression)
                         and the excerpt is not in that part, so its absence proves nothing
  PAYWALLED              isAccessibleForFree false in JSON-LD or microdata, a paywall redirect, or
                         page text that says the article is for subscribers only
  LOGIN_WALL             HTTP 401, a redirect to a login path, or a login form dominating the page
  CONSENT_WALL           a redirect to a cookie-consent host or path, or a short page that is only a
                         consent dialog
  SOFT_404               a deep URL redirected to the site root or a parent section, or a 200 page
                         that says "not found"
  BLOCKED                HTTP 403 / 429 / 451, or a bot-challenge page
  NO_CONTENT             too little readable main text once navigation, header, footer, scripts and
                         comments are removed (usually a page rendered by JavaScript), or a body in
                         an encoding this script cannot decode
  UNREACHABLE            network error, timeout, 404, 410, 5xx, a redirect loop, a non-http URL,
                         or an address this script refuses to fetch (see Address policy)

Only REACHED, REACHED_QUOTE_FUZZY and REACHED_QUOTE_MISSING mean the page was read. Every other
verdict means "not verified (reason)" and must never be reported as unsupported or false.

Usage
  check_source.py --batch FILE [--compact]
      FILE holds a JSON array of {"id": ..., "url": ..., "quote": ...}. An agent writes that file
      with its Write tool and passes only the path: never put a URL or page text on a command
      line, where the shell runs $(...) and backticks even inside double quotes. "-" reads the
      array from stdin, for a program that pipes it in (a test, a script); an agent does not use
      it, because a heredoc puts the page text back on the command line.
Options
  --compact    print only what the checker itself decides (id, url, final_url, verdict, reason,
               http_status, quote_found, quote_match, quote_similarity, truncated, signals,
               quote_digest): no page title, no redirect list, nothing else a page controls. One
               JSON object per line, in input order, so a relay that garbles one line loses one
               verdict, not the batch
  --timeout SECONDS (default 15)   --max-bytes N (default 2000000)   --workers N (default 8)
  --allow-private  fetch non-public addresses (the fixture tests on 127.0.0.1 need it)

Address policy: every address that is not publicly routable is refused (loopback, private,
link-local, CGNAT 100.64.0.0/10 where the Tailscale tailnet lives, multicast, reserved, and IPv6
forms that embed one of those), and so is every *.ts.net name. The check runs inside the
connection itself: the socket connects to exactly the address that was validated, on every
redirect hop, while the Host header and the TLS certificate check keep the hostname, so a DNS
answer that changes between two lookups (rebinding) cannot reach an internal service. Proxy
settings from the environment are ignored for the same reason.

Output is JSON on stdout: an array in input order, or JSON Lines with --compact. Exit 0 whenever the check ran, whatever the
verdicts; exit 2 on bad usage or unreadable input. Stdlib only, so it runs on any Python 3.9 or
newer. The pack starts it through the launcher, which finds that Python where `python3` is missing
(normal on Windows):
  sh ~/.claude/scripts/python-launcher.sh plain check_source.py --batch FILE --compact
"""

import argparse
import html
import http.client
import http.cookiejar
import ipaddress
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from heapq import nlargest
from html.parser import HTMLParser

VERDICTS = (
    'REACHED', 'REACHED_QUOTE_FUZZY', 'REACHED_QUOTE_MISSING', 'REACHED_UNCHECKED', 'TRUNCATED', 'PAYWALLED',
    'LOGIN_WALL', 'CONSENT_WALL', 'SOFT_404', 'BLOCKED', 'NO_CONTENT', 'UNREACHABLE',
)
READ_VERDICTS = ('REACHED', 'REACHED_QUOTE_FUZZY', 'REACHED_QUOTE_MISSING')

DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_WORKERS = 8
MAX_REDIRECTS = 10
MAX_META_REFRESH = 2
# Plain text below this many characters counts as empty.
MIN_CONTENT_CHARS = 50
# An HTML page whose main text (navigation, header, footer and asides removed) is shorter than
# this was not read: a JavaScript shell typically serves a menu, a footer and an empty root div.
MIN_MAIN_CHARS = 200
# A login form on a page shorter than this dominates it; on a longer page it is a header widget.
LOGIN_PAGE_MAX_CHARS = 1500
# A consent dialog only counts as the whole page when the main text is this short.
CONSENT_PAGE_MAX_CHARS = 1500
# A "not found" title only counts when the page is this short, or the h1 says the same.
NOT_FOUND_PAGE_MAX_CHARS = 3000
# Fuzzy quote tier. Each fragment of the excerpt is aligned in word order against the best window
# of the page, and scored 2 * matched_words / (quote_words + aligned_page_words). 0.85 lets one
# changed word in seven through (0.857) and stops two in ten (0.80): tolerant of a reformatted or
# lightly paraphrased copy, strict enough that a different sentence on the same topic fails.
# Fragments shorter than FUZZY_MIN_WORDS words only count when every word is there in order.
FUZZY_THRESHOLD = 0.85
FUZZY_MIN_WORDS = 6
FUZZY_CANDIDATES = 10

USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/126.0 Safari/537.36')
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en;q=0.9,*;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
}

TEXT_TYPES = ('text/', 'application/json', 'application/xml', 'application/xhtml+xml',
              'application/rss+xml', 'application/atom+xml', 'application/ld+json')

LOGIN_SEGMENTS = {
    'login', 'log-in', 'logon', 'signin', 'sign-in', 'sign_in', 'signon', 'sso', 'auth',
    'authenticate', 'authorize', 'oauth', 'oauth2', 'authwall', 'wp-login.php', 'uas',
}
LOGIN_HOST_LABELS = {'login', 'signin', 'auth', 'sso', 'accounts', 'idp'}
PAYWALL_SEGMENTS = {'subscribe', 'subscription', 'subscriptions', 'paywall', 'premium'}
CONSENT_HOST_LABELS = {'consent', 'cmp', 'guce', 'myprivacy'}
CONSENT_SEGMENTS = {'consent', 'cookie-consent', 'cookies-consent', 'privacy-consent', 'gdpr-consent',
                    'collectconsent', 'cookiewall', 'cookie-wall', 'nastaveni-souhlasu', 'souhlas'}
NOT_FOUND_SEGMENTS = {'404', '404.html', '404.php', 'not-found', 'notfound', 'page-not-found',
                      'pagenotfound', 'error-404'}
ROOT_LIKE_SEGMENTS = {'index.html', 'index.htm', 'index.php', 'home', 'default.aspx'}
# A trailing segment that names the same page in another form: /x/index.html is /x/, /x/amp is /x.
SAME_PAGE_TAILS = {'index.html', 'index.htm', 'index.php', 'default.aspx', 'amp'}
# A language root such as /en/ or /cs-cz/ is a site root too. A closed list, because a bare
# two-letter pattern would also swallow real sections such as /ai/ or /go/.
LANGUAGES = {'en', 'cs', 'sk', 'de', 'fr', 'es', 'it', 'pl', 'pt', 'nl', 'ru', 'uk', 'ja', 'zh',
             'ko', 'sv', 'da', 'fi', 'nb', 'hu', 'ro', 'tr', 'el', 'he', 'ar', 'bg', 'hr', 'sl'}
LOCALE_SEGMENT = re.compile(r'^(' + '|'.join(sorted(LANGUAGES)) + r')([-_][a-z]{2})?$')

# A title segment that IS a login prompt ("Sign in - Portal", "Log in or sign up"), matched on
# folded text (no case, no diacritics). A title that merely mentions signing in ("Sign in with
# passkeys: a guide") is an article about it and does not count.
LOGIN_TITLE_SEGMENT = re.compile(
    r'^(please )?(log ?in|sign ?in|signin|login|log on|anmelden|connexion|iniciar sesion|'
    r'prihlaseni|prihlasit se|prihlaste se)( (or|and|to|with your) .{0,40})?$')
TITLE_SEPARATORS = re.compile(r'\s[-|:\u00b7\u2013]\s|\s?[|\u00b7]\s?')
NOT_FOUND_TEXT = re.compile(
    r'(^\s*(error\s*)?404\b|\bpage not found\b|^\s*not found\b|\bnot found\s*$|'
    r'\b(page|article|post|file)\b[^.]{0,40}\b(does not|doesn\'t|could not|couldn\'t|cannot|can\'t) '
    r'(exist|be found)|nenalezen|stránka neexistuje|nicht gefunden|introuvable|no encontrada|'
    r'non trovata|nie znaleziono)', re.I)
CHALLENGE_TITLE = re.compile(
    r'(just a moment|attention required|access denied|security check|checking your browser|'
    r'ddos-guard|robot check|are you a robot|verifying you are human|human verification|'
    r'pardon our interruption|request blocked|you have been blocked|bot verification|captcha|'
    r'access to this page has been denied|^\s*403 forbidden)', re.I)
CHALLENGE_MARKERS = ('cf_chl_opt', 'cf-browser-verification', '_incapsula_resource', 'px-captcha',
                     'ddos-guard', 'captcha-delivery.com')
ACCESS_FALSE = re.compile(r'"isAccessibleForFree"\s*:\s*"?(false|no)"?', re.I)

# Paywall messages, matched on folded page text (no case, no diacritics). Each is the wording of
# a wall, not of a promotion, because a hit turns "quote missing" into "not verified".
PAYWALL_TEXT = re.compile('|'.join([
    r'\bsubscribe (now )?to (continue|keep) reading\b',
    r'\bsubscribe to (read|unlock|access) (the |this )?(full |whole |rest of the )?(article|story|post)\b',
    r'\b(this|the) (article|story|content|post) is (only )?(available )?(for|to) (paying |paid )?'
    r'(subscribers|members)\b',
    r'\bto (continue|keep) reading,? (please )?(subscribe|become a (paid )?(subscriber|member))\b',
    r"\byou('ve| have) (reached|used) (your|all your|the) (free article|article|monthly) limit",
    r"\byou('ve| have) (reached|used) (your|all your) free articles\b",
    r'\b(create|register for) a free account to (continue|keep) reading\b',
    r'\bthe rest of (this|the) (article|story) is (available|reserved) (only )?(for|to) (subscribers|members)\b',
    r'\bunlock (this|the full) (article|story)\b',
    r'\b(clanek|obsah|text|cely clanek) je (dostupny|urcen|k dispozici) (pouze|jen|vyhradne) (pro|predplatitelum)\b',
    r'\b(pouze|jen|vyhradne) pro predplatitele\b',
    r'\bcely (clanek|text) (si )?(prectete|ctete|je dostupny)\b.{0,40}\bpredplat',
    r'\b(zbytek|zbyvajici cast|pokracovani) (clanku|textu)\b.{0,40}\b(predplat|premium)',
    r'\bpro (dalsi |pokracovani ve )?cteni (se )?(prihlaste|si kupte|si predplat|kupte si)',
    r'\bodemknete si (cely )?(clanek|text)\b',
]))
# Consent-dialog wording, matched on folded text of a short page. Two distinct hits are needed,
# because a single cookie line also sits on ordinary pages.
CONSENT_TEXT = [re.compile(p) for p in (
    r'\b(accept|reject|allow|refuse|decline) all( cookies)?\b',
    r'\bmanage (cookie |privacy |your )?(preferences|settings|options|choices)\b',
    r'\bwe (and our (\d+ )?(partners|vendors) )?(use|store|process) cookies\b',
    r'\bbefore you continue\b',
    r'\byour privacy choices\b',
    r'\bpart of the \w+ family of brands\b',
    r'\b(prijmout|odmitnout|povolit) vse\b',
    r'\bnastaveni (souhlasu|cookies|soukromi)\b',
    r'\bsouhlas(im| s (pouzitim|vyuzitim|zpracovanim))\b',
    r'\b(pouzivame|vyuzivame|potrebujeme) (soubory |vas souhlas s vyuzitim )?cookies\b',
    r'\bnez budete pokracovat\b',
)]

SKIP_TEXT_TAGS = {'script', 'style', 'noscript', 'template', 'svg', 'head', 'iframe', 'object'}
# An inline style that hides the element, matched with all whitespace removed and in lower case,
# so "Display : None !important" counts; only whole declarations match, never a longer property name.
HIDING_STYLE = re.compile(r'(^|;)(display:none|visibility:hidden)(!important)?(;|$)')
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param',
             'source', 'track', 'wbr'}
# Tags that do not break a word: "<b>A</b>I" reads "AI". Every other tag starts a new word.
INLINE_TAGS = {'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'code', 'data', 'del', 'dfn', 'em', 'font',
               'i', 'img', 'ins', 'kbd', 'label', 'mark', 'q', 'rp', 'rt', 'ruby', 's', 'samp',
               'small', 'span', 'strike', 'strong', 'sub', 'sup', 'time', 'tt', 'u', 'var', 'wbr'}
# Page furniture, left out of the main-text measure (never out of the quote haystack).
BOILERPLATE_TAGS = {'nav', 'header', 'footer', 'aside'}
BOILERPLATE_ROLES = {'navigation', 'banner', 'contentinfo', 'complementary', 'search'}
BOILERPLATE_NAMES = {'nav', 'navbar', 'navigation', 'menu', 'header', 'site-header', 'footer',
                     'site-footer', 'masthead', 'sidebar', 'breadcrumb', 'breadcrumbs',
                     'cookie-banner', 'cookie-consent'}

# Written as escapes, so the file itself carries no literal em dash.
DASHES = dict.fromkeys(map(ord, '\u2010\u2011\u2012\u2013\u2014\u2015\u2212'), '-')
QUOTES = {ord('‘'): "'", ord('’'): "'", ord('‚'): "'", ord('‛'): "'",
          ord('“'): '"', ord('”'): '"', ord('„'): '"', ord('‟'): '"',
          ord('«'): '"', ord('»'): '"', ord('‹'): "'", ord('›'): "'"}
# Soft hyphen, zero-width space, non-joiner, joiner, word joiner, byte-order mark.
INVISIBLE = dict.fromkeys(map(ord, '\u00ad\u200b\u200c\u200d\u2060\ufeff'), None)
# Markdown a fetch tool adds when it turns a page into text: emphasis marks, code ticks, links.
MARKDOWN_MARKS = dict.fromkeys(map(ord, '*`_'), None)
MARKDOWN_LINK = re.compile(r'!?\[([^\]]*)\]\([^)\s]*\)')
MARKDOWN_BLOCK = re.compile(r'^\s*(#{1,6}|>|[-+*]|\d+[.)])\s+')
WORD = re.compile(r'\w+')

NAT64 = ipaddress.ip_network('64:ff9b::/96')


class RefusedAddress(Exception):
    """The URL names or resolves to an address the checker will not fetch."""


class PageParser(HTMLParser):
    """Collects the handful of things the classifier needs, and nothing else."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.h1 = []
        self.text = []
        self.main = []
        self.ld_json = []
        self.meta = []
        self.canonical = ''
        self.refresh = ''
        self.password_inputs = 0
        self._stack = []  # (tag, skips text, is page furniture)
        self._skip = 0
        self._boiler = 0
        self._in_title = False
        self._in_h1 = False
        self._in_ld = False
        self._buffer = []

    def _break(self):
        if not self._skip:
            self.text.append(' ')
            self.main.append(' ')

    def _is_boilerplate(self, tag, a):
        if tag in ('header', 'footer'):
            # An <article> or <main> keeps its own header and footer: the title and byline live there.
            return not any(t in ('article', 'main') for t, _s, _b in self._stack)
        if tag in BOILERPLATE_TAGS or a.get('role', '').lower() in BOILERPLATE_ROLES:
            return True
        names = set(a.get('class', '').lower().split()) | {a.get('id', '').lower()}
        return bool(names & BOILERPLATE_NAMES)

    @staticmethod
    def _is_hidden(a):
        """The markup itself hides this element from a reader."""
        if 'hidden' in a and a['hidden'].strip().lower() != 'until-found':
            return True
        if a.get('aria-hidden', '').strip().lower() == 'true':
            return True
        return bool(HIDING_STYLE.search(''.join(a.get('style', '').lower().split())))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'meta':
            self.meta.append(a)
            if a.get('http-equiv', '').lower() == 'refresh':
                self.refresh = a.get('content', '')
        elif tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonical = a.get('href', '')
        elif tag == 'input' and a.get('type', '').lower() == 'password':
            self.password_inputs += 1
        if tag not in INLINE_TAGS:
            self._break()
        if tag in VOID_TAGS:
            return
        skip = tag in SKIP_TEXT_TAGS or self._is_hidden(a)
        boiler = self._is_boilerplate(tag, a)
        self._stack.append((tag, skip, boiler))
        self._skip += skip
        self._boiler += boiler
        if tag == 'title' and not self.title:
            self._in_title = True
            self._buffer = []
        elif tag == 'h1':
            self._in_h1 = True
            self._buffer = []
        elif tag == 'script' and 'ld+json' in a.get('type', '').lower():
            self._in_ld = True
            self._buffer = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title' and self._in_title:
            self.title = ' '.join(''.join(self._buffer).split())
            self._in_title = False
        elif tag == 'h1' and self._in_h1:
            self.h1.append(' '.join(''.join(self._buffer).split()))
            self._in_h1 = False
        elif tag == 'script' and self._in_ld:
            self.ld_json.append(''.join(self._buffer))
            self._in_ld = False
        if any(t == tag for t, _s, _b in self._stack):
            while self._stack:
                popped, skip, boiler = self._stack.pop()
                self._skip -= skip
                self._boiler -= boiler
                if popped == tag:
                    break
        if tag not in INLINE_TAGS:
            self._break()

    def handle_data(self, data):
        if self._in_title or self._in_h1 or self._in_ld:
            self._buffer.append(data)
        if self._in_title or self._in_ld or self._skip:
            return
        self.text.append(data)
        if not self._boiler:
            self.main.append(data)

    def visible_text(self):
        return ' '.join(''.join(self.text).split())

    def main_text(self):
        return ' '.join(''.join(self.main).split())


def normalize(text):
    """Fold the differences a copied quote picks up: entities, invisible characters, case,
    quotes, dashes, spacing, and the markdown a fetch tool adds."""
    text = html.unescape(text or '').translate(INVISIBLE)
    text = unicodedata.normalize('NFKC', text)
    text = text.translate(DASHES).translate(QUOTES).replace('…', '...')
    text = MARKDOWN_LINK.sub(r'\1', text).translate(MARKDOWN_MARKS)
    return ' '.join(text.casefold().split())


def fold(text):
    """normalize, then strip diacritics: for matching fixed phrases, never for quotes."""
    decomposed = unicodedata.normalize('NFKD', normalize(text))
    return ''.join(c for c in decomposed if not unicodedata.combining(c))


def quote_fragments(quote):
    """An excerpt with an ellipsis is several fragments that must all be present, in order."""
    q = normalize(MARKDOWN_BLOCK.sub('', quote or '')).strip('"\' ')
    parts = [p.strip('"\' ') for p in re.split(r'\[?\.\.\.\]?', q)]
    return [p for p in parts if len(p) >= 3]


def quote_present(quote, haystacks):
    fragments = quote_fragments(quote)
    if not fragments:
        return None
    for hay in haystacks:
        position = 0
        for fragment in fragments:
            found = hay.find(fragment, position)
            if found < 0:
                break
            position = found + len(fragment)
        else:
            return True
    return False


def _find_words(words, page, start):
    first = words[0]
    for i in range(start, len(page) - len(words) + 1):
        if page[i] == first and page[i:i + len(words)] == words:
            return i
    return -1


def _best_window(words, page, start):
    """Best in-order alignment of words against a window of page[start:], as (score, end)."""
    n = len(words)
    if len(page) - start < 1:
        return 0.0, start
    need = Counter(words)
    window = Counter(w for w in page[start:start + n] if w in need)
    overlap = sum(min(c, window[w]) for w, c in need.items())
    floor = max(1, int(0.6 * n))
    candidates = [(overlap, start)] if overlap >= floor else []
    for i in range(start + 1, len(page) - n + 1):
        out, inn = page[i - 1], page[i + n - 1]
        if out in need:
            if window[out] <= need[out]:
                overlap -= 1
            window[out] -= 1
        if inn in need:
            if window[inn] < need[inn]:
                overlap += 1
            window[inn] += 1
        if overlap >= floor:
            candidates.append((overlap, i))
    slack = max(2, n // 4)
    best = (0.0, start)
    for _overlap, i in nlargest(FUZZY_CANDIDATES, candidates):
        lo = max(start, i - slack)
        segment = page[lo:i + n + slack]
        blocks = [b for b in SequenceMatcher(None, words, segment, autojunk=False).get_matching_blocks() if b.size]
        if not blocks:
            continue
        matched = sum(b.size for b in blocks)
        span = blocks[-1].b + blocks[-1].size - blocks[0].b
        score = 2 * matched / (n + span)
        if score > best[0]:
            best = (score, lo + blocks[-1].b + blocks[-1].size)
    return best


def fuzzy_similarity(quote, haystack):
    """0..1: the weakest fragment's alignment score, fragments taken in order. None when the
    quote has no usable fragment."""
    fragments = quote_fragments(quote)
    if not fragments:
        return None
    page = WORD.findall(haystack)
    position = 0
    scores = []
    for fragment in fragments:
        words = WORD.findall(fragment)
        if not words:
            continue
        if len(words) < FUZZY_MIN_WORDS:
            found = _find_words(words, page, position)
            if found < 0:
                return 0.0
            scores.append(1.0)
            position = found + len(words)
            continue
        score, position = _best_window(words, page, position)
        scores.append(score)
    return round(min(scores), 3) if scores else None


def quote_digest(quote):
    """FNV-1a (32 bit) over the UTF-16 code units of the quote exactly as received, so a caller
    can prove the checker saw the excerpt it sent. research.js computes the same function."""
    data = str(quote or '').encode('utf-16-le', 'surrogatepass')
    value = 0x811c9dc5
    for i in range(0, len(data), 2):
        value ^= data[i] | (data[i + 1] << 8)
        value = (value * 0x01000193) & 0xffffffff
    return f'{value:08x}'


# ---- address policy -----------------------------------------------------------------------------

def _embedded_ipv4(address):
    if address.version != 6:
        return []
    inner = []
    if address.ipv4_mapped:
        inner.append(address.ipv4_mapped)
    if address.sixtofour:
        inner.append(address.sixtofour)
    if address.teredo:
        inner.extend(address.teredo)
    if address in NAT64:
        inner.append(ipaddress.IPv4Address(int(address) & 0xffffffff))
    return inner


def address_refused(ip_text):
    """True for any address that is not publicly routable, or an IPv6 form that carries one."""
    address = ipaddress.ip_address(str(ip_text).split('%')[0])
    for a in [address] + _embedded_ipv4(address):
        if (not a.is_global or a.is_private or a.is_loopback or a.is_link_local or a.is_multicast
                or a.is_reserved or a.is_unspecified):
            return True
    return False


def host_refused(host):
    name = (host or '').lower().rstrip('.')
    return name == 'ts.net' or name.endswith('.ts.net')


def resolve_checked(host, port, allow_private):
    """Resolve once and validate every answer. The caller connects only to what this returns."""
    if not allow_private and host_refused(host):
        raise RefusedAddress(f'refused: {host} is a tailnet name')
    infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    if not allow_private:
        for info in infos:
            if address_refused(info[4][0]):
                raise RefusedAddress(f'refused: {host} resolves to a private or local (non-public) address')
    return infos


def open_pinned_socket(address, timeout, source_address, allow_private):
    """socket.create_connection, except that it connects to the addresses it has just validated
    and never resolves the name a second time."""
    host, port = address
    error = None
    for family, socktype, proto, _canonical, sockaddr in resolve_checked(host, port, allow_private):
        sock = socket.socket(family, socktype, proto)
        try:
            if isinstance(timeout, (int, float)):
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            error = exc
            sock.close()
    raise error or OSError(f'no address found for {host}')


class PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, allow_private=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = lambda address, timeout=None, source_address=None: open_pinned_socket(
            address, timeout, source_address, allow_private)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    # HTTPSConnection.connect wraps the pinned socket with server_hostname=self.host, so SNI and
    # certificate verification still use the hostname, not the pinned address.
    def __init__(self, *args, allow_private=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = lambda address, timeout=None, source_address=None: open_pinned_socket(
            address, timeout, source_address, allow_private)


class PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, allow_private):
        super().__init__()
        self._allow_private = allow_private

    def http_open(self, req):
        return self.do_open(PinnedHTTPConnection, req, allow_private=self._allow_private)


class PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, allow_private):
        super().__init__()
        self._allow_private = allow_private

    def https_open(self, req):
        return self.do_open(PinnedHTTPSConnection, req, context=self._context, allow_private=self._allow_private)


def check_address(url, allow_private):
    """The cheap refusals that need no DNS: the scheme and tailnet names. Addresses are checked
    where the socket connects (open_pinned_socket), on every hop."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise RefusedAddress(f'not an http(s) URL: {url[:200]}')
    if not allow_private and host_refused(parts.hostname):
        raise RefusedAddress(f'refused: {parts.hostname} is a tailnet name')


def make_opener(hops, allow_private):
    class RecordingRedirect(urllib.request.HTTPRedirectHandler):
        max_redirections = MAX_REDIRECTS

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            check_address(newurl, allow_private)
            hops.append(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        PinnedHTTPHandler(allow_private),
        PinnedHTTPSHandler(allow_private),
        RecordingRedirect(),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )


# ---- fetch --------------------------------------------------------------------------------------

def read_capped(response, max_bytes, deadline):
    chunks = []
    total = 0
    truncated = False
    while True:
        if time.monotonic() > deadline:
            truncated = True
            break
        chunk = response.read(65536)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            truncated = True
            break
    return b''.join(chunks)[:max_bytes], truncated


def decode_body(raw, encoding, content_type, max_bytes):
    """Return (text, truncated, failed). truncated: decompression stopped at max_bytes, so the
    text is a prefix. failed: a content encoding this script cannot undo, so the text is noise."""
    truncated = failed = False
    encoding = (encoding or '').lower().strip()
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        # MAX_WBITS | 32 accepts both gzip and zlib headers; some servers send raw deflate,
        # hence the second attempt. max_length bounds a decompression bomb.
        for wbits in (zlib.MAX_WBITS | 32, -zlib.MAX_WBITS):
            try:
                inflater = zlib.decompressobj(wbits)
                out = inflater.decompress(raw, max_bytes)
            except zlib.error:
                continue
            truncated = bool(inflater.unconsumed_tail) or (len(out) >= max_bytes and not inflater.eof)
            raw = out
            break
        else:
            failed = True
    elif encoding not in ('', 'identity'):
        failed = True  # br, zstd and the rest were not requested and cannot be read here
    charset = ''
    match = re.search(r'charset=([\w-]+)', content_type or '', re.I)
    if match:
        charset = match.group(1)
    else:
        sniff = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:4096], re.I)
        if sniff:
            charset = sniff.group(1).decode('ascii', 'ignore')
    try:
        text = raw.decode(charset or 'utf-8', errors='replace')
    except LookupError:
        text = raw.decode('utf-8', errors='replace')
    return text, truncated, failed


def fetch(url, timeout, max_bytes, allow_private):
    """One GET with redirects and up to two meta refreshes. Never raises."""
    result = {'url': url, 'final_url': url, 'http_status': None, 'redirects': [], 'error': None,
              'content_type': '', 'body': '', 'bytes_read': 0, 'truncated': False, 'meta_refresh': False,
              'decode_failed': False}
    current = url
    deadline = time.monotonic() + timeout * 3
    for _refresh in range(MAX_META_REFRESH + 1):
        hops = []
        try:
            check_address(current, allow_private)
            opener = make_opener(hops, allow_private)
            request = urllib.request.Request(current, headers=HEADERS)
            try:
                response = opener.open(request, timeout=timeout)
            except urllib.error.HTTPError as error:
                if 300 <= error.code < 400:
                    # urllib raises a 3xx only when it gives up following: a loop or too many hops.
                    result['redirects'].extend(hops)
                    result['http_status'] = error.code
                    result['error'] = f'HTTP {error.code}: redirect loop or more than {MAX_REDIRECTS} redirects'
                    return result
                response = error  # a 4xx/5xx is a response too; its body identifies challenge pages
            status = response.getcode()
            headers = response.headers or {}
            final_url = response.geturl() or current
            try:
                raw, truncated = read_capped(response, max_bytes, deadline)
            except AttributeError:
                raw, truncated = b'', False  # an HTTPError without a body
            finally:
                response.close()
            result['redirects'].extend(hops)
            result['http_status'] = status
            result['final_url'] = final_url
            result['content_type'] = headers.get('Content-Type', '') or ''
            result['bytes_read'] += len(raw)
            body, decode_truncated, decode_failed = decode_body(
                raw, headers.get('Content-Encoding', ''), result['content_type'], max_bytes)
            result['truncated'] = truncated or decode_truncated
            result['decode_failed'] = decode_failed
            result['body'] = body
        except RefusedAddress as error:
            result['redirects'].extend(hops)
            result['error'] = str(error)
            return result
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError, ValueError) as error:
            result['redirects'].extend(hops)
            reason = getattr(error, 'reason', error)
            result['error'] = f'{type(error).__name__}: {reason}'[:300]
            return result
        refresh = meta_refresh_target(result)
        if not refresh or result['http_status'] is None or not (200 <= result['http_status'] < 300):
            return result
        current = urllib.parse.urljoin(result['final_url'], refresh)
        result['redirects'].append(current)
        result['meta_refresh'] = True
    return result


def meta_refresh_target(result):
    if 'html' not in result['content_type'].lower() and not result['body'].lstrip().startswith('<'):
        return ''
    match = re.search(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]*>', result['body'][:20000], re.I)
    if not match:
        return ''
    content = re.search(r'content=["\']?\s*(\d+)\s*;\s*url\s*=\s*["\']?([^"\'>]+)', match.group(0), re.I)
    if not content or int(content.group(1)) > 10:
        return ''
    return content.group(2).strip()


# ---- classify -----------------------------------------------------------------------------------

def path_segments(url):
    return [s for s in urllib.parse.urlsplit(url).path.lower().split('/') if s]


def root_like(segments):
    if not segments:
        return True
    if len(segments) == 1 and (segments[0] in ROOT_LIKE_SEGMENTS or LOCALE_SEGMENT.match(segments[0])):
        return True
    return len(segments) == 2 and LOCALE_SEGMENT.match(segments[0]) and segments[1] in ROOT_LIKE_SEGMENTS


def same_page(orig_segments, final_segments):
    """/x/index.html landing on /x/, or /x/amp landing on /x, is the same page, not a soft 404."""
    return bool(orig_segments) and orig_segments[-1] in SAME_PAGE_TAILS and orig_segments[:-1] == final_segments


def is_login_url(url):
    parts = urllib.parse.urlsplit(url.lower())
    labels = (parts.hostname or '').split('.')
    if labels and labels[0] in LOGIN_HOST_LABELS:
        return True
    return any(s in LOGIN_SEGMENTS for s in path_segments(url))


def is_consent_url(url):
    parts = urllib.parse.urlsplit(url.lower())
    labels = (parts.hostname or '').split('.')
    if labels and labels[0] in CONSENT_HOST_LABELS:
        return True
    return any(s in CONSENT_SEGMENTS for s in path_segments(url))


def is_login_title(title):
    return any(LOGIN_TITLE_SEGMENT.match(part.strip()) for part in TITLE_SEPARATORS.split(fold(title)) if part.strip())


def ld_json_paywalled(blocks):
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'isAccessibleForFree' and (value is False or str(value).strip().lower() in ('false', 'no')):
                    return True
                if walk(value):
                    return True
        elif isinstance(node, list):
            return any(walk(item) for item in node)
        return False

    for block in blocks:
        try:
            if walk(json.loads(block)):
                return True
        except ValueError:
            if ACCESS_FALSE.search(block):
                return True
    return False


def verdict(name, reason, quote_found=None, quote_match=None, quote_similarity=None, **base):
    return {'verdict': name, 'reason': reason, 'quote_found': quote_found, 'quote_match': quote_match,
            'quote_similarity': quote_similarity, **base}


def classify(page, quote):
    """Turn one fetch into a verdict. Pure: no I/O, so the rules are unit-testable."""
    status = page['http_status']
    signals = []
    if page['error']:
        return verdict('UNREACHABLE', page['error'], signals=signals, title='')

    content_type = page['content_type'].lower()
    body = page['body']
    decode_failed = bool(page.get('decode_failed'))
    is_html = not decode_failed and ('html' in content_type or (not content_type and body.lstrip()[:1] == '<'))
    parser = PageParser()
    if is_html:
        try:
            parser.feed(body)
            parser.close()
        except Exception as error:  # a malformed page must still get a verdict, never a crash
            signals.append(f'html_parse_error:{type(error).__name__}')
    title = parser.title[:150]
    text = parser.visible_text() if is_html else ' '.join(body.split())
    main = parser.main_text() if is_html else text
    truncated = bool(page['truncated'])
    if truncated:
        signals.append('truncated')
    if decode_failed:
        signals.append('decode_failed')
    lower_body = body[:200000].lower()
    challenge = bool(CHALLENGE_TITLE.search(title)) or any(m in lower_body for m in CHALLENGE_MARKERS)
    base = {'signals': signals, 'title': title}

    if status in (401, 407):
        return verdict('LOGIN_WALL', f'HTTP {status}: authentication required', **base)
    if status in (403, 405, 406, 429, 451, 999) or (status == 503 and challenge):
        kind = 'bot challenge page' if challenge else 'access refused'
        return verdict('BLOCKED', f'HTTP {status}: {kind}', **base)
    if status in (404, 410):
        return verdict('UNREACHABLE', f'HTTP {status}: page does not exist', **base)
    if status is None or not (200 <= status < 300):
        return verdict('UNREACHABLE', f'HTTP {status}: no usable response', **base)

    textual = not decode_failed and (is_html or content_type.startswith(TEXT_TYPES) or not content_type)
    haystack = normalize(text) if quote and textual else ''
    quote_found = quote_present(quote, [haystack]) if quote and textual else None
    if quote_found is True:
        # Word for word in the text a reader sees: the page carries the excerpt, whatever else it is.
        return verdict('REACHED', 'quoted excerpt found on the page', quote_found=True, quote_match='exact',
                       quote_similarity=1.0, **base)
    if challenge and len(text) < NOT_FOUND_PAGE_MAX_CHARS:
        return verdict('BLOCKED', f'HTTP {status}: bot challenge page', quote_found=quote_found, **base)

    # From here on the quote was not found, or none was given: identify the walls first, so an
    # unread page never becomes "the source does not say this".
    original = page['url']
    final = page['final_url']
    redirected = bool(page['redirects']) and final != original
    orig_segments = path_segments(original)
    final_segments = path_segments(final)
    wall = {'quote_found': quote_found, **base}

    if redirected and is_login_url(final) and not is_login_url(original):
        return verdict('LOGIN_WALL', 'redirected to a login page', **wall)
    if redirected and any(s in PAYWALL_SEGMENTS for s in final_segments):
        return verdict('PAYWALLED', 'redirected to a subscription page', **wall)
    if redirected and is_consent_url(final) and not is_consent_url(original):
        return verdict('CONSENT_WALL', 'redirected to a cookie-consent page', **wall)

    access_meta = [m for m in parser.meta if m.get('itemprop', '').lower() == 'isaccessibleforfree']
    tier_locked = any(m.get('property', '').lower() == 'article:content_tier'
                      and m.get('content', '').lower() == 'locked' for m in parser.meta)
    if ld_json_paywalled(parser.ld_json) or tier_locked or any(
            m.get('content', '').strip().lower() in ('false', 'no') for m in access_meta):
        return verdict('PAYWALLED', 'page marks its content isAccessibleForFree false', **wall)

    if is_html:
        folded = fold(f'{title} {text}')
        if PAYWALL_TEXT.search(folded):
            return verdict('PAYWALLED', 'the page text says the article is for subscribers only', **wall)
        if len(main) < CONSENT_PAGE_MAX_CHARS and sum(1 for p in CONSENT_TEXT if p.search(folded)) >= 2:
            return verdict('CONSENT_WALL', 'the page is a cookie-consent dialog', **wall)
        if parser.password_inputs and (len(main) < LOGIN_PAGE_MAX_CHARS or is_login_title(title)):
            return verdict('LOGIN_WALL', 'a login form dominates the page', **wall)

    if redirected and orig_segments and not root_like(orig_segments) and not same_page(orig_segments, final_segments):
        if root_like(final_segments):
            return verdict('SOFT_404', 'a deep URL redirected to the site root', **wall)
        if len(final_segments) < len(orig_segments) and orig_segments[:len(final_segments)] == final_segments:
            return verdict('SOFT_404', 'a deep URL redirected to a parent section', **wall)
    if redirected and final_segments and final_segments[-1] in NOT_FOUND_SEGMENTS:
        return verdict('SOFT_404', 'redirected to a not-found page', **wall)
    if is_html:
        h1_says = any(NOT_FOUND_TEXT.search(h) for h in parser.h1[:3])
        if NOT_FOUND_TEXT.search(title) and (len(text) < NOT_FOUND_PAGE_MAX_CHARS or h1_says):
            return verdict('SOFT_404', 'HTTP 200 page that says not found', **wall)
        if h1_says and len(text) < NOT_FOUND_PAGE_MAX_CHARS:
            return verdict('SOFT_404', 'HTTP 200 page that says not found', **wall)
        canonical = urllib.parse.urljoin(final, parser.canonical) if parser.canonical else ''
        if canonical and orig_segments and not root_like(orig_segments) and root_like(path_segments(canonical)):
            return verdict('SOFT_404', 'a deep URL whose canonical is the site root', **wall)

    if redirected and final_segments != orig_segments and not same_page(orig_segments, final_segments):
        signals.append('redirected_to_different_path')
    if decode_failed:
        return verdict('NO_CONTENT', 'the body uses a content encoding this script cannot decode', **base)
    if not textual:
        # The address answered, but nothing here can read inside a PDF or an image: reaching a file
        # is not reading it, so this never counts as a read source, quote or no quote.
        return verdict('REACHED_UNCHECKED', 'non-text content (such as a PDF) this script cannot read inside; '
                       'neither the content nor the excerpt was checked', **base)
    if len(main) < (MIN_MAIN_CHARS if is_html else MIN_CONTENT_CHARS):
        signals.append('little_main_text')
        return verdict('NO_CONTENT', 'too little readable main text once navigation, header and footer are '
                       'removed (likely rendered by JavaScript)', quote_found=quote_found, **base)
    if quote_found is None:
        return verdict('REACHED', 'page read; no quote given', **base)

    similarity = fuzzy_similarity(quote, haystack)
    if similarity is not None and similarity >= FUZZY_THRESHOLD:
        return verdict('REACHED_QUOTE_FUZZY', 'page read; a passage matches the excerpt closely but not word for word',
                       quote_found=False, quote_match='fuzzy', quote_similarity=similarity, **base)
    if truncated:
        return verdict('TRUNCATED', 'only part of the page was read and the excerpt is not in that part',
                       quote_found=False, quote_match='none', quote_similarity=similarity, **base)
    return verdict('REACHED_QUOTE_MISSING', 'page read; the excerpt is not in its readable text',
                   quote_found=False, quote_match='none', quote_similarity=similarity, **base)


# ---- report -------------------------------------------------------------------------------------

COMPACT_FIELDS = ('id', 'url', 'final_url', 'verdict', 'reason', 'http_status', 'quote_found', 'quote_match',
                  'quote_similarity', 'truncated', 'signals', 'quote_digest')


def plain(value, limit):
    """One line, no control characters, capped: for any text a model will read from the output."""
    text = ''.join(c if c.isprintable() else ' ' for c in str(value or ''))
    return ' '.join(text.split())[:limit]


def safe_url(url, limit=500):
    return urllib.parse.quote(plain(url, 2000), safe=":/?#[]@!$&'()*+,;=%~-._")[:limit]


def check(url, quote=None, timeout=DEFAULT_TIMEOUT, max_bytes=DEFAULT_MAX_BYTES, allow_private=False):
    url = (url or '').strip()
    page = fetch(url, timeout, max_bytes, allow_private)
    return report(page, quote)


def report(page, quote):
    outcome = classify(page, quote)
    return {
        'url': page['url'],
        'final_url': page['final_url'],
        'http_status': page['http_status'],
        'redirects': page['redirects'],
        'verdict': outcome['verdict'],
        'reason': outcome['reason'],
        'quote_found': outcome['quote_found'],
        'quote_match': outcome['quote_match'],
        'quote_similarity': outcome['quote_similarity'],
        'title': outcome['title'],
        'content_type': page['content_type'].split(';')[0].strip(),
        'bytes_read': page['bytes_read'],
        'truncated': bool(page['truncated']),
        'signals': outcome['signals'],
        'quote_digest': quote_digest(quote),
    }


def compact(entry):
    out = {key: entry.get(key) for key in COMPACT_FIELDS}
    out['final_url'] = safe_url(entry.get('final_url'))
    out['reason'] = plain(entry.get('reason'), 200)
    return out


def check_batch(items, timeout=DEFAULT_TIMEOUT, max_bytes=DEFAULT_MAX_BYTES, workers=DEFAULT_WORKERS,
                allow_private=False):
    """Fetch every distinct URL once, then classify each item against its own quote."""
    urls = []
    for item in items:
        url = str(item.get('url') or '').strip()
        if url not in urls:
            urls.append(url)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        pages = dict(zip(urls, pool.map(lambda u: fetch(u, timeout, max_bytes, allow_private), urls)))
    results = []
    for index, item in enumerate(items):
        url = str(item.get('url') or '').strip()
        entry = report(pages[url], item.get('quote'))
        entry['id'] = str(item.get('id', index))
        results.append(entry)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Deterministic source reachability check. Write the URLs and quotes to a JSON file '
                    'with the Write tool and pass its path; never put page text on a command line.')
    parser.add_argument('--batch', metavar='FILE', required=True,
                        help='JSON array of {id, url, quote}; "-" reads stdin (for programs, not agents)')
    parser.add_argument('--compact', action='store_true',
                        help='only the fields the checker decides; no title, no redirect list')
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument('--max-bytes', type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    parser.add_argument('--allow-private', action='store_true')
    args = parser.parse_args(argv)
    options = {'timeout': args.timeout, 'max_bytes': args.max_bytes, 'allow_private': args.allow_private}

    try:
        if args.batch == '-':
            raw = sys.stdin.read()
        else:
            with open(args.batch, encoding='utf-8') as handle:
                raw = handle.read()
        items = json.loads(raw)
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ValueError('the batch must be a JSON array of objects')
    except (OSError, ValueError) as error:
        print(json.dumps({'error': f'unreadable batch: {error}'}))
        return 2
    results = check_batch(items, workers=args.workers, **options)
    if args.compact:
        for entry in results:
            print(json.dumps(compact(entry), ensure_ascii=False))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
