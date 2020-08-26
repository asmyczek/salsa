# -*- coding: utf-8 -*-
"""
salsa.py - Load shedding API for CityPower customers
"""

from typing import Callable, Any, Dict
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from json import dumps, loads
from os.path import isfile
from datetime import datetime, timedelta, timezone


HEADERS = {'Accept': 'application/json;odata=verbose'}
API_GET_STATUS = "http://loadshedding.eskom.co.za/LoadShedding/GetStatus?_={timestamp}"
API_GET_SUBURBS = "https://www.citypower.co.za/_api/web/lists/getByTitle('LoadSheddingSuburb')/items?"\
                  "$select=*,SubBlock/Title&$expand=SubBlock&$top=2000"
API_GET_SCHEDULE = "https://www.citypower.co.za/_api/web/lists/getByTitle('Loadshedding')/items?"\
                   "$select=*&$filter=Title%20eq%20'Stage{stage}'%20and%20substringof('{block}',SubBlock)&$top=2000"

SUBURBS_CACHE_FILE = 'suburbs.json'


def time_in_millis(time: datetime) -> int:
    return int(round(time.timestamp() * 1000))


def http_get(url: str, parser: Callable = lambda x: x) -> Any:
    request = Request(url, headers=HEADERS)
    try:
        response = urlopen(request)
    except HTTPError as e:
        print('Server error.')
        print('Error code: ', e.code)
    except URLError as e:
        print('Server not available.')
        print('Reason: ', e.reason)
    else:
        result = loads(response.read())
        return parser(result)


def load_suburbs() -> [str]:
    with open(SUBURBS_CACHE_FILE, 'r') as file:
        return loads(file.read())


def get_suburbs(force_fetch: bool = False) -> [str]:
    subs = load_suburbs() if isfile(SUBURBS_CACHE_FILE) and not force_fetch else \
        http_get(API_GET_SUBURBS, lambda res: [{'title': r['Title'],
                                                'id': r['ID'],
                                                'block': r['SubBlock']['Title']}
                                               for r in res['d']['results']])
    with open(SUBURBS_CACHE_FILE, 'w') as file:
        file.write(dumps(subs))
    return subs;


def get_block(name: str = None, block: str = None) -> str:
    if block:
        ublock = block.upper()
        for suburb in get_suburbs():
            if suburb['block'] == ublock:
                return ublock
        raise ValueError(f'Block {ublock} does not exist')
    elif name:
        suburbs = find_suburb(name)
        if len(suburbs) == 1:
            return suburbs[0]['block']
        raise ValueError(f'Suburb \'{name}\' does not exist' if len(suburbs) == 0 else
                         f'Found {len(suburbs)} suburbs \'{name}\', find block id and us it for schedule query.')
    else:
        raise ValueError(f'No name nor block provided.')


def find_suburb(name: str = None, block: str = None) -> [Dict]:
    subs = get_suburbs()
    if block:
        ublock = block.upper()
        return sorted([s for s in subs if s['block'] == ublock], key=lambda s: s['title'])
    elif name:
        name_str = name.lower()
        return sorted([s for s in subs if name_str in s['title'].lower()], key=lambda s: s['title'])
    else:
        raise ValueError("Provide name or block id")


def get_stage() -> int:
    return http_get(API_GET_STATUS.format(timestamp=str(time_in_millis(datetime.now())))) - 1


def get_schedule(stage: int,
                 name: str = None,
                 block: str = None,
                 from_date: datetime = None,
                 days: int = 7) -> [Dict]:
    if not name and not block:
        raise ValueError("Provide name or block id")
    block_id = get_block(name=name, block=block)
    if not from_date:
        from_date = datetime.now().replace(tzinfo=timezone.utc, hour=0, minute=0, second=0).astimezone(tz=None)
    to_datetime = lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz=None)
    schedule = http_get(API_GET_SCHEDULE.format(block=block_id, stage=stage),
                        lambda res: [{'level': r['Title'],
                                      'id': r['ID'],
                                      'start': to_datetime(r['EventDate']),
                                      'end': to_datetime(r['EndDate'])}
                                     for r in res['d']['results']])
    sorted(schedule, key=lambda s: s['start'])
    to_date = from_date + timedelta(days=days)
    return {'block': block_id,
            'stage': stage,
            'schedule': [s for s in schedule if from_date <= s['start'] <= to_date]}
