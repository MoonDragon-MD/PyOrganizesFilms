import os
import shutil
import requests
from tinytag import TinyTag, TinyTagException
from mutagen import easyid3, mp4, id3
from bs4 import BeautifulSoup
import re
import html  
from html import escape as escape_html
import subprocess

# Script PyOrganizzaFilm by MoonDragon v.1.0
# Gennaio 2025 - revisione n29

# Dipendenze
# sudo apt-get install mkvtoolnix ffmpeg
# pip install requests tinytag mutagen beautifulsoup4

# Variabile per abilitare/disabilitare il debug
DEBUG = False  # Cambia a True/False
# avviare server con ./kiwix-serve '/percorso/cartella/FILE.zim' -p 5000
KIWIX_API_URL = 'http://localhost:5000/search'
KIWIX_VIEWER_URL = 'http://localhost:5000'
# scaricare gli zim da https://download.kiwix.org/zim/  USARE SOLO ITALIANO (wikipedia_it*) se si vuole inglese usare PyOrganizesFilms.py
KIWIX_FILE = 'wikipedia_it_all_maxi_2024-03' #Cambiare in base al vostro file impostato sul server
CARTELLA_FILM = 'Percoso/dei/tuoi/film' #Cambiare in base alla vostra cartella contenente i film
# Genera i print debug se abilitati
def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")
# Pulisci il titolo da cose inutili	, in caso aggiungi quelli che vuoi per migliorare la ricerca su wiki
def clean_title(title):
    unwanted_words = ["1440p", "1080p", "720p", "576p", "480p", "360p", "VP8", "VP9", "AV1", "MPEG-4", "HEVC", "ProRes", "x264", "h264", "x265", "h265"] 
    for word in unwanted_words:
        title = title.replace(word, "")
    return title.strip()
# Funzione per ottenere i metadati dai file video e audio
def get_metadata(file_path, use_tags=True):
    if use_tags:
        title, year = get_metadata_from_file(file_path)
        if title and year:
            return title, year
    
    return get_metadata_from_title(file_path)
# Funzione per leggere i metadati audio/video usando TinyTag
def get_metadata_from_file(file_path):
    debug_print(f"DEBUG: Ottenere metadati per {file_path}")
    try:
        tag = TinyTag.get(file_path)
        debug_print(f"DEBUG: Metadati ottenuti da TinyTag: {tag}")
        return tag.title, tag.year
    except TinyTagException as e:
        debug_print(f"DEBUG: Errore TinyTagException per {file_path}: {e}")
        return None, None
# Funzione che usa ffprobe per leggere i metadati da file non gestiti da TinyTag
def get_metadata_from_video(file_path, ask_for_fallback=True):
    debug_print(f"DEBUG: Ottenere metadati da {file_path}")

    # Assumiamo che file_path sia il percorso dell'HTML di Wikipedia
    if not os.path.exists(file_path):
        debug_print(f"DEBUG: Il file {file_path} non esiste.")
        return None, None

    try:
        # Leggi il contenuto HTML del file offline
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Usa BeautifulSoup per fare il parsing dell'HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Estrazione del titolo del film
        title_tag = soup.find('h1', {'class': 'firstHeading'})
        title = title_tag.text.strip() if title_tag else None
        debug_print(f"DEBUG: Titolo estratto: {title}")

        # Estrazione dell'anno dal sinottico (infobox)
        year = None
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and 'Anno' in header.text:
                    year_cell = row.find('td')
                    if year_cell:
                        year = year_cell.text.strip().split()[0]  # Estrarre solo l'anno (es. 2020)
                        debug_print(f"DEBUG: Anno estratto: {year}")
                        break  # Trova il primo anno

        # Se l'anno non è stato trovato nel sinottico, possiamo fare altre ricerche
        if not year:
            debug_print("DEBUG: Anno non trovato nel sinottico, tentando altre fonti...")

            # Prova a cercare nell'HTML in modo più generico
            # Ad esempio, cercando l'anno nel testo che appare dopo 'Anno'
            text_content = soup.get_text()
            year_candidates = re.findall(r'\b\d{4}\b', text_content)  # Cerca tutti i numeri di 4 cifre
            if year_candidates:
                year = year_candidates[0]
                debug_print(f"DEBUG: Anno trovato nel testo: {year}")
            else:
                debug_print("DEBUG: Anno non trovato nel testo.")

        return title, year

    except Exception as e:
        debug_print(f"DEBUG: Errore durante il parsing dell'HTML: {e}")
        return None, None
