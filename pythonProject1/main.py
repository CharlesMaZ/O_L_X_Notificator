import re
from fileinput import filename
from http.client import responses
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import smtplib
import time
import os
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import random
import time
import json

#app = Flask(__name__)

def load_config():
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    return config_data

config = load_config()

first_run = True
file_name = "ads_backup.txt"
subcsribers = set()

def load_previous_ads():
    global first_run
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            ads = set(line.strip() for line in file.readlines())
            if len(ads) > 300:
                first_run = False
            return ads
    return set()

def save_previous_ads(ads):
    with open(file_name, "w") as file:
        for ad_id in ads:
            file.write(f"{ad_id}\n")

previous_ads = load_previous_ads()


def get_og_image(url):
    """Pobiera obrazek z tagu og:image z URL"""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    og_image = soup.find('meta', property='og:image')
    if og_image:
        return og_image.get('content')
    return None


# def send_message(recipient_id, text):
def send_message(message, ad_link):
    access_token_page = config.get("fb_access_token")
    user_id= config.get("fb_user_id")
    image_url = get_og_image(ad_link)
    # message_data = {
    #     "message": {
    #         "text": message
    #     },
    #     "recipient": {
    #         "id": user_id
    #     }
    # }
    #print(ad_link)
    if not image_url:
        image_url = "https://ireland.apollo.olxcdn.com/v1/files/64eb38z9sa72-PL/image;s=516x361"
    message_data = {
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "OLX Listing",
                            "subtitle": message,
                            "image_url": image_url,
                            "default_action": {
                                "type": "web_url",
                                "url": ad_link
                            },
                            # "buttons": [
                            #     {
                            #         "type": "web_url",
                            #         "url": ad_link,
                            #         "title": "View Listing"
                            #     }
                            # ]
                        }
                    ]
                }
            }
        },
        "recipient": {
            "id": user_id
        }
    }
    print(message_data)
    url = f'https://graph.facebook.com/v21.0/me/messages?access_token={access_token_page}'
    response = requests.post(url, json=message_data)

    if response.status_code == 200:
        print("Wiadomość została wysłana!")
    else:
        print(f"Coś poszło nie tak: {response.status_code}, {response.text}")
    #
    # headers = {"Content-Type": "application/json"}
    # payload = {
    #     "recipient": {"id": recipient_id},
    #     "message": {"text": text},
    #     "messaging_type": "RESPONSE",
    #     "access_token": PAGE_ACCESS_TOKEN,
    # }
    # #TODO try catch
    # requests.post(url, headers=headers, json=payload)




def update_url_page(url, new_page):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    query_params['page'] = [str(new_page)]

    new_query = urlencode(query_params, doseq=True)#doseq - zmienia listę na odpiwednie paaramety
    new_url = urlunparse(parsed_url._replace(query=new_query))

    return new_url

def fetch_ads(page_limit=5):
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
    while page<= 25:
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

                    #czy ogłoszenei już bylo wczytane:
                    if ad_link is None or ad_link in previous_ads:
                        continue
                    else:
                        previous_ads.add(ad_link)
                        #dodac mże flage by wczytać ogłoszenia by nei wyslac wiadomosci dla każdego ogłsozenia przy czystym starcie
                    title_element = ad.find("h4", class_=["css-1sq4ur2"])
                    #print(title_element)
                    title = title_element.text.strip() if title_element else "Brak tytułu"

                    price_element = ad.find("p", {"data-testid": "ad-price"})
                    price = price_element.text.strip() if price_element else "Brak ceny"

                    #TODO dla img usunąc size na koncu linku
                    #jesli jest to link do ototomoto to zdjecie ładuje skrypt - w skrypcie jest link do zdjęcia
                    # ale w formacie /u002F więc trzeba konwertować script lub sizke i suzkac po niej image
                    img_parent = ad.find("div", class_=["css-gl6djm"])
                    #if img_parent:
                    image_element = img_parent.find("img")#class="css-x7ghln" <div class="css-gl6djm"
                    #print(image_element)
                    image_urlPre = image_element["src"]
                    #print(image_urlPre)
                    image_url = re.sub(r";s=\d+x\d+;q=\d+", "", image_urlPre)
                    #print(image_url, "<- img url")
                        #image_element.get('src')) if image_element else "/app/static/media/no_thumbnail.15f456ec5.svg"

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

                    message = (f"Nowe ogłoszenie\n: {title}\n"
                               f"  Cena: {price}\n"
                               f"  Lokalizacja: {location}\n"
                               f"  Data: {date}\n")

                    send_message(message, ad_link)
                    #send_message(ad_link)


                    previous_ads.add(ad_link)
                    if not first_run:
                        mess = ""
                        #send_mess_via_messenger(mess)
                    save_previous_ads(previous_ads)
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

        print("liczba ogloszen: ", count_ad)

        if page >= 25:
            break


def main():
    send_message("IVECO", "https://www.olx.pl/d/oferta/iveco-daily-wywrotka-kiper-35c130-plandeka-CID5-ID136JqP.html")
    global first_run
    #previous_ads = load_previous_ads()
    print("hello")
    #get_user_conversations(config.get("fb_access_token"))
    #get_user_id()
    #send_mess_via_messenger("aaa")
    #w pliku można zapisywac wszystkie ogłoszenia ale jeślid ata dodania jest więsza niż np. 2 msc to usuną c ogłoszenie
    #TODO albo nowe ogłoszenie porórywać tylko do ostatnich 30
    fetch_ads()
    first_run = False
    while True:
        fetch_ads()
        print("sleep")
        slep_time_random = random.randint(200,650)
        time.sleep(slep_time_random)


if __name__ == "__main__":
    #app.run(port=5000, debug=True)
    main()

