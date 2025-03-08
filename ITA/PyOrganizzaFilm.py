# Script PyOrganizzaFilm by MoonDragon v.2.0
# Marzo 2025 - revisione n11

# Dipendenze richieste
# sudo apt-get install mkvtoolnix ffmpeg
# pip install requests tinytag mutagen beautifulsoup4 unidecode

import os
import shutil
import requests
import subprocess
from tinytag import TinyTag, TinyTagException
from mutagen.mp4 import MP4, MP4Tags
from bs4 import BeautifulSoup
import re
import html
from html import escape as escape_html
from unidecode import unidecode #Per aumentare la tolleranza di ricerca nel wiky
import tempfile # Per creare un XML temporaneo per i tag nei file mkv

# Variabili globali
DEBUG = False  # Cambia a True per debug
KIWIX_API_URL = 'http://localhost:5000/search'
KIWIX_VIEWER_URL = 'http://localhost:5000'
KIWIX_FILE = 'wikipedia_it_all_maxi_2024-03'  # Modifica in base al tuo file ZIM
CARTELLA_FILM = 'Percoso/dei/tuoi/film'  # Modifica con il percorso della tua cartella film

# Funzione di debug
def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

# Pulizia del titolo
def clean_title(title):
    unwanted_words = ["1440p", "1080p", "720p", "576p", "480p", "360p", "VP8", "VP9", "AV1", "MPEG-4", "HEVC", "ProRes", "x264", "h264", "x265", "h265"]
    for word in unwanted_words:
        pattern = r'\b' + re.escape(word) + r'\b'
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    # Sostituisci sequenze di trattini con un singolo trattino
    title = re.sub(r'-+', '-', title)
    # Sostituisci sequenze di spazi con un singolo spazio
    title = re.sub(r'\s+', ' ', title)
    # Rimuovi spazi prima e dopo i trattini
    title = re.sub(r'\s*-\s*', '-', title)
    # Rimuovi spazi iniziali e finali
    title = title.strip()
    return title

# Ottieni metadati dai file
def get_metadata(file_path, use_tags=True):
    if use_tags:
        title, year = get_metadata_from_file(file_path)
        if title and year:
            return title, year
    return get_metadata_from_title(file_path)

# Funzione per normalizzare i titoli   
def normalize_title(title):
    # Rimuove accenti e caratteri speciali (es. "ö" → "o")
    title = unidecode(title)
    # Rimuove punteggiatura (es. apostrofi, due punti, trattini)
    title = re.sub(r'[^\w\s]', '', title)
    # Converte in minuscolo e rimuove spazi extra
    return title.lower().strip()

# Leggi metadati con TinyTag (solo per formati limitati)
def get_metadata_from_file(file_path):
    debug_print(f"Ottenere metadati per {file_path}")
    try:
        tag = TinyTag.get(file_path)
        debug_print(f"Metadati ottenuti da TinyTag: {tag}")
        return tag.title, tag.year
    except TinyTagException:
        debug_print(f"Errore TinyTagException per {file_path}")
        return None, None
    except Exception as e:
        debug_print(f"Errore inatteso per {file_path}: {e}")
        return None, None

# Estrai metadati dal nome del file
def get_metadata_from_title(file_path):
    base_name = os.path.basename(file_path)
    base_name = os.path.splitext(base_name)[0]
    base_name = base_name.replace('.', ' ').replace(',', ' ').replace(';', ' ').replace('_', ' ').replace('(', ' ').replace(')', ' ').replace('[', ' ').replace(']', ' ')
    year_matches = re.findall(r'\b\d{4}\b', base_name)

    if len(year_matches) == 1:
        year = year_matches[0]
        base_name = re.sub(r'\b\d{4}\b', '', base_name).strip()
    elif len(year_matches) > 1:
        print(f"Trovati più anni nel file: {', '.join(year_matches)} per [ {os.path.basename(file_path)} ]")
        year = ask_for_year(year_matches, os.path.basename(file_path))
        if year:
            base_name = re.sub(r'\b' + year + r'\b', '', base_name).strip()
        else:
            year = None
    else:
        year = None

    title = base_name.strip()
    return title, year

