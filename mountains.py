import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "https://climbnz.org.nz"
INDEX_PAGE = f"{BASE_URL}/mountains"


def get_index():
    table_selector = ".view-climbnz-mountains tbody tr"

    html = requests.get(INDEX_PAGE).text
    soup = BeautifulSoup(html, features='lxml')

    rows = soup.select(table_selector)
    for row in rows:
        link = row.select_one('td.views-field-title a')
        yield (link.text, f"{BASE_URL}{link.attrs['href']}")


def download_mountain(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, features='lxml')

    def maybe_text(el: BeautifulSoup, selector: str):
        el = el.select_one(selector)
        if not el: return None

        return el.text.strip()

    def get_lat_lng():
        el = soup.select_one('.field-name-field-geo-lat-lon .field-items')
        if not el:
            return None

        return [c.strip() for c in el.text.split(',')]

    def get_img():
        el = soup.select_one('.field-name-field-image img')
        if not el:
            return None
        return el.attrs['src']

    def parse_routes():
        route_els = soup.select(
            '.view-climbnz-route-table tbody tr.route-description-row')

        for el in route_els:
            detail_row = el
            title_row = el.find_previous_sibling()
            name_el = title_row.select_one('.views-field-title')

            yield {
                'name': name_el.text.strip(),
                'link': f'{BASE_URL}{name_el.select_one("a").attrs["href"]}',
                'grade': maybe_text(title_row, '.views-field-field-grade'),
                'length': maybe_text(title_row, '.views-field-field-length'),
                'quality': len(title_row.select('.views-field-field-quality span.on')),
                'bolts':  maybe_text(title_row, '.views-field-field-bolts'),
                'natural_pro': title_row.select_one('.views-field-field-natural-pro img') is not None,
                'description': maybe_text(detail_row, '.description'),
                'ascent': maybe_text(detail_row, '.ascent'),
            }

    return {
        'link': url,
        'name': maybe_text(soup, '.page-header'),
        'altitude': maybe_text(soup, '.field-name-field-altitude .field-items'),
        'description': maybe_text(soup, '.field-name-field-description'),
        'latlng': get_lat_lng(),
        'routes': list(parse_routes()),
        'image': get_img()
    }


if __name__ == "__main__":
    mountains = {}

    from multiprocessing import Pool

    mountains = None
    with Pool() as p:
        mountains = list(p.map(download_mountain, [url for (title, url) in get_index()]))

    result = {}
    for mountain in mountains:
        result[mountain['link']] = mountain

    with open('mountains.json', 'w') as f:
        f.write(json.dumps(result, indent='\t'))
