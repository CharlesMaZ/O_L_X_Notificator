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


app = Flask(__name__)

def load_config():
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    return config_data

config = load_config()

PAGE_ACCESS_TOKEN = config.get("fb_access_token")

first_run = True
file_name = "ads_backup.txt"
subcsribers = set()

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

def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v22.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
        "access_token": PAGE_ACCESS_TOKEN,
    }
    #TODO try catch
    requests.post(url, headers=headers, json=payload)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token"):
            request.args.get("hub.challenge")
    return "invalid verif token", 403

    data = request.get_json()

    for entry in data.get("entry", []):
        for message in entry.get("messaging", []):
            sender_id = message["sender"]["id"]
            if "message" in message and "text" in message["message"]:
                user_message = message["message"]["text"].strip().lower()

                if user_message == "start":
                    subcsribers.add(sender_id)
                    send_message(sender_id, "zapisnao do powiadomien")
                elif user_message == "stop":
                    subcsribers.discard(sender_id)
                    send_message(sender_idm, "nie bedziesz wiecej otrzymwyac powiadomien")
    return "OK", 200

def get_user_id():
    url = "https://graph.facebook.com/v12.0/me"
    params = {
        "access_token": config.get("access_token")
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        user_data = response.json()
        print(user_data.get("id"))
    else:
        print(f"Błąd pobierania ID użytkownika: {response.status_code} - {response.text}")
        return None

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

                    previous_ads.add(ad_link)
                    if not first_run:
                        mess = ""
                        #send_mess_via_messenger(mess)

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
        time.sleep(350)


if __name__ == "__main__":
    from threading
    app.run(port=5000, debug=True)
    main()