# Chiedi all'utente di scegliere l'anno
def ask_for_year(years, file_name):
    while True:
        for year in years:
            response = input(f"È '{year}' l'anno del film '{file_name}'? (si/no o s/n): ").strip().lower()
            if response in ['s', 'si']:  # Accetta "s" o "si"
                return year
            elif response in ['n', 'no']:  # Accetta "n" o "no"
                continue # Passa al prossimo anno
            else:
                print("Risposta non valida. Inserisci 's' o 'n'.") # Gestisce risposte errate
        print("Nessun anno selezionato.") # Solo se tutti gli anni sono stati rifiutati
        skip = input("Vuoi saltare la scelta dell'anno? (si/no o s/n): ").strip().lower()
        if skip in ['s', 'si']:  # Accetta "s" o "si" - salta la scelta dell'anno
            return None
        else:
            print("Riprova a selezionare un anno.") # Torna a proporre gli anni

# Gestione avanzata della ricerca di nuovi articoli su Kiwix
def search_article(search_title, year=None):
    # Normalizza il titolo del file
    normalized_search_title = normalize_title(search_title)
    
    # Crea un pattern di ricerca base
    pattern = f"{search_title} (film)"
    response = requests.get(f'{KIWIX_API_URL}?books.name={KIWIX_FILE}&pattern={pattern}')
    
    if response.status_code != 200:
        print(f"Errore nella richiesta. Stato: {response.status_code}")
        return []
    
    # Parsa i risultati
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    results_div = soup.find('div', class_='results')
    if not results_div:
        print("Nessun risultato trovato.")
        return []
    
    results = results_div.find_all('li')
    articles = []

    for result in results:
        link = result.find('a')
        if link:
            title = link.text.strip()
            href = link['href']
            # Normalizza il titolo dell’articolo
            normalized_article_title = normalize_title(title)
            
            # Verifica se il titolo normalizzato del file è contenuto in quello dell’articolo
            if normalized_search_title in normalized_article_title:
                full_article_url = f"{KIWIX_VIEWER_URL}{href}"
                # Controlla se è un film
                if "(film" in normalized_article_title or "film" in normalized_article_title:
                    articles.append(href)
                    continue
                
                # Verifica aggiuntiva tramite infobox (opzionale)
                article_response = requests.get(full_article_url)
                if article_response.status_code == 200:
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    infobox = article_soup.find('table', {'class': 'sinottico'})
                    if infobox and any('Regia' in th.text.lower() for th in infobox.find_all('th')):
                        articles.append(href)
    
    # Filtro opzionale per anno
    if year:
        articles = [article for article in articles if str(year) in article]
    
    return articles

# Gestione ricerca articoli successivi
def handle_new_article_search(title, file_name, year_from_file=None, previous_articles=None):
    if previous_articles is None:
        previous_articles = []

    # Ricerca senza anno per ampliare i risultati
    all_articles = search_article(title)  # Non passare year

    new_articles = [article for article in all_articles if article not in previous_articles]

    if not new_articles:
        print("Nessun altro articolo trovato.")
        if year_from_file:
            print(f"Uso l'anno dal file: {year_from_file}")
            return year_from_file, None  # Restituisce l'anno del file e nessun nuovo articolo
        else:
            return None, None

    # Prendi il prossimo articolo
    next_article = new_articles[0]
    full_article_url = f"{KIWIX_VIEWER_URL}{next_article}"
    
    # Estrai l’anno dal nuovo articolo
    new_year = extract_year_from_article(next_article)
    if new_year:
        print(f"Trovato un nuovo articolo: {full_article_url} con anno {new_year}")
    else:
        print(f"Trovato un nuovo articolo: {full_article_url} (anno non trovato)")

    # Costruisci il menu delle opzioni
    options = "Vuoi: (a) accettarlo, (b) cercare ancora, (c) saltare"
    if year_from_file:
        options += ", (d) tenere l'anno del file"
    options += "? (a/b/c"
    if year_from_file:
        options += "/d"
    options += "): "

    # Ciclo per ottenere una scelta valida
    while True:
        choice = input(options).strip().lower()
        if choice in ['a', 'b', 'c'] or (choice == 'd' and year_from_file):
            break
        print("Scelta non valida. Riprova.")

    # Gestisci la scelta dell’utente
    if choice == 'a':
        return new_year if new_year else None, next_article  # Restituisce l'anno e l'URL del nuovo articolo
    elif choice == 'b':
        previous_articles.append(next_article)
        # Chiamata ricorsiva senza anno
        return handle_new_article_search(title, file_name, year_from_file, previous_articles)
    elif choice == 'c':
        return None, None
    elif choice == 'd' and year_from_file:
        return year_from_file, None  # Restituisce l'anno del file e nessun nuovo articolo

