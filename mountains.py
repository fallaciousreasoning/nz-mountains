from soup_helper import get_soup
import json
from bs4 import BeautifulSoup

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

def download_mountain(url):
    soup = get_soup(url)

    def maybe_text(el: BeautifulSoup, selector: str):
        el = el.select_one(selector)
        if not el: return None

        return el.text.strip()

    def get_lat_lng():
        el = soup.select_one('.field--name-field-climbnz-geo-lat-lon .field__item')
        if not el:
            return None

        return [c.strip() for c in el.text.strip('POINT ()').split(' ')]

    def get_imgs():
        return [{
                'src': resolve_url(el.attrs['src']),
                'height': el.attrs['height'],
                'width': el.attrs['width']
            } for el in soup.select('.field__items img')]

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

        def parse_pitches(el: BeautifulSoup):
            pitch_els = el.select('.pitches table.table tbody tr:nth-child(odd)')
            for el in pitch_els:
                detail_row = el.find_next_sibling()
                description = None
                if detail_row:
                    description = maybe_text(detail_row, 'td:nth-child(2)')
                yield {
                    'ewbank': maybe_text(el, 'td:nth-child(2)'),
                    'alpine': maybe_text(el, 'td:nth-child(3)'),
                    'commitment': maybe_text(el, 'td:nth-child(4)'),
                    'mtcook': maybe_text(el, 'td:nth-child(5)'),
                    'aid': maybe_text(el, 'td:nth-child(6)'),
                    'ice': maybe_text(el, 'td:nth-child(7)'),
                    'mixed': maybe_text(el, 'td:nth-child(8)'),
                    'boulder': maybe_text(el, 'td:nth-child(9)'),
                    'length': maybe_text(el, 'td:nth-child(10)'),
                    'bolts': maybe_text(el, 'td:nth-child(11)'),
                    'trad': maybe_text(el, 'td:nth-child(12)') == 'Yes',
                    'description': description
                }


        route_els = soup.select(
            '.view-climbnz-route-table tbody tr.route-description-row')

        for el in route_els:
            detail_row = el
            title_row = el.find_previous_sibling()
            name_el = title_row.select_one('.views-field-title')
            link = f'{BASE_URL}{name_el.select_one("a").attrs["href"]}'

            yield {
                'name': name_el.text.strip(),
                'link': link,
                'image': maybe_get_image_url(title_row, link),
                'grade': maybe_text(title_row, '.views-field-field-grade'),
                'length': maybe_text(title_row, '.views-field-field-length'),
                'pitches': list(parse_pitches(detail_row)),
                'quality': len(title_row.select('.views-field-field-quality span.on')),
                'bolts':  maybe_text(title_row, '.views-field-field-bolts'),
                'natural_pro': title_row.select_one('.views-field-field-natural-pro img') is not None,
                'description': maybe_text(detail_row, '.description'),
                'ascent': maybe_text(detail_row, '.ascent'),
            }

    def get_places(mountain: BeautifulSoup):
        place_els = mountain.select('.view-climbnz-places-in-place tbody tr')
        for el in place_els:
            link = el.select_one('a')
            if not link: continue
            yield download_mountain(f"{BASE_URL}{link.attrs['href']}")

    images = get_imgs()
    return {
        'link': url,
        'name': maybe_text(soup, '.block-page-title-block'),
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
    print(json.dumps(download_mountain('https://climbnz.org.nz/nz/si/aspiring/main-divide/mt-aspiring-tititea'), indent='\t'))
    # mountains = {}

    # from multiprocessing import Pool

    # mountains = None
    # with Pool(processes=100) as p:
    #     mountains = list(p.map(download_mountain, [url for (title, url) in get_index()]))

    # # Some subplaces are listed at the top level, so we remove them.
    # subplace_links = get_sub_place_links(mountains)
    # mountains = [mountain for mountain in mountains if mountain['link'] not in subplace_links]

    # result = {}
    # for mountain in mountains:
    #     result[mountain['link']] = mountain

    # with open('mountains.json', 'w') as f:
    #     f.write(json.dumps(result, indent='\t'))
