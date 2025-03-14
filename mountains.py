from soup_helper import get_soup
import json
from bs4 import BeautifulSoup

import re
numbers_only = re.compile("^[0-9]+$")

BASE_URL = "https://climbnz.org.nz"
INDEX_PAGE = f"{BASE_URL}/mountains"


def get_index():
    table_selector = ".view-climbnz-mountains tbody tr"
    soup = get_soup(INDEX_PAGE)

    rows = soup.select(table_selector)
    for row in rows:
        link = row.select_one('td.views-field-title a')
        yield (link.text, f"{BASE_URL}{link.attrs['href']}")

def resolve_url(url):
    if url.startswith('http'): return url
    if url.startswith('/'): return BASE_URL + url

    raise "Oh no! Can't resolve " + url

def maybe_text(el: BeautifulSoup, selector: str, additional_none: str=''):
    el = el.select_one(selector)
    if not el: return None

    text = el.text.strip()
    if additional_none == text:
        return None
    return text

def get_imgs(soup: BeautifulSoup):
    return [{
            'src': resolve_url(el.attrs['src']),
            'height': el.attrs['height'],
            'width': el.attrs['width']
        } for el in soup.select('.field__items img')]

def download_route(url):
    soup = get_soup(url)

    def extract_match(info: list[BeautifulSoup], predicate):
        if not info: return None

        for i in range(len(info)):
            if predicate(info[i]):
                return info.pop(i)
        return None


    def maybe_pitch_number(info: list[BeautifulSoup]):
        return extract_match(info, lambda x: x == info[0])

    def maybe_text_prefixed_by(info: list[BeautifulSoup], text: str):
        el = extract_match(info, lambda x: x.text.strip().upper().startswith(text))
        if el is not None:
            return el.text[len(text):].strip()
        return None

    def maybe_water_ice(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'WATER ICE')

    def maybe_mixed(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'MIXED')

    def maybe_trad(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'TRAD') is not None

    def maybe_commitment(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'ALPINE (COMMITMENT)')

    def maybe_mtcook(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'ALPINE (MT COOK)')

    def maybe_alpine(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'ALPINE (TECHNICAL)')

    def maybe_aid(info: list[BeautifulSoup]):
        return maybe_text_prefixed_by(info, 'AID')

    def maybe_length(info: list[BeautifulSoup]):
        el = extract_match(info, lambda x: x.text.strip().upper().endswith('M'))
        return el.text.strip() if el else None

    def maybe_ewbank(info: list[BeautifulSoup]):
        el = extract_match(info, lambda x: numbers_only.match(x.text.strip()))
        return el.text.strip() if el else None

    def maybe_bolts(info: list[BeautifulSoup]):
        el = extract_match(info, lambda x: x.select_one('.icon-bolt') is not None)
        if el is not None:
            text = el.text.strip()
            if text != '0':
                return text
        return None

    def parse_pitches(el: BeautifulSoup):
        if not el: return

        # Info from a header row is:
        # P# <Ewbank> <Water Ice WIN> <Mixed MN> <Alpine (Commitment) NN> <Alpine (Mt Cook) N> <Lengthm> <Bolts> <Trad>

        pitch_els = el.select('.pitch.row')
        for pitch_el in pitch_els:
            # Unfortunately all parts are optionally present and there's no easy way to 
            # tell them apart except by their content.
            header_parts = list(pitch_el.select('.col-lg-8 li'))

            yield {
                'alpine': maybe_alpine(header_parts),
                'commitment': maybe_commitment(header_parts),
                'mtcook': maybe_mtcook(header_parts),
                'aid': maybe_aid(header_parts),
                'ice': maybe_water_ice(header_parts),
                'mixed': maybe_mixed(header_parts),
                'length': maybe_length(header_parts),
                'bolts': maybe_bolts(header_parts),
                'trad': maybe_trad(header_parts),
                # It's important we parse ewbank grade last, as it's the hardest to tell.
                'ewbank': maybe_ewbank(header_parts),
                'description': maybe_text(pitch_el, '.pitch-desc')
            }

    pitch_el = soup.select_one('.field--name-field-climbnz-pitch .field__item')
    pitches = list(parse_pitches(pitch_el))

    images = get_imgs(soup)
    return {
        'link': url,
        'name': maybe_text(soup, '.field--name-title'),
        'grade': maybe_text(soup, '.field--name-field-climbnz-grade .field__item'),
        'topo_ref': maybe_text(soup, '.field--name-field-climbnz-reference .field__item'),
        'image': None if len(images) == 0 else images[0]['src'],
        'images': images,
        'length': maybe_text(soup, '.field--name-field-climbnz-length .field__item', additional_none='0m'),
        'pitches': pitches,
        'quality': len(soup.select('.fivestar-basic span.on')),
        'bolts': maybe_text(soup, '.field--name-field-climbnz-bolts .field__item', additional_none='0'),
        'natural_pro': soup.select_one('.field--name-field-climbnz-natural-pro .climbnz-wire') is not None,
        'description': maybe_text(soup, '.field--name-field-climbnz-description'),
        'ascent': maybe_text(soup, '.field--name-field-climbnz-first-ascent .field__item')
    }