# Funzione principale che decide come leggere i metadati
def get_full_metadata(file_path, use_tags=True):
    if file_path.endswith(('.mp4', '.m4v', '.mov')):  # Per i file video supportati da Mutagen
        return get_metadata_from_file(file_path)
    
    if file_path.endswith(('.avi', '.mkv')):  # Per file video che non sono gestiti direttamente da TinyTag
        return get_metadata_from_video(file_path)
    
    return get_metadata_from_title(file_path)  # Se non sono file video, usa il nome del file
# serve se ho una coppia di quattro numeri	
def ask_for_year(years, file_name):
    print(f"Hai trovato i seguenti anni possibili nel file: {', '.join(years)} nel file: {file_name}.")
    for year in years:
        response = input(f"È l'anno del film? (si/no) per l'anno {year}: ").strip().lower()
        if response == 'si':
            return year
    return None
# Estrai metadati dal nome del file
def get_metadata_from_title(file_path):
    debug_print(f"DEBUG: Utilizzo del nome del file per ottenere i metadati")
    base_name = os.path.basename(file_path)
    base_name = os.path.splitext(base_name)[0]
    base_name = base_name.replace('.', ' ')
    base_name = base_name.replace(',', ' ')
    base_name = base_name.replace(';', ' ')
    base_name = base_name.replace('_', ' ')
    base_name = base_name.replace('(', ' ')
    base_name = base_name.replace(')', ' ')	
    base_name = base_name.replace('[', ' ')
    base_name = base_name.replace(']', ' ')	
    base_name = base_name.replace('{', ' ')
    base_name = base_name.replace('}', ' ')	
    # Cerca l'anno nel formato "-2021" o "- 2021"
    year_match = re.search(r'-\s*(\d{4})\b', base_name)
    year = None
    if year_match:
        year = year_match.group(1)
        base_name = re.sub(r'-\s*\d{4}\b', '', base_name).strip()
    else:
        # Cerca un numero di quattro cifre che non è preceduto da un trattino
        year_matches = re.findall(r'\b(\d{4})\b', base_name)
        year = None
        if year_matches:
            year = ask_for_year(year_matches, base_name)
            if year:
                base_name = re.sub(r'\b\d{4}\b', '', base_name).strip()
    
    parts = base_name.split('-')
    title_parts = [part for part in parts if not (part.isdigit() and len(part) == 4)]
    title = ' '.join(title_parts).strip()

    return title, year

