import requests
from bs4 import BeautifulSoup

BASE_URL = "https://climbnz.org"
INDEX_PAGE = f"{BASE_URL}/mountains"

def get_index():
    table_selector = ".view-climbnz-mountains tbody tr"
    
    html = requests.get(INDEX_PAGE).text
    soup = BeautifulSoup(html, features='lxml')

    rows = soup.select(table_selector)
    for row in rows:
        link = row.select_one('td.views-field-title a')
        yield (f"{BASE_URL}{link.text}", link.attrs['href'])

def download_mountain(url):
    pass

def download_route(url):
    pass

if __name__ == "__main__":
    for result in get_index():
        print(result)
