import os
import requests
from bs4 import BeautifulSoup

CACHE_FOLDER = ".cache"
if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

def get_name_for_url(url: str):
    allow = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-"
    return "".join([char for char in url if char in allow])

def read_file(filename):
    with open(filename) as f:
        return f.read()

def fetch_content(url):
    return requests.get(url).text

def get_soup(url: str):
    filename = os.path.join(CACHE_FOLDER, get_name_for_url(url))

    if os.path.exists(filename):
        return BeautifulSoup(read_file(filename), features="lxml")

    content = fetch_content(url)
    with open(filename, 'w') as f:
        f.write(content)
    return BeautifulSoup(content, features="lxml")