# Estrai l'anno dall'articolo
def extract_year_from_article(article_url):
    try:
        article_response = requests.get(f'{KIWIX_VIEWER_URL}{article_url}')
        if article_response.status_code == 200:
            soup = BeautifulSoup(article_response.content, 'html.parser')
            infobox = soup.find('table', {'class': 'sinottico'})
            if infobox:
                for row in infobox.find_all('tr'):
                    header = row.find('th')
                    if header and 'Anno' in header.text:
                        year_cell = row.find('td')
                        if year_cell:
                            year = re.search(r'\b(\d{4})\b', year_cell.text)
                            if year:
                                return year.group(1)
            text_content = soup.get_text()
            year_match = re.search(r'\b\d{4}\b', text_content)
            if year_match:
                return year_match.group(0)
        return None
    except Exception as e:
        debug_print(f"Errore nell'estrazione dell'anno: {e}")
        return None

# Ottieni metadati completi
def get_full_metadata(file_path, use_tags):
    title, year_from_file = get_metadata(file_path, use_tags)
    title = clean_title(title)
    file_name = os.path.basename(file_path)
    debug_print(f"Titolo iniziale: {title}, Anno iniziale: {year_from_file}")

    # Prima ricerca con anno, se disponibile
    if year_from_file:
        articles = search_article(title, year_from_file)
    else:
        articles = search_article(title)

    # Se non ci sono risultati e c'era un anno, cerca senza anno
    if not articles and year_from_file:
        articles = search_article(title)

    genres = ['Genere sconosciuto']
    plot = 'Nessun riassunto disponibile'
    director = 'Regista sconosciuto'
    actors = 'Attori sconosciuti'
    cover_url = None
    article_url = None
    full_article_url = None
    year = year_from_file

    if articles:
        article_url = articles[0]
        full_article_url = f'{KIWIX_VIEWER_URL}{article_url}'
        article_response = requests.get(full_article_url)
        if article_response.status_code == 200:
            soup = BeautifulSoup(article_response.content, 'html.parser')

            # Estrai la trama
            plot_section = soup.find('h2', string=re.compile("Trama", re.IGNORECASE))
            if plot_section:
                plot_paragraph = plot_section.find_next('p')
                if plot_paragraph:
                    plot = plot_paragraph.text.strip()
                    plot_words = plot.split()[:300]
                    plot = ' '.join(plot_words)
                    sentences = plot.split('.')
                    plot = '. '.join(sentences[:3]) + '.' if len(sentences) > 2 else plot

            # Estrai infobox
            infobox = soup.find('table', {'class': 'sinottico'})
            if infobox:
                for row in infobox.find_all('tr'):
                    header = row.find('th')
                    data = row.find('td')
                    if header and data:
                        header_text = header.text.strip().lower()
                        if 'genere' in header_text:
                            raw_genres = data.text.strip()
                            raw_genres = re.sub(r'\[.*?\]', '', raw_genres)
                            genres = [genre.strip() for genre in raw_genres.split(',')]
                        elif 'regia' in header_text:
                            director = data.text.strip()
                        elif 'interpreti' in header_text or 'attori' in header_text:
                            actors = data.text.strip()

                # Prova a estrarre attori da una sezione alternativa
                if actors == 'Attori sconosciuti':
                    cast_section = infobox.find('tr', class_='sinottico_divisione')
                    if cast_section:
                        next_td = cast_section.find_next('td')
                        if next_td:
                            actors_list = next_td.find_all('li')
                            if actors_list:
                                actors = ', '.join([li.text.strip() for li in actors_list])
                                actors = re.sub(r'\[.*?\]', '', actors)

            # Verifica anno
            year_from_wikipedia = extract_year_from_article(article_url)
            if year_from_file and year_from_wikipedia and year_from_file != year_from_wikipedia:
                print(f"L'anno nel file '{year_from_file}' non corrisponde a quello su Wikipedia '{year_from_wikipedia}' per '{file_name}'.")
                while True:
                    choice = input("Vuoi: (a) tenere l'anno del file, (b) usare l'anno di Wikipedia, (c) cercare un altro articolo, (d) saltare l'anno? (a/b/c/d): ").strip().lower()
                    if choice in ['a', 'b', 'c', 'd']:
                        break
                    print("Scelta non valida. Riprova.")
                if choice == 'a':
                    year = year_from_file
                elif choice == 'b':
                    year = year_from_wikipedia
                elif choice == 'c':
                    new_year, new_article_url = handle_new_article_search(title, file_name, year_from_file)
                    if new_article_url:
                        # Aggiorna tutti i metadati con il nuovo articolo
                        article_url = new_article_url
                        full_article_url = f'{KIWIX_VIEWER_URL}{article_url}'
                        article_response = requests.get(full_article_url)
                        if article_response.status_code == 200:
                            soup = BeautifulSoup(article_response.content, 'html.parser')
                            # Riesegui l'estrazione della trama
                            plot_section = soup.find('h2', string=re.compile("Trama", re.IGNORECASE))
                            if plot_section:
                                plot_paragraph = plot_section.find_next('p')
                                if plot_paragraph:
                                    plot = plot_paragraph.text.strip()
                                    plot_words = plot.split()[:300]
                                    plot = ' '.join(plot_words)
                                    sentences = plot.split('.')
                                    plot = '. '.join(sentences[:3]) + '.' if len(sentences) > 2 else plot
                            # Riesegui l'estrazione dell'infobox
                            infobox = soup.find('table', {'class': 'sinottico'})
                            if infobox:
                                for row in infobox.find_all('tr'):
                                    header = row.find('th')
                                    data = row.find('td')
                                    if header and data:
                                        header_text = header.text.strip().lower()
                                        if 'genere' in header_text:
                                            raw_genres = data.text.strip()
                                            raw_genres = re.sub(r'\[.*?\]', '', raw_genres)
                                            genres = [genre.strip() for genre in raw_genres.split(',')]
                                        elif 'regia' in header_text:
                                            director = data.text.strip()
                                        elif 'interpreti' in header_text or 'attori' in header_text:
                                            actors = data.text.strip()
                                if actors == 'Attori sconosciuti':
                                    cast_section = infobox.find('tr', class_='sinottico_divisione')
                                    if cast_section:
                                        next_td = cast_section.find_next('td')
                                        if next_td:
                                            actors_list = next_td.find_all('li')
                                            if actors_list:
                                                actors = ', '.join([li.text.strip() for li in actors_list])
                                                actors = re.sub(r'\[.*?\]', '', actors)
                            year = new_year if new_year else year_from_file
                    else:
                        year = new_year if new_year else year_from_file
                elif choice == 'd':
                    year = None
            elif not year_from_file and year_from_wikipedia:
                print(f"Nessun anno trovato nel file '{file_name}'. Wikipedia suggerisce l'anno {year_from_wikipedia}.")
                while True:
                    choice = input("Vuoi: (a) accettarlo, (b) cercare un altro articolo, (c) saltare l'anno? (a/b/c): ").strip().lower()
                    if choice in ['a', 'b', 'c']:
                        break
                    print("Scelta non valida. Riprova.")
                if choice == 'a':
                    year = year_from_wikipedia
                elif choice == 'b':
                    new_year, new_article_url = handle_new_article_search(title, file_name, year_from_file)
                    if new_article_url:
                        # Aggiorna tutti i metadati con il nuovo articolo
                        article_url = new_article_url
                        full_article_url = f'{KIWIX_VIEWER_URL}{article_url}'
                        article_response = requests.get(full_article_url)
                        if article_response.status_code == 200:
                            soup = BeautifulSoup(article_response.content, 'html.parser')
                            # Riesegui l'estrazione della trama
                            plot_section = soup.find('h2', string=re.compile("Trama", re.IGNORECASE))
                            if plot_section:
                                plot_paragraph = plot_section.find_next('p')
                                if plot_paragraph:
                                    plot = plot_paragraph.text.strip()
                                    plot_words = plot.split()[:300]
                                    plot = ' '.join(plot_words)
                                    sentences = plot.split('.')
                                    plot = '. '.join(sentences[:3]) + '.' if len(sentences) > 2 else plot
                            # Riesegui l'estrazione dell'infobox
                            infobox = soup.find('table', {'class': 'sinottico'})
                            if infobox:
                                for row in infobox.find_all('tr'):
                                    header = row.find('th')
                                    data = row.find('td')
                                    if header and data:
                                        header_text = header.text.strip().lower()
                                        if 'genere' in header_text:
                                            raw_genres = data.text.strip()
                                            raw_genres = re.sub(r'\[.*?\]', '', raw_genres)
                                            genres = [genre.strip() for genre in raw_genres.split(',')]
                                        elif 'regia' in header_text:
                                            director = data.text.strip()
                                        elif 'interpreti' in header_text or 'attori' in header_text:
                                            actors = data.text.strip()
                                if actors == 'Attori sconosciuti':
                                    cast_section = infobox.find('tr', class_='sinottico_divisione')
                                    if cast_section:
                                        next_td = cast_section.find_next('td')
                                        if next_td:
                                            actors_list = next_td.find_all('li')
                                            if actors_list:
                                                actors = ', '.join([li.text.strip() for li in actors_list])
                                                actors = re.sub(r'\[.*?\]', '', actors)
                            year = new_year if new_year else year_from_wikipedia
                    else:
                        year = new_year if new_year else year_from_wikipedia
                elif choice == 'c':
                    year = None
            else:
                year = year_from_file if year_from_file else year_from_wikipedia
    else:
        year = year_from_file

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