def download_mountain(url):
    soup = get_soup(url)

    def get_lat_lng():
        el = soup.select_one('.field--name-field-climbnz-geo-lat-lon .field__item > span')
        if not el:
            return None

        (lat, lng) = list([c.strip() for c in el.text.strip().split(',')])

        # Check the values are in the expected range. This could break if the page structure changes.
        lat_f = float(lat)
        lon_f = float(lng)
        assert lat_f >= -90 and lat_f <= 90, f"Latitude {lat_f} is out of range (-90, 90) for {url}"
        assert lon_f >= -180 and lon_f <= 180, f"Longitude {lon_f} is out of range (-180, 180) for {url}"

        return (lat, lng)

    def parse_routes():
        def maybe_get_image_url(el: BeautifulSoup, route_link: str):
            has_image = el.select_one('.views-field-field-route-image .glyphicon-picture')
            if not has_image: return

            soup = get_soup(route_link)
            img = soup.select_one('.field-name-field-route-image a')
            if not img:
                print("Couldn't find image on", route_link, has_image)
                return
            return img.attrs['href']


        route_els = soup.select(
            '.field--name-field-climbnz-routes-in-place tbody tr')

        for el in route_els:
            link = el.select_one('td:nth-child(2) a')
            if link:
                href = resolve_url(link.attrs['href'])
                yield download_route(href)

    def get_places(mountain: BeautifulSoup):
        place_els = mountain.select('.view-climbnz-places-in-place tbody tr')
        for el in place_els:
            link = el.select_one('a')
            if not link: continue
            yield download_mountain(f"{BASE_URL}{link.attrs['href']}")

    images = get_imgs(soup)
    return {
        'link': url,
        'name': maybe_text(soup, '.block-page-title-block') or '',
        'altitude': maybe_text(soup, '.field--name-field-climbnz-altitude .field__item'),
        'access': maybe_text(soup, '.field--name-field-climbnz-access .field__item'),
        'description': maybe_text(soup, '.field--name-field-climbnz-description'),
        'latlng': get_lat_lng(),
        'routes': list(parse_routes()),
        'places': list(get_places(soup)),
        'image': images[0]['src'] if images else None,
        'images': images
    }

def all_places(places, depth=0):
    for place in places:
        yield place, depth

        if 'places' in place:
            for subplace_depth in all_places(place['places'], depth+1):
                yield subplace_depth

def get_sub_place_links(places):
    subplaces = set()
    for place, depth in all_places(places):
        if depth > 0:
            subplaces.add(place['link'])
    return subplaces

if __name__ == "__main__":
    mountains = {}

    from multiprocessing import Pool

    mountains = None
    with Pool(processes=100) as p:
        mountains = list(p.map(download_mountain, [url for (title, url) in get_index()]))

    # Some subplaces are listed at the top level, so we remove them.
    subplace_links = get_sub_place_links(mountains)
    mountains = [mountain for mountain in mountains if mountain['link'] not in subplace_links]

    result = {}
    for mountain in sorted(mountains, key=lambda m: m['link']):
        result[mountain['link']] = mountain

    with open('mountains.json', 'w') as f:
        f.write(json.dumps(result, indent='\t').replace('\r\n', '\n'))
