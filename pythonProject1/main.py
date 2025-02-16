from fileinput import filename
from http.client import responses

import requests
from bs4 import BeautifulSoup
import smtplib
import time
import os
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import random
import time

PREVIOUS_ADS_FILEE = "previous_ads.json"
file_name = "ads_backup.txt"

def load_previous_ads():
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            ads = set(line.strip() for line in file.readlines())
            return ads
    return set()

def save_previous_ads(ads):
    with open(file_name, "w") as file:
        for ad_id in ads:
            file.write(f"{ad_id}\n")

previous_ads = load_previous_ads()



# def load_previous_ads():
#     if os.path.exists(PREVIOUS_ADS_FILEE):
#         with open(PREVIOUS_ADS_FILEE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return {}
#
# def save_ads(ads):
#     with open(PREVIOUS_ADS_FILEE, "w", encoding="utf-8") as f:
#         json.dump(ads, f, indent=4, ensure_ascii=False)
#

def update_url_page(url, new_page):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    query_params['page'] = [str(new_page)]

    new_query = urlencode(query_params, doseq=True)#doseq - zmienia listę na odpiwednie paaramety
    new_url = urlunparse(parsed_url._replace(query=new_query))

    return new_url



def fetch_ads():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    ]
    base_url = ("https://www.olx.pl/motoryzacja/dostawcze/q-iveco-daily/?search%5Bfilter_float_price%3Ato%5D=150000&search%5Bfilter_float_year%3Afrom%5D=2003&search%5Border%5D=created_at%3Adesc")
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    ads = []
    page = 1
    count_ad = 0
    while True:
        url = base_url if page == 1 else update_url_page(base_url, page)
        print(f"Proba pobrania strony: {url}\n")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            ###
            filename = "olx2.html"
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
                print(f"Strona zapisana do pliku: {filename}\n")
            #####

            soup = BeautifulSoup(response.text, "html.parser")
            listing_grid = soup.find("div", {"data-testid": "listing-grid"}) #ogloszenia div

            #print(listing_grid.text)

            if not listing_grid:
                print("Nie znaleziono kontenera z ogłoszeniami.")
                break

            ad_elements = listing_grid.find_all("div", {"data-cy": "l-card"})
            #print(ad_elements)
            counter = 1
            for ad in ad_elements:
                count_ad+=1
                try:
                    #print(counter)
                    #print(ad.text)
                    counter+=1
                    ad_link_element = ad.find("a", class_=["css-qo0cxu"])
                    #print(ad_link_element)
                    if ad_link_element:
                        ad_link = ad_link_element["href"]
                        if ad_link.startswith("/"):
                            ad_link = "https://www.olx.pl" + ad_link
                    else:
                        ad_link = None

                    if ad_link is None or ad_link in previous_ads:
                        continue

                    title_element = ad.find("h4", class_=["css-1sq4ur2"])
                    #print(title_element)
                    title = title_element.text.strip() if title_element else "Brak tytułu"

                    price_element = ad.find("p", {"data-testid": "ad-price"})
                    price = price_element.text.strip() if price_element else "Brak ceny"

                    #TODO dla img usunąc size na koncu linku
                    image_element = ad.find("img", class_=["css-8wsg1m", "css-1bmvjcs"])
                    image_url = image_element.get(
                        'src') if image_element else "/app/static/media/no_thumbnail.15f456ec5.svg"

                    location_element = ad.find("p", {"data-testid": "location-date"})
                    location_and_date = location_element.text.strip() if location_element else "Brak lokalizacji i daty"
                    parts = location_and_date.split("-")
                    location = parts[0].strip()
                    date = "-".join(parts[1:]).strip()

                    print(f"Nowe ogłoszenie: {title}")
                    print(f"  Link: {ad_link}")
                    print(f"  Cena: {price}")
                    print(f"  Zdjęcie: {image_url}")
                    print(f"  Lokalizacja: {location}")
                    print(f"  Data: {date}")
                    print("-" * 30)

                    previous_ads.add(ad_link)
                    new_ads_found = True

                except AttributeError as e:
                    print(f"Błąd parsowania ogłoszenia: {e}")
                    print(f"Problematic ad element HTML:\n{ad}")
                    continue
                except Exception as e:
                    print(f"Nieoczekiwany błąd przy ogłoszeniu: {e}, {ad_link=}")
                    continue

            page += 1
            if page > 25:  # Limit stron
                print("liczba ogloszen: ", count_ad)
                break
        except Exception as e:
            print("BŁĄD pobierania strony lub z bs4", e)
            break
        print("liczba ogloszen: ", count_ad)

        # soup = BeautifulSoup(response.text, "html.parser")
        # ad_elelements = soup.find("div", {"data-cy": "l-card"})
        #
        # if not ad_elelements:
        #     print("BRAK OGŁOSZEN")
        #
        # for ad in ad_elelements:
        #     #pobierz ogłoszenie, zapisz do listy widzianych ogłoszeń link (ogłoszenia do ototomoto mają pełny link, ale te do olx mają urwany początek bo prowadzą do postrony, nie innego serwisu)
        #     #wyprintuj title ogłoszenia, cenę, link do zdjęcia jeśli już nie oglądaliśmy tego ogłoszenia. Jesli ogladaliśmy to pomiń
        #     ad_id=ad["id"]
        #     ad_link = ad.find("a",{"class": "css-qo0cxu"})["href"]
        print("liczba ogloszen: ", count_ad)

        if page >= 25:
            break


def main():
    #previous_ads = load_previous_ads()
    print("hello")
    #w pliku można zapisywac wszystkie ogłoszenia ale jeślid ata dodania jest więsza niż np. 2 msc to usuną c ogłoszenie
    #TODO albo nowe ogłoszenie porórywać tylko do ostatnich 30
    fetch_ads()
    # while True:
    #     ads = fetch_ads()
    #     new_ads = []
    #     for


if __name__ == "__main__":
    main()