# Scrivi i tag nei file
# Scrivi i tag nei file
def write_tags(file_path, title, year, genres, director=None):
    try:
        if file_path.endswith(('.mp4', '.m4v', '.mov')):
            audio = MP4(file_path)
            tags = audio.tags or MP4Tags()
            audio.tags = tags
            tags["\xa9nam"] = title  # Titolo
            if year:
                tags["\xa9day"] = year  # Anno
            if genres:  # Anche "Genere sconosciuto" va bene
                tags["\xa9gen"] = ', '.join(genres)  # Genere
            if director:
                tags["\xa9ART"] = director  # Artista (regista)
            audio.save()
            debug_print(f"Tag scritti con Mutagen per {file_path}")
        elif file_path.endswith('.mkv'):
            # Imposta il titolo e, se presente, l'anno nel file MKV
            cmd = ['mkvpropedit', file_path, '--edit', 'info', '--set', f'title={title}']
            if year:
                cmd.extend(['--set', f'date={year}-01-01T00:00:00Z'])
            subprocess.run(cmd, check=True)
            
            # Crea un file XML temporaneo per i tag
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as temp_xml:
                temp_xml.write('<Tags>\n')
                # Aggiungi i generi, se presenti
                if genres:
                    for genre in genres:
                        temp_xml.write(
                            f'  <Tag>\n'
                            f'    <Simple>\n'
                            f'      <Name>GENRE</Name>\n'
                            f'      <String>{html.escape(genre)}</String>\n'
                            f'    </Simple>\n'
                            f'  </Tag>\n'
                        )
                # Aggiungi il regista (ARTIST), se presente
                if director:
                    temp_xml.write(
                        f'  <Tag>\n'
                        f'    <Simple>\n'
                        f'      <Name>ARTIST</Name>\n'
                        f'      <String>{html.escape(director)}</String>\n'
                        f'    </Simple>\n'
                        f'  </Tag>\n'
                    )
                temp_xml.write('</Tags>')
                temp_xml_path = temp_xml.name
            
            # Debug: stampa il percorso del file XML temporaneo
            debug_print(f"File XML temporaneo per tag: {temp_xml_path}")
            
            # Esegui mkvpropedit per applicare i tag, catturando l'output
            result = subprocess.run(
                ['mkvpropedit', file_path, '--tags', f'global:{temp_xml_path}'],
                capture_output=True,
                text=True,
                check=True
            )
            debug_print(f"mkvpropedit completato con successo: {result.stdout}")
            
            # Rimuovi il file temporaneo
            os.remove(temp_xml_path)
            debug_print(f"Tag scritti con mkvpropedit per {file_path}")
    except subprocess.CalledProcessError as e:
        debug_print(f"Errore mkvpropedit per {file_path}: {e}")
    except Exception as e:
        debug_print(f"Errore inatteso scrittura tag per {file_path}: {e}")

