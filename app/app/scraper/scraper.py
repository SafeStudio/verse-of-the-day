import re
import time

import requests
from bs4 import BeautifulSoup

from .constants import *
from ..lib.logger import log


class VotdScraper(object):
    start_url = 'https://bible.com'
    ref_regex = '([\w|\s|:]+)(?:\s)(?:\()(\w+)(?:\))'
    ref_url_regex = '(?:\/bible\/)(\d+)(?:\/)([0-9A-Z]+)(?:\.)([\w]+)(?:\.)([\w]+)'

    def __init__(self, redis_storage):
        self.redis_storage = redis_storage

    def scrap(self):
        r = requests.get(self.start_url)
        soup = BeautifulSoup(r.text, "html.parser")
        votd_verse = soup.find('p', class_="votd-verse")
        votd_ref = soup.find('p', class_="votd-ref")
        votd_ref_link = votd_ref.find('a')
        votd_ref_text = votd_ref_link.text
        votd_ref_url = votd_ref_link['href'] if votd_ref_link.has_attr('href') else None
        log.debug('Ref URL = ' + str(votd_ref_url))
        ref_url_groups = re.search(self.ref_url_regex, votd_ref_url)
        log.debug('Ref URL Groups = ' + str(ref_url_groups))
        log.debug('Ref Text = ' + str(votd_ref_text))
        ref_groups = re.search(self.ref_regex, votd_ref_text)
        log.debug('Ref Groups = ' + str(ref_groups))
        date = time.strftime('%Y-%m-%d')
        version_code = ref_groups.group(2)
        verse = self.create_verse(date=date, verse=votd_verse.find('a').text,
                                  reference_text=ref_groups.group(1), reference_book_code=ref_url_groups.group(2),
                                  reference_chapter=ref_url_groups.group(3),
                                  reference_verse=ref_url_groups.group(4), version_id=ref_url_groups.group(1),
                                  version_code=version_code)
        key = '_'.join([date, version_code])
        self.redis_storage.set(key, verse)
        self.redis_storage.set(date,
                               '.'.join([ref_url_groups.group(2), ref_url_groups.group(3), ref_url_groups.group(4)]))
        return verse

    @staticmethod
    def create_verse(date, verse, reference_text, reference_book_code, reference_chapter, reference_verse,
                     version_id, version_code):
        verse = {
            'date': date,
            'verse': verse,
            'reference': {
                'text': reference_text.strip(),
                'book_code': reference_book_code.upper(),
                'chapter': int(reference_chapter),
                'verse': int(reference_verse),
            },
            'version': {
                'id': int(version_id),
                'code': version_code.upper(),
            },
        }
        return verse


class BibleScraper(object):
    versions_url = 'https://www.bible.com/versions'
    verses_url = 'https://nodejs.bible.com/api/bible/verses/3.1'
    version_link_regex = '(?:\/versions\/)(\d+)(?:-)([a-z0-9]+)(?:.+)'

    def __init__(self, redis_storage=None):
        if redis_storage is not None:
            self.init_storage(redis_storage)

    def init_storage(self, storage):
        self.redis_storage = storage

    def scrap_version(self):
        r = requests.get(self.versions_url)
        soup = BeautifulSoup(r.text, "html.parser")
        all_links = soup.findAll('a', href=True)
        version_ids = []
        for link in all_links:
            href = link['href'] if link.has_attr('href') else None
            if re.match(self.version_link_regex, href):
                version_link_groups = re.search(self.version_link_regex, href)
                version_id = version_link_groups.group(1).upper()
                version_ids.append(version_id)
                version_code = version_link_groups.group(2).upper()
                self.redis_storage.set(VERSION_CODE_PREFIX + str(version_code), version_id)
                self.redis_storage.set(VERSION_ID_PREFIX + str(version_id), version_code)
        return version_ids

    def scrap_verse(self, version_id, reference):
        params = {
            'id': version_id,
            'references[0]': reference,
            'format': 'text'
        }
        log.info('Params = ' + str(params))
        response = requests.get(self.verses_url, params=params)
        if response.status_code != 200:
            raise ValueError("Failed")
        verse_json = response.json()
        if 'verses' not in verse_json:
            log.error("Response has no key 'verses'")
            log.error('Params: ' + str(params))
            log.error('Response: ' + str(verse_json))
            return None
        book_reference = reference.split('.')
        version_code = self.redis_storage.get(VERSION_ID_PREFIX + str(version_id))
        if version_code is None:
            self.scrap_version()
            version_code = self.redis_storage.get(VERSION_ID_PREFIX + str(version_id))
        version_code = version_code.decode('utf8')
        date = time.strftime('%Y-%m-%d')
        verse = VotdScraper.create_verse(date=date, verse=verse_json['verses'][0]['content'],
                                         reference_text=verse_json['verses'][0]['reference']['human'],
                                         reference_book_code=book_reference[0],
                                         reference_chapter=book_reference[1],
                                         reference_verse=book_reference[2], version_id=version_id,
                                         version_code=version_code)
        key = '_'.join([date, version_code])
        self.redis_storage.set(key, verse)
        return verse
