from flask_redis import FlaskRedis
from flask_rq2 import RQ

from ..scraper.scraper import BibleScraper, VERSION_ID_PREFIX

rq = RQ()
redis_store = FlaskRedis()
bible_scraper = BibleScraper()


@rq.job('scrap_verse')
def scrap_verse(version_id, reference, date):
    from ..main import bible_scraper
    verse = bible_scraper.scrap_verse(version_id, reference)
    key = '_'.join([date, redis_store.get(VERSION_ID_PREFIX + version_id).decode('utf8')])
    redis_store.set(key, verse)