# Genera nomi file univoci
def get_unique_file_name(directory, base_name, extension):
    # Rimuove i caratteri non validi dal nome del file
    base_name = re.sub(r'[<>:"/\\|?*]', '', base_name).strip()
    
    # Imposta il nome iniziale del file
    counter = 1
    new_name = f"{base_name}.{extension}"
    
    # Verifica se il file esiste già e modifica il nome se necessario
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base_name} - Doppione {counter}.{extension}"
        counter += 1
    
    return new_name

# Chiedi come organizzare i film
def chiedi_organizzazione():
    print("Come vuoi organizzare i tuoi film?")
    print("a) Suddividi per genere")
    print("b) Suddividi per decadi")
    print("c) Suddividi per genere con sottosezioni decadi")
    while True:
        scelta = input("Inserisci la tua scelta (a/b/c): ").strip().lower()
        if scelta in ['a', 'b', 'c']:
            return scelta
        print("Scelta non valida. Riprova.")

# Ottieni il decennio
def get_decade(year):
    if year and str(year).isdigit():
        return f"{year[:3]}0s"
    return None

# Organizza i file
def organize_files(files_metadata, action, scelta):
    new_file_names = {}
    for file_path, metadata in files_metadata.items():
        genre = metadata['genres'][0] if metadata['genres'] else 'Misti'
        decade = get_decade(metadata['year'])
        if scelta == 'a':
            new_folder = os.path.join('Films_Organizzati', genre)
        elif scelta == 'b':
            new_folder = os.path.join('Films_Organizzati', decade if decade else genre)
        elif scelta == 'c':
            new_folder = os.path.join('Films_Organizzati', genre, decade if decade else '')

        os.makedirs(new_folder, exist_ok=True)
        
        # Pulizia del titolo
        cleaned_title = clean_title(metadata['title']).strip()
        cleaned_title = cleaned_title.rstrip('- ').strip()

        # Costruzione del nuovo nome
        if metadata['year']:
            new_file_name = f"{cleaned_title} - {metadata['year']}"
        else:
            new_file_name = cleaned_title
        
        # Pulizia finale
        new_file_name = re.sub(r'\s*-\s*', '-', new_file_name)
        new_file_name = re.sub(r'-+', '-', new_file_name)
        new_file_name = re.sub(r'\s+', ' ', new_file_name).strip()
        
        extension = os.path.splitext(file_path)[1][1:]
        new_file_name = get_unique_file_name(new_folder, new_file_name, extension)
        new_file_path = os.path.join(new_folder, new_file_name)

        if action == 'copiare':
            shutil.copy(file_path, new_file_path)
        elif action == 'spostare':
            shutil.move(file_path, new_file_path)
        write_tags(new_file_path, metadata['title'], metadata['year'], metadata['genres'], metadata['director'])
        new_file_names[file_path] = new_file_name
    return new_file_names, scelta  # Restituisco anche scelta per html