def search_article(search_title, year=None):
    # Costruisci l'URL della richiesta
    response = requests.get(f'{KIWIX_API_URL}?books.name={KIWIX_FILE}&pattern={search_title}')
    # Controlla se la richiesta ha avuto successo
    if response.status_code != 200:
        debug_print(f"DEBUG: Errore nella richiesta. Stato: {response.status_code}")
        return []
    # Effettua il parsing della risposta HTML
    soup = BeautifulSoup(response.content.decode('utf-8', errors='ignore'), 'html.parser')
    results_div = soup.find('div', class_='results')
    if not results_div:
        debug_print("DEBUG: Nessun risultato trovato.")
        return []
    # Trova tutti gli elementi <li> che rappresentano articoli di ricerca
    results = results_div.find_all('li')
    articles = []

    for result in results:
        link = result.find('a')
        if link:
            title = link.text.strip()
            href = link['href']
            full_article_url = f"{KIWIX_VIEWER_URL}{href}"
            debug_print(f"DEBUG: URL completo dell'articolo: {full_article_url}")

            # verifica corrispondenza anno tra file e wiki
            found_year = None  # Assicurati di definire found_year
            # Logica per estrarre found_year dall'articolo se necessario

            if year and found_year and year != found_year:
                response = input(f"L'anno trovato su Wikipedia è {found_year}. È corretto? (si/no): ").strip().lower()
                if response == 'si':
                    year = found_year  # Usa l'anno di Wikipedia
                    debug_print(f"Utilizzo l'anno trovato su Wikipedia: {year}")
                else:
                    debug_print("Cerco un altro anno.")
                    continue  # Passa al prossimo articolo

            # Controlla se il titolo contiene "(film)"
            if "(film" in title.lower():
                articles.append(href)
                break    # Trova il primo risultato corretto e interrompi
            # Se non contiene "(film)", verifica il sinottico
            article_response = requests.get(full_article_url)
            debug_print(f"DEBUG: URL della richiesta: {full_article_url}")
            if article_response.status_code == 200:
                debug_print(f"DEBUG: Richiesta andata a buon fine per {href}")
                article_content = article_response.content.decode('utf-8', errors='ignore')
                article_soup = BeautifulSoup(article_content, 'html.parser')
                infobox = article_soup.find('table', {'class': 'sinottico'})

                if infobox:
                    debug_print(f"DEBUG: Infobox trovato per {href}")
                    has_director = any('Regia' in th.text for th in infobox.find_all('th'))
                    if has_director:
                        articles.append(href)
                        debug_print(f"DEBUG: Trovato articolo valido: {href}")
                        break
                    else:
                        debug_print(f"DEBUG: Infobox trovato ma 'Regia' non presente in {href}")
                else:
                    debug_print(f"DEBUG: Infobox non trovato per {href}")
            else:
                debug_print(f"DEBUG: Errore nella richiesta per {href}. Stato: {article_response.status_code}, Risposta: {article_response.text}")
    # Se non ci sono articoli trovati, restituisci un elenco vuoto
    if not articles:
        debug_print("DEBUG: Nessun articolo valido trovato.")

    return articles

def get_full_metadata(file_path, use_tags):
    title, year = get_metadata(file_path, use_tags)
    title = clean_title(title)
    debug_print(f"DEBUG: Titolo: {title}, Anno: {year}")

    articles = search_article(title, year)  # Passa year qui
    if not articles:
        articles = search_article(f"{title} (film", year)  # E qui

    genres = ['Genere sconosciuto']
    plot = 'Nessun riassunto disponibile'
    director = 'Regista sconosciuto'
    actors = 'Attori sconosciuti'
    cover_url = None
    article_url = None
    full_article_url = None
	
    if articles:
        debug_print(f"DEBUG: Articoli trovati: {articles}")
        article_url = articles[0]
        full_article_url = f'file:///content/{article_url}'
        article_response = requests.get(f'{KIWIX_VIEWER_URL}{article_url}')
        if article_response.status_code == 200:
            article_content = article_response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(article_content, 'html.parser')

            # Estrazione della trama
            plot_section = soup.find('h2', string=re.compile("Trama", re.IGNORECASE))
            if plot_section:
                # Trova il paragrafo sottostante alla sezione "Trama"
                plot_paragraph = plot_section.find_next('p')
                if plot_paragraph:
                    plot = plot_paragraph.text.strip()
                    plot_words = plot.split()[:300]  # Limita a 300 parole
                    plot = ' '.join(plot_words)
                    # Prendi le prime tre frasi
                    sentences = plot.split('.')
                    plot = '. '.join(sentences[:3]) + '.' if len(sentences) > 2 else plot

            infobox = soup.find('table', {'class': 'sinottico'})
            if infobox:
                rows = infobox.find_all('tr')
                genres = []
                for row in rows:
                    header = row.find('th')
                    data = row.find('td')
                    if header and data:
                        if 'Genere' in header.text:
                            raw_genres = data.text
                            raw_genres = re.sub(r'\[.*?\]', '', raw_genres)  # Rimuovi il testo tra parentesi quadre
                            genres = [genre.strip() for genre in raw_genres.split(',')]
                        elif 'Anno' in header.text:
                            year = data.text
                        elif 'Regia' in header.text:
                            director = data.text
                        elif 'Interpreti' in header.text:
                            actors = data.text

                # Estrai attori dalla sezione <td colspan="2">
                actors_list = None  # Inizializza actors_list
                cast_section = infobox.find_next('tr', class_='sinottico_divisione')
                if cast_section:
                    actors_list = cast_section.find_next('td')

                if actors_list:
                    actors = ', '.join([li.text for li in actors_list.find_all('li')])
                else:
                    debug_print(f"DEBUG: Nessun elenco di attori trovato per {article_url}")

                debug_print(f"DEBUG: Informazioni estratte: Generi: {genres}, Anno: {year}, Trama: {plot}, Regista: {director}, Attori: {actors}, Cover URL: {cover_url}, Full Article URL: {full_article_url}")

    return {
        'title': title,
        'year': year,
        'genres': genres,
        'plot': plot,
        'director': director,
        'actors': actors,
        'cover_url': cover_url,
        'article_url': article_url,
        'full_article_url': full_article_url
    }
