import os
import time

import click
from flask import Flask, jsonify
from flask import request

from .exceptions.BibleVersionNotSupportedException import BibleVersionNotSupportedException
from .lib.logger import log
from .scraper.constants import *
from .scraper.scraper import VotdScraper, BibleScraper


def create_app():
    from .jobs.jobs import rq
    from .jobs.jobs import redis_store
    from .jobs.jobs import bible_scraper
    app = Flask(__name__)
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL')
    app.config['RQ_REDIS_URL'] = os.environ.get('RQ_REDIS_URL')
    redis_store.init_app(app)
    rq.init_app(app)
    bible_scraper.init_storage(redis_store)
    return app, redis_store, bible_scraper


app, redis_store, bible_scraper = create_app()


@app.route("/votd")
def votd():
    date = time.strftime('%Y-%m-%d')
    version = request.args.get('version') if request.args.get('version') is not None else 'NIV'
    return get_votd_by_version(date, version)


def get_votd_by_version(date=time.strftime('%Y-%m-%d'), version='NIV'):
    key = '_'.join([date, version])
    log.info('Key = ' + str(key))
    votd = redis_store.get(key)
    if votd is None:
        log.info("No cache")
        scrap_votd(version)
        votd = redis_store.get(key)
    votd_json = votd.decode('utf8').replace("'", '"')
    return votd_json


@app.cli.command()
def job_scrap_votd():
    click.echo('Scraping Versions')
    version_ids = bible_scraper.scrap_version()
    click.echo('Scraping VOTD')
    votd_scraper = VotdScraper(redis_store)
    votd = votd_scraper.scrap()
    reference = redis_store.get(votd['date']).decode('utf8')
    for version_id in version_ids:
        log.info("Queue job with version_id = " + str(version_id) + " and reference = " + str(reference))
        from .jobs.jobs import scrap_verse
        scrap_verse.queue(version_id, reference, votd['date'], result_ttl=86400)


def scrap_votd(version_code='NIV'):
    version_code = version_code.upper()
    votd_scraper = VotdScraper(redis_store)
    votd = votd_scraper.scrap()
    if version_code != str(votd['version']['code']).upper():
        verse_ref = '.'.join(
            [str(votd['reference']['book_code']), str(votd['reference']['chapter']), str(votd['reference']['verse'])])
        bible_scraper = BibleScraper(redis_store)
        version_id_record = redis_store.get(VERSION_CODE_PREFIX + version_code)
        if version_id_record is None:
            raise BibleVersionNotSupportedException()
        version_id = version_id_record.decode('utf8')
        votd = bible_scraper.scrap_verse(version_id, verse_ref)
    key_elements = [
        str(votd['date']),
        str(votd['version']['code'])
    ]
    key = '_'.join(key_elements)
    log.info('Key = ' + str(key))
    redis_store.set(key, votd)


@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, BibleVersionNotSupportedException):
        code = 400
        return jsonify(error=e.error), code
    else:
        return jsonify(error='Internal Server Error'), code


@app.cli.command()
def job_scrap_bible_version():
    scraper = BibleScraper(redis_store)
    scraper.scrap_version()
