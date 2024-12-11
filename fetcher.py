import requests
import pandas as pd
import json
import os
import matplotlib.pyplot as plt

'''Autoreporter-palvelun tilastotietoja
Kyberturvallisuuskeskuksen Autoreporter -palvelusta saadut tiedot haittaohjelma- ja tietoturvaloukkaushavainnoista suomalaisissa verkoissa. Tilastotiedot on julkaistu JSON-muodossa.

Tässä ohjelmassa voit:
1) Ladata uusimmat tiedot API:sta ja tallentaa ne JSON-tiedostoon.
2) Käyttää olemassa olevaa JSON-tiedostoa ja piirtää havainnot pylväsdiagrammina.

Ohjelma muodostaa DataFrame:n JSON-tiedostosta, laskee päivittäiset havainnot pääluokittain ja visualisoi tulokset pylväsdiagrammina.
'''

API_URL = "https://opendata.traficom.fi/api/v13/Autoreporter"
JSON_FILE_PATH = "latest_autoreporter_data.json"

def fetch_latest_data(max_queries=100, page_size=100):
    all_data = []
    last_id = None  # Aloitetaan ilman ID-suodatinta
    seen_ids = set()  # Tallennetaan jo käsitellyt ID:t

    for i in range(max_queries):
        # Parametrit
        params = {
            "$top": page_size,
            "$orderby": "ID desc"  # Järjestetään alussa ID:n mukaan laskevasti
        }

        # Lisää suodatin seuraaviin kyselyihin
        if last_id:
            params["$filter"] = f"ID lt {last_id}"

        try:
            # Tee GET-pyyntö API:lle
            response = requests.get(API_URL, params=params)

            if response.status_code == 200:
                data = response.json().get('value', [])
                if not data:
                    print("Ei lisää dataa haettavana.")
                    break

                # Poistetaan duplikaatit
                new_data = [item for item in data if item['ID'] not in seen_ids]
                seen_ids.update(item['ID'] for item in new_data)

                all_data.extend(new_data)
                last_id = data[-1]['ID']  # Päivitetään viimeisin ID seuraavaa kyselyä varten
            else:
                print(f"Virhe haussa: {response.status_code} - {response.text}")
                break
        except requests.exceptions.RequestException as e:
            print(f"Virhe yhteydessä API:in: {e}")
            break

    # Tallennetaan data JSON-tiedostoon
    if all_data:
        with open(JSON_FILE_PATH, "w") as f:
            json.dump(all_data, f, indent=4)
        print(f"Data tallennettu tiedostoon: {JSON_FILE_PATH}")
    else:
        print("Ei dataa tallennettavaksi.")

    return all_data

def plot_data_from_json(file_path):
    # Ladataan JSON-tiedosto
    if not os.path.exists(file_path):
        print(f"Tiedostoa {file_path} ei löydy.")
        return

    with open(file_path, "r") as f:
        data = json.load(f)

    if not data:
        print("JSON-tiedosto on tyhjä.")
        return

    # Muodostetaan DataFrame datasta
    df = pd.DataFrame(data)

    # Tarkistetaan, onko tiedoissa tarvittavat sarakkeet
    if 'DateFrom' not in df or 'MainCategory' not in df:
        print("JSON-tiedostosta puuttuu tarvittavia sarakkeita.")
        return

    # Muutetaan DateFrom-päivämäärät datetime-muotoon
    df['DateFrom'] = pd.to_datetime(df['DateFrom'], errors='coerce')

    # Poistetaan rivit, joissa DateFrom ei ole kelvollinen
    df = df.dropna(subset=['DateFrom'])

    # Lisätään päivämäärä (ilman aikaa) sarakkeena
    df['Date'] = df['DateFrom'].dt.date

    # Lasketaan kokonaismäärät päivittäin
    total_per_day = df['Date'].value_counts().sort_index()
    print("\nHavaintojen kokonaismäärä per päivä:")
    for date, count in total_per_day.items():
        print(f"{date}: {count}")

    # Ryhmitellään data päivittäin ja pääluokan mukaan
    grouped = df.groupby(['Date', 'MainCategory']).size().reset_index(name='Count')

    # Pivot-taulukko, jotta jokainen pääluokka saa oman sarakkeen
    pivot_table = grouped.pivot(index='Date', columns='MainCategory', values='Count').fillna(0)

    # Piirretään diagrammi
    pivot_table.plot(kind='bar', stacked=True, figsize=(12, 6))
    plt.title('Havaintojen jakauma päivittäin pääluokittain')
    plt.xlabel('Päivämäärä')
    plt.ylabel('Havaintojen lukumäärä')
    plt.legend(title='Pääluokka')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Tarkastetaan, onko JSON-tiedosto olemassa
    file_exists = os.path.exists(JSON_FILE_PATH)

    print("Autoreporter Data Analysis\n")
    if file_exists:
        print("latest_autoreporter_data.json -tiedosto löytyy.")
        print("[1] Lataa uusi data API:sta ja ylikirjoita tiedosto")
        print("[2] Käytä olemassa olevaa dataa tulosten piirtämiseen")
    else:
        print("latest_autoreporter_data.json -tiedostoa ei löydy.")
        print("[1] Lataa uusi data API:sta")
        print("[2] Lopeta")

    choice = input("Valitse toiminto (1 tai 2): ")

    if choice == "1":
        # Haetaan uusin data ja tallennetaan
        fetch_latest_data()
        # Plotataan uusi data, jos lataus onnistui
        if os.path.exists(JSON_FILE_PATH):
            plot_data_from_json(JSON_FILE_PATH)
    elif choice == "2":
        if file_exists:
            # Yritetään piirtää jo olemassa oleva data
            plot_data_from_json(JSON_FILE_PATH)
        else:
            print("Ohjelma päättyy.")
    else:
        print("Virheellinen valinta. Ohjelma päättyy.")
2