# Estrai solo anno da wiki per funzione alternativa a lettura tag da file
def extract_year_from_article(article_url):
    try:
        # Richiedi il contenuto dell'articolo
        article_response = requests.get(f'{KIWIX_VIEWER_URL}{article_url}')
        if article_response.status_code == 200:
            article_content = article_response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(article_content, 'html.parser')

            # Cerca l'anno nel contenuto dell'articolo
            # Supponiamo che l'anno sia scritto nel formato yyyy in alcune sezioni specifiche
            year_match = re.search(r'(\d{4})', article_content)
            if year_match:
                year = year_match.group(1)
                debug_print(f"DEBUG: Anno estratto dall'articolo: {year}")
                return year
            else:
                debug_print("DEBUG: Anno non trovato nell'articolo.")
                return None
        else:
            debug_print(f"DEBUG: Errore nella richiesta dell'articolo. Stato: {article_response.status_code}")
            return None
    except Exception as e:
        debug_print(f"DEBUG: Errore nell'estrazione dell'anno dall'articolo: {e}")
        return None
# Scrivi i tag nei file sistemati
def write_tags(file_path, title, year, genres):
    try:
        if file_path.endswith(('.mp4', '.m4v', '.mov')): 
            if file_path.endswith(('.mp4', '.m4v')):  # Per mp4 e m4v, utilizza Mutagen
                audio = MP4(file_path)
                tags = audio.tags
                if tags is None:
                    tags = MP4Tags()
                    audio.tags = tags
                tags["\xa9nam"] = title  # Titolo
                tags["\xa9day"] = year   # Anno pubblicazione
                tags["\xa9gen"] = ', '.join(genres)  # Genere
                audio.save()
            else:
                # Per .mov utilizziamo ffmpeg 
                cmd = [
                    'ffmpeg', '-i', file_path, '-metadata',
                    f'title={title}', '-metadata', f'year={year}',
                    '-metadata', f'genre={",".join(genres)}',
                    '-codec', 'copy', 'temp_' + file_path
                ]
                subprocess.run(cmd, check=True)  # Esegui il comando ffmpeg con check=True
                
                # Rinominare il file temporaneo
                subprocess.run(['mv', f'temp_{file_path}', file_path], check=True)
            
            debug_print(f"DEBUG: Tag scritti per {file_path}")
        elif file_path.endswith('.mkv'):
            # Imposta solo il titolo per i file .mkv
            cmd = [
                'mkvpropedit', file_path,
                '--set', f'title={title}'
            ]
            subprocess.run(cmd, check=True)  # Esegui il comando mkvpropedit con check=True
            debug_print(f"DEBUG: Tag scritti per {file_path}")
    except subprocess.CalledProcessError as e:
        debug_print(f"DEBUG: Errore durante l'esecuzione del comando subprocess per {file_path}: {e}")
    except Exception as e:
        debug_print(f"DEBUG: Errore sconosciuto durante la scrittura dei tag per {file_path}: {e}")

# evita di avere due nomi uguali		
def get_unique_file_name(directory, base_name, extension):
    base_name = sanitize_filename(base_name)  # Pulisci il nome base
    counter = 1
    new_name = f"{base_name}.{extension}"
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base_name} - Doppione {counter}.{extension}"
        counter += 1
    return new_name
