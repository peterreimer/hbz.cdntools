#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, urljoin
import logging
import pkg_resources

version = pkg_resources.require("hbz.cdntools")[0].version
logger = logging.getLogger('cdnparse')

IGNORE_RELS = ('dns-prefetch', 'alternate', 'search', 'shortlink')
DEFAULT_LOGFILE = "cdnparse.log"


def rels_in_ignored_rels(rels):
    """Return True if any of the rels attributes is in the IGNORE_RELS list"""

    result = False
    for rel in rels:
        if rel in IGNORE_RELS:
            result = True
            break
    return result


class CDN:

    def __init__(self, url):

        logger.info("received %s" % url)
        r = requests.get(url)
        url_final = r.url
        logger.info("parsing %s" % url_final)
        self.site = urlparse(url_final)

        self.url = urlparse(url)

        self.scheme = self.site.scheme
        self.netloc = self.site.netloc
        self.path = self.site.path
        self.soup = BeautifulSoup(r.text, features="html.parser")
        self.files = []

    def _normalize(self, url):
        """Return full url with hostname of given url.

        If the url is relativ or absolute, but without hostname, it will
        be added. External URLs are passed unchanged.
        """
        u = urlparse(url)
        if u.netloc == '':
            path = urljoin(self.path, u.path)
            url = urlunparse((self.scheme, self.netloc, path, '', '', ''))
            r = requests.head(url)
            logger.info("%s [HTTP %s]" % (url, r.status_code))
            return url
        else:
            return url

    def link(self):
        """Return all CSS files found in the head.

        Not all sites a written well and include proper rel="stylesheet" and
        type="text/css" attributes. It's safer to scrape everything and
        exclude certain rel-attributes.
        """
        head = self.soup.head
        # css_files = head.find_all(css_filter, type="text/css")
        link_files = head.find_all("link")

        for link_file in link_files:
            if link_file.has_attr('href'):
                href = link_file.attrs['href']
                logger.info("found %s" % href)
                rel = link_file.attrs.get('rel', [])      # rel is a list
                if not rels_in_ignored_rels(rel):
                    url = self._normalize(href)
                    self.files.append(url)
                    logger.info("added %s to cdn files [rel=%s]" % (url, ' '.join(rel)))
                else:
                    logger.info("ignored %s [rel=%s]" % (href, ' '.join(rel)))

    def js(self):
        """Return all JS files in head and body.

        Javascript can be everywhere, not just the head.
        type="text/javascript" is not always properly used.
        """
        js_files = self.soup.find_all("script")
        for js_file in js_files:
            if js_file.has_attr('src'):
                src = js_file.attrs['src']
                logger.info("found %s" % src)
                url = self._normalize(src)
                self.files.append(url)
                logger.info("added %s to cdn files" % url)


def main():

    parser = argparse.ArgumentParser(description='CDN gathering')
    parser.add_argument('url', help='URL of website')
    parser.add_argument('-a', '--all', action="store_true", help='include also local css/js')
    parser.add_argument('-l', '--logfile', default="cdnparse.log", help='Name of the logfile (default: %s)' % DEFAULT_LOGFILE)
    parser.add_argument('--version', action='version', version=version)

    args = parser.parse_args()
    logfile = args.logfile
    all = args.all

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    cdn = CDN(args.url)
    cdn.link()
    cdn.js()

    for url in cdn.files:
        o = urlparse(url)
        if o.netloc != cdn.netloc or all:
            print(url)


if __name__ == '__main__':

    # url = "https://stadtarchivkoblenz.wordpress.com"
    url = "https://www.vg-lingenfeld.de/vg_lingenfeld/Startseite/"
    cdn = CDN(url)
    cdn.link()
    cdn.js()
    for file in cdn.files:
        print(file)