# Crea pagina HTML
def create_html_page(files_metadata, new_file_names, scelta):
    with open('PyOrganizzaFilm.html', 'w', encoding='utf-8') as f:
        f.write('<html><body><a href="https://github.com/MoonDragon-MD/PyOrganizesFilms" target="_blank"><h1>PyOrganizzaFilm</h1></a>')
        f.write('<input type="text" id="searchInput" onkeyup="searchMovies()" placeholder="Cerca film..">')
        f.write('<ul id="movieList">')
        for file_path, metadata in files_metadata.items():
            genre = metadata['genres'][0] if metadata['genres'] else 'Misti'
            decade = get_decade(metadata['year'])
            new_file_name = new_file_names.get(file_path)
            if not new_file_name:
                continue
            
            # Determina il percorso del file in base alla scelta
            if scelta == 'a':
                file_link = os.path.join('Films_Organizzati', genre, new_file_name)
            elif scelta == 'b':
                file_link = os.path.join('Films_Organizzati', decade if decade else genre, new_file_name)
            elif scelta == 'c':
                file_link = os.path.join('Films_Organizzati', genre, decade if decade else '', new_file_name)
            
            # Usa il titolo pulito per la visualizzazione
            cleaned_title = clean_title(metadata['title']).strip()
            file_title = f"{cleaned_title} - {metadata['year']}" if metadata['year'] else cleaned_title
            wiki_url = metadata['full_article_url'] if metadata['full_article_url'] else '#'
            
            f.write(f'<li><strong><a href="{file_link}">{escape_html(file_title)}</a></strong>')
            f.write(f' <a href="{wiki_url}" target="_blank">      Wikipedia</a><br>')
            f.write(f'Regista: {escape_html(metadata["director"])}<br>')
            f.write(f'Attori: {escape_html(metadata["actors"])}<br>')
            f.write(f'<p>{escape_html(metadata["plot"])}</p></li>')
        f.write('''
        <script>
        function searchMovies() {
            var input = document.getElementById('searchInput').value.toUpperCase();
            var li = document.getElementById("movieList").getElementsByTagName('li');
            for (var i = 0; i < li.length; i++) {
                var txtValue = li[i].textContent || li[i].innerText;
                li[i].style.display = txtValue.toUpperCase().indexOf(input) > -1 ? "" : "none";
            }
        }
        </script></body></html>''')