# ulteriore pulizia nome
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()
# Funzione per chiedere come organizzare i film
def chiedi_organizzazione():
    print("Come vuoi organizzare i tuoi film?")
    print("a) Suddividi per genere")
    print("b) Suddividi per decadi")
    print("c) Suddividi per genere con sottosezioni decadi")
    scelta = input("Inserisci la tua scelta (a/b/c): ").strip().lower()
    while scelta not in ['a', 'b', 'c']:
        scelta = input("Scelta non valida. Inserisci la tua scelta (a/b/c): ").strip().lower()
    return scelta
# Funzione per ottenere il decennio da un anno
def get_decade(year):
    if year:
        year = str(year).strip()  # Converte l'anno in stringa e rimuove eventuali spazi bianchi
        if year.isdigit():  # Verifica se la stringa è composta solo da cifre
            return f"{year[:3]}0s"
    return None
# Funzione per organizzare i file in base alla scelta
def organize_files(files_metadata, action, scelta):
    new_file_names = {}
    for file_path, metadata in files_metadata.items():
        genre = metadata['genres'][0] if metadata['genres'] else 'Misti'
        decade = get_decade(metadata['year'])

        if scelta == 'a':
            new_folder = os.path.join('Films_Organizzati', genre)
        elif scelta == 'b':
            if decade:
                new_folder = os.path.join('Films_Organizzati', decade)
            else:
                new_folder = os.path.join('Films_Organizzati', genre)
        elif scelta == 'c':
            if decade:
                new_folder = os.path.join('Films_Organizzati', genre, decade)
            else:
                new_folder = os.path.join('Films_Organizzati', genre)

        os.makedirs(new_folder, exist_ok=True)

        new_file_name = clean_title(f"{metadata['title']}").strip().replace('\n', '').replace('\r', '')

        if metadata['year'] and metadata['year'] not in new_file_name:
            new_file_name += f" - {metadata['year']}"

        extension = file_path.split('.')[-1]
        new_file_name = get_unique_file_name(new_folder, new_file_name, extension)
        new_file_path = os.path.join(new_folder, new_file_name)

        try:
            if action == 'copiare':
                shutil.copy(file_path, new_file_path)
            elif action == 'spostare':
                shutil.move(file_path, new_file_path)

            write_tags(new_file_path, metadata['title'], metadata['year'], metadata['genres'])
            
            new_file_names[file_path] = new_file_name
        except Exception as e:
            print(f"Errore durante l'{action} di {file_path} in {new_file_path}: {e}")

    return new_file_names