# Main
if __name__ == '__main__':
    print("#########################################")
    print("####  PyOrganizzaFilm by MoonDragon  ####")
    print("####       v.2.0 Revisione n11       ####")    
    print("#########################################")
    files = [os.path.join(dp, f) for dp, _, fn in os.walk(CARTELLA_FILM) for f in fn if f.endswith(('.mp4', '.m4v', '.avi', '.mkv', '.mov'))]
    debug_print(f"Trovati {len(files)} file")

    while True:
        use_tags = input("Vuoi leggere i tag dai file (nota: potrebbero essere scritti male - consiglio di mettere no)? (si/no o s/n): ").strip().lower()
        if use_tags in ['s', 'si']:
            use_tags = True
            break
        elif use_tags in ['n', 'no']:
            use_tags = False
            break
        print("Input non valido. Riprova.")

    files_metadata = {}
    for file_path in files:
        metadata = get_full_metadata(file_path, use_tags)
        files_metadata[file_path] = metadata

    while True:
        action = input("Vuoi spostare o copiare i file? (spostare/copiare o spo/cop): ").strip().lower()
        if action in ['spo', 'spostare']:
            action = 'spostare'
            break
        elif action in ['cop', 'copiare']:
            action = 'copiare'
            break
        print("Input non valido. Riprova.")

    scelta = chiedi_organizzazione()
    new_file_names, scelta = organize_files(files_metadata, action, scelta)  # Ricevi scelta
    create_html_page(files_metadata, new_file_names, scelta)  # Passa scelta
    debug_print("Fine script")