# Crea la pagina htm per infomazioni e cercare i film
def create_html_page(files_metadata, new_file_names):
    debug_print(f"DEBUG: Creazione della pagina HTML con i metadati dei file")
    with open('PyOrganizzaFilm.html', 'w', encoding='utf-8') as f:
        f.write('<html><body>')
        f.write('<h1><a href="https://github.com/MoonDragon-MD/PyOrganizzaFilm">PyOrganizzaFilm</a></h1>')
        f.write('<input type="text" id="searchInput" onkeyup="searchMovies()" placeholder="Cerca film..">')
        f.write('<ul id="movieList">')

        for file_path, metadata in files_metadata.items():
            genre = metadata['genres'][0] if metadata['genres'] else 'Misti'
            new_file_name = new_file_names.get(file_path)
            if new_file_name is None:
                debug_print(f"DEBUG: Attenzione! Nuovo nome non trovato per {file_path}")
                continue

            # Gestisci l'anno
            year = metadata.get("year")
            if not year:
                debug_print(f"DEBUG: Anno non trovato per {file_path}")
                year = "Anno sconosciuto"  # Gestione dell'anno mancante

            file_link = os.path.join('Films_Organizzati', genre, new_file_name)
            file_title = metadata["title"]
            if year not in file_title:  # Aggiungi l'anno al titolo, se non presente
                file_title = f"{file_title} - {year}"
				
            # Definisci l'URL di Wikipedia
            if metadata['full_article_url']:
                full_article_url = metadata['full_article_url'].replace('file:///', '').replace('content/', '')
                wiki_url = f"http://localhost:5000/viewer#{full_article_url.replace('#/', '#')}"
                if wiki_url.startswith('http://localhost:5000/viewer#/'):
                    wiki_url = wiki_url.replace('http://localhost:5000/viewer#/', 'http://localhost:5000/viewer#')
            else:
                wiki_url = '#'

            debug_print(f"DEBUG: url wiki film: (wiki_url) ")

            f.write(f'<li class="file-item"><strong><a href="{file_link}" class="fileLink">{escape_html(file_title)}</a></strong>')
            f.write(f'<button class="copy-button" onclick="copyFolderPath(\'{file_link}\')">VLC</button></li>')
            # f.write(f'Anno: {year}<br>')  # L'anno è già nel titolo
            f.write(f'<a href="{wiki_url}">Wikipedia</a><br>')  # link a Wikipedia offline
            f.write(f'Regista: {escape_html(metadata["director"])}<br>')
            f.write(f'Attori: {escape_html(metadata["actors"])}<br>')
            if metadata['cover_url']:
                f.write(f'<img src="{metadata["cover_url"]}" alt="Copertina del film"><br>')
            f.write(f'<p>{escape_html(metadata["plot"])}</p></li>')

        f.write('''
        <script>
        function searchMovies() {
            var input, filter, ul, li, a, i, txtValue;
            input = document.getElementById('searchInput');
            filter = input.value.toUpperCase();
            ul = document.getElementById("movieList");
            li = ul.getElementsByTagName('li');
            for (i = 0; i < li.length; i++) {
                txtValue = li[i].textContent || li[i].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    li[i].style.display = "";
                } else {
                    li[i].style.display = "none";
                }
            }
        }
        </script>
        <script>
            function copyFolderPath(fileLink) {
                // Ottieni l'intero URL della pagina dal browser
                let pageUrl = window.location.href;
                // Decodifica l'URL
                pageUrl = decodeURIComponent(pageUrl);
                // Rimuovi 'file://' dall'URL
                pageUrl = pageUrl.replace('file://', '');
                // Rimuovi 'PyOrganizzaFilm.html' dall'URL
                pageUrl = pageUrl.replace('PyOrganizzaFilm.html', '');
                // Concatenare il fileLink al percorso ottenuto
                let folderPath = pageUrl + fileLink;
                // Copia il percorso negli appunti
                navigator.clipboard.writeText(folderPath).then(function() {
                    alert('vlc ' + folderPath);
                }).catch(function(err) {
                    console.error('Errore nella copia negli appunti: ', err);
                });
            }
        </script>
        ''')
        f.write('</body></html>')

if __name__ == '__main__':
    debug_print("DEBUG: Inizio script")
    print("#########################################")
    print("####  PyOrganizzaFilm by MoonDragon  ####")
    print("####       v.1.0 Revisione n29       ####")    
    print("#########################################")
    debug_print("DEBUG: Inizio script")
    file_types = ['*.mp4', '*.m4v', '*.avi', '*.mkv', '*.mov']
    files = []
    for dirpath, _, filenames in os.walk(CARTELLA_FILM):
        for file in filenames:
            if any(file.endswith(ext) for ext in ['.mp4', '.m4v', '.avi', '.mkv', '.mov']):
                files.append(os.path.join(dirpath, file))

    debug_print(f"DEBUG: Trovati {len(files)} file")
    use_tags = input("Vuoi leggere i tag dai file (nota: potrebbero essere scritti male)? (si/no): ").strip().lower() == 'si'
    files_metadata = {}
    for file_path in files:
        metadata = get_full_metadata(file_path, use_tags)
        files_metadata[file_path] = metadata

    action = input("Vuoi spostare o copiare i file? (spostare/copiare): ").strip().lower()
    while action not in ['spostare', 'copiare']:
        action = input("Input non valido. Vuoi spostare o copiare i file? (spostare/copiare): ").strip().lower()
    
    scelta = chiedi_organizzazione()
    new_file_names = organize_files(files_metadata, action, scelta)
    create_html_page(files_metadata, new_file_names)
    debug_print("DEBUG: Fine script")