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

# Script PyOrganizesFilms by MoonDragon v.1.0
# January 2025 - revision n29

# Software dependencies
# sudo apt-get install mkvtoolnix ffmpeg
# pip install requests tinytag mutagen beautifulsoup4

# Variable to enable/disable debugging
DEBUG = False  # Change to True/False
# avviare server con ./kiwix-serve '/percorso/cartella/FILE.zim' -p 5000
KIWIX_API_URL = 'http://localhost:5000/search'
KIWIX_VIEWER_URL = 'http://localhost:5000'
# download zims from https://download.kiwix.org/zim/  USE ONLY ENGLISH (wikipedia_en*) if you want Italian use PyOrganizesFilms.py
KIWIX_FILE = 'wikipedia_en_all_nopic_2024-06' # Change according to your file set on the server
CARTELLA_FILM = 'Path/to/your/movies' # Change according to your folder containing movies
# Generate and print debug if enabled
def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")
# Clean the title from unnecessary things, if necessary add what you want to improve the search on wiki
def clean_title(title):
    unwanted_words = ["1440p", "1080p", "720p", "576p", "480p", "360p", "VP8", "VP9", "AV1", "MPEG-4", "HEVC", "ProRes", "x264", "h264", "x265", "h265"] 
    for word in unwanted_words:
        title = title.replace(word, "")
    return title.strip()
# Function to get metadata from video and audio files
def get_metadata(file_path, use_tags=True):
    if use_tags:
        title, year = get_metadata_from_file(file_path)
        if title and year:
            return title, year
    
    return get_metadata_from_title(file_path)
# Function to read audio/video metadata using TinyTag
def get_metadata_from_file(file_path):
    debug_print(f"DEBUG: Get metadata for {file_path}")
    try:
        tag = TinyTag.get(file_path)
        debug_print(f"DEBUG: Metadata obtained from TinyTag: {tag}")
        return tag.title, tag.year
    except TinyTagException as e:
        debug_print(f"DEBUG: Error TinyTagException for {file_path}: {e}")
        return None, None
# Function that uses ffprobe to read metadata from files not handled by TinyTag
def get_metadata_from_video(file_path, ask_for_fallback=True):
    debug_print(f"DEBUG: Get metadata from {file_path}")

    # Let's assume that file_path is the path to the Wikipedia HTML
    if not os.path.exists(file_path):
        debug_print(f"DEBUG: The file {file_path} it doesn't exist.")
        return None, None

    try:
        # Read HTML content of file offline
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Use BeautifulSoup to parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Movie Title Extraction
        title_tag = soup.find('h1', {'class': 'firstHeading'})
        title = title_tag.text.strip() if title_tag else None
        debug_print(f"DEBUG: Extracted title: {title}")

        # Extracting the year from the synoptic (infobox)
        year = None
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and ('Release date' in header.text or 'Released' in header.text):
                    year_cell = row.find('td')
                    if year_cell:
                        year_match = re.search(r'\b\d{4}\b', year_cell.text)
                        if year_match:
                            year = year_match.group(0)  # Extract only the year (e.g., 2000)
                            debug_print(f"DEBUG: Year extracted: {year}")
                            break  # Find the first year

        # If the year was not found in the synoptic, we can do further research
        if not year:
            debug_print("DEBUG: Year not found in the synoptic, trying other sources...")

            # Try searching the HTML more generally
            # For example, searching for the year in the text that appears after 'Year'
            text_content = soup.get_text()
            year_candidates = re.findall(r'\b\d{4}\b', text_content)  # Search all 4 digit numbers
            if year_candidates:
                year = year_candidates[0]
                debug_print(f"DEBUG: Year found in text: {year}")
            else:
                debug_print("DEBUG: Year not found in text.")

        return title, year

    except Exception as e:
        debug_print(f"DEBUG: Error parsing HTML: {e}")
        return None, None
# Main function that decides how to read metadata
def get_full_metadata(file_path, use_tags=True):
    if file_path.endswith(('.mp4', '.m4v', '.mov')):  # For video files supported by Mutagen
        return get_metadata_from_file(file_path)
    
    if file_path.endswith(('.avi', '.mkv')):  # For video files that are not handled directly by TinyTag
        return get_metadata_from_video(file_path)
    
    return get_metadata_from_title(file_path)  # If they are not video files, use the file name
# it's useful if I have a pair of four numbers	
def ask_for_year(years, file_name):
    print(f"You found the following possible years in the file: {', '.join(years)} nel file: {file_name}.")
    for year in years:
        response = input(f"Is this the year of the movie? (yes/no) for the year {year}: ").strip().lower()
        if response == 'yes':
            return year
    return None
# Extract metadata from file name
def get_metadata_from_title(file_path):
    debug_print(f"DEBUG: Using the file name to get metadata")
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
    # Search for the year in the format "-2001" or "- 2001"
    year_match = re.search(r'-\s*(\d{4})\b', base_name)
    year = None
    if year_match:
        year = year_match.group(1)
        base_name = re.sub(r'-\s*\d{4}\b', '', base_name).strip()
    else:
        # Search for a four-digit number that is not preceded by a hyphen
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
    # Build the request URL
    response = requests.get(f'{KIWIX_API_URL}?books.name={KIWIX_FILE}&pattern={search_title} film')
    # Check if the request was successful
    if response.status_code != 200:
        debug_print(f"DEBUG: Error in request. Status: {response.status_code}")
        return []
    # Parse the HTML response
    soup = BeautifulSoup(response.content.decode('utf-8', errors='ignore'), 'html.parser')
    results_div = soup.find('div', class_='results')
    if not results_div:
        debug_print("DEBUG: No results found.")
        return []
    # Find all <li> elements that represent infobox = research articles
    results = results_div.find_all('li')
    articles = []

    for result in results:
        link = result.find('a')
        if link:
            title = link.text.strip()
            href = link['href']
            full_article_url = f"{KIWIX_VIEWER_URL}{href}"
            debug_print(f"DEBUG: Full URL of the article: {full_article_url}")

            # check year correspondence between file and wiki
            found_year = None  # Make sure to define found_year
            # Logic to extract found_year from article if needed

            if year and found_year and year != found_year:
                response = input(f"The year found on Wikipedia is {found_year}. Is this correct? (yes/no): ").strip().lower()
                if response == 'yes':
                    year = found_year  # Use Wikipedia year
                    debug_print(f"I use the year found on Wikipedia: {year}")
                else:
                    debug_print("I'm looking for another year.")
                    continue  # Skip to next article

            # Check if the title contains "(film)"
            if "film)" in title.lower():
                articles.append(href)
                break    # Find the first correct result and stop
            # If it doesn't contain "(film)", check the synopsis
            article_response = requests.get(full_article_url)
            debug_print(f"DEBUG: Request URL: {full_article_url}")
            if article_response.status_code == 200:
                debug_print(f"DEBUG: Request successful for {href}")
                article_content = article_response.content.decode('utf-8', errors='ignore')
                article_soup = BeautifulSoup(article_content, 'html.parser')
                infobox = article_soup.find('table', {'class': 'infobox vevent'})

                if infobox:
                    debug_print(f"DEBUG: Infobox found for {href}")
                    has_director = any('Directed by' in th.text for th in infobox.find_all('th'))
                    if has_director:
                        articles.append(href)
                        debug_print(f"DEBUG: Found valid article: {href}")
                        break
                    else:
                        debug_print(f"DEBUG: Infobox found but 'Directed by' not present in {href}")
                else:
                    debug_print(f"DEBUG: Infobox not found for {href}")
            else:
                debug_print(f"DEBUG: Error in request for {href}. State: {article_response.status_code}, Answer: {article_response.text}")
    # If no items found, return an empty list
    if not articles:
        debug_print("DEBUG: No valid articles found.")

    return articles

def get_full_metadata(file_path, use_tags):
    title, year = get_metadata(file_path, use_tags)
    title = clean_title(title)
    debug_print(f"DEBUG: Title: {title}, Year: {year}")

    articles = search_article(title, year)  # pass the given year here
    if not articles:
        articles = search_article(f"{title} (film", year)  # And here

    plot = 'No summary available'
    director = 'Unknown director'
    actors = 'Unknown actors'
    article_url = None
    full_article_url = None

    if articles:
        debug_print(f"DEBUG: Articles found: {articles}")
        article_url = articles[0]
        full_article_url = f'file:///content/{article_url}'
        article_response = requests.get(f'{KIWIX_VIEWER_URL}{article_url}')
        if article_response.status_code == 200:
            article_content = article_response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(article_content, 'html.parser')

            # Plot extraction
            plot_section = soup.find('h2', string=re.compile("Plot", re.IGNORECASE))
            if plot_section:
                # Find the paragraph below the "Plot" section
                plot_paragraph = plot_section.find_next('p')
                if plot_paragraph:
                    plot = plot_paragraph.text.strip()
                    plot_words = plot.split()[:300]  # Limit to 300 words
                    plot = ' '.join(plot_words)
                    # Take the first three sentences
                    sentences = plot.split('.')
                    plot = '. '.join(sentences[:3]) + '.' if len(sentences) > 2 else plot

            infobox = soup.find('table', {'class': 'infobox vevent'}) or soup.find('table', {'class': 'infobox vevent haudio'})
            if infobox:
                rows = infobox.find_all('tr')
                for row in rows:
                    header = row.find('th')
                    data = row.find('td')
                    if header and data:
                        if 'Release date' in header.text or 'Released' in header.text:
                            year_match = re.search(r'\b\d{4}\b', data.text)
                            if year_match:
                                year = year_match.group(0)
                        elif 'Directed by' in header.text:
                            director = data.text.strip()
                        elif 'Starring' in header.text:
                            actors_list = data.find_all('li')
                            if actors_list:
                                actors = ', '.join([li.text.strip() for li in actors_list])
                            else:
                                actors = data.text.strip()

                debug_print(f"DEBUG: Extracted information: Year: {year}, Plot: {plot}, Directed by: {director}, Starring: {actors}, Full Article URL: {full_article_url}")

    return {
        'title': title,
        'year': year,
        'plot': plot,
        'director': director,
        'actors': actors,
        'article_url': article_url,
        'full_article_url': full_article_url
    }
# Extract only year from wiki for alternative function to reading tags from file
def extract_year_from_article(article_url):
    try:
        # Request the content of the article
        article_response = requests.get(f'{KIWIX_VIEWER_URL}{article_url}')
        if article_response.status_code == 200:
            article_content = article_response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(article_content, 'html.parser')

            # Search for the year in the article content
            # Suppose the year is written in yyyy format in some specific sections
            year_match = re.search(r'(\d{4})', article_content)
            if year_match:
                year = year_match.group(1)
                debug_print(f"DEBUG: Year extracted from the article: {year}")
                return year
            else:
                debug_print("DEBUG: Year not found in article.")
                return None
        else:
            debug_print(f"DEBUG: Error requesting item. Status: {article_response.status_code}")
            return None
    except Exception as e:
        debug_print(f"DEBUG: Error extracting year from article: {e}")
        return None
# Write tags in the fixed files
def write_tags(file_path, title, year):
    try:
        if file_path.endswith(('.mp4', '.m4v', '.mov')): 
            if file_path.endswith(('.mp4', '.m4v')):  # For mp4 and m4v, use Mutagen
                audio = MP4(file_path)
                tags = audio.tags
                if tags is None:
                    tags = MP4Tags()
                    audio.tags = tags
                tags["\xa9nam"] = title  # Title
                tags["\xa9day"] = year   # Year of publication
                audio.save()
            else:
                # For .mov we use ffmpeg 
                cmd = [
                    'ffmpeg', '-i', file_path, '-metadata',
                    f'title={title}', '-metadata', f'year={year}',
                    '-codec', 'copy', 'temp_' + file_path
                ]
                subprocess.run(cmd, check=True)  # Run the ffmpeg command with check=True
                
                # Rename the temporary file
                subprocess.run(['mv', f'temp_{file_path}', file_path], check=True)
            
            debug_print(f"DEBUG: Tag scritti per {file_path}")
        elif file_path.endswith('.mkv'):
            # Set only title for .mkv files
            cmd = [
                'mkvpropedit', file_path,
                '--set', f'title={title}'
            ]
            subprocess.run(cmd, check=True)  # Run the mkvpropedit command with check=True
            debug_print(f"DEBUG: Tag scritti per {file_path}")
    except subprocess.CalledProcessError as e:
        debug_print(f"DEBUG: Error executing subprocess command for {file_path}: {e}")
    except Exception as e:
        debug_print(f"DEBUG: Unknown error while writing tags for {file_path}: {e}")

# avoid having two identical names		
def get_unique_file_name(directory, base_name, extension):
    base_name = sanitize_filename(base_name)  # Clean up the base name
    counter = 1
    new_name = f"{base_name}.{extension}"
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base_name} - Duplicate {counter}.{extension}"
        counter += 1
    return new_name
# further cleaning name
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()
# I organize the files by decade
def organize_files(files_metadata, action):
    debug_print(f"DEBUG: File Organization")
    new_file_names = {}
    for file_path, metadata in files_metadata.items():
        year = metadata['year']
        if year and year.isdigit():
            decade = f"{(int(year) // 10) * 10}s"
        else:
            decade = 'Unknown Decade'
        
        new_folder = os.path.join('Organized_Films', decade)
        os.makedirs(new_folder, exist_ok=True)

        new_file_name = clean_title(f"{metadata['title']}").strip().replace('\n', '').replace('\r', '')  # Remove newlines and spaces

        # Debug print
        debug_print(f"DEBUG: New generated file name: {new_file_name}")

        if metadata['year'] and metadata['year'] not in new_file_name:
            new_file_name += f" - {metadata['year']}"

        extension = file_path.split('.')[-1]
        new_file_name = get_unique_file_name(new_folder, new_file_name, extension)  # Make sure the name is unique
        new_file_path = os.path.join(new_folder, new_file_name)

        debug_print(f"DEBUG: {action.capitalize()} di {file_path} in {new_file_path}")

        try:
            if action == 'copy':
                shutil.copy(file_path, new_file_path)
            elif action == 'spostare':
                shutil.move(file_path, new_file_path)

            write_tags(new_file_path, metadata['title'], metadata['year'])
            
            new_file_names[file_path] = new_file_name
            debug_print(f"DEBUG: New file name: {new_file_name}")
            debug_print(f"DEBUG: New organized file names: {new_file_names}")
        except Exception as e:
            debug_print(f"DEBUG: Error while {action} of {file_path} in {new_file_path}: {e}")
    return new_file_names

# Write tags in the fixed files
def write_tags(file_path, title, year):
    try:
        if file_path.endswith(('.mp4', '.m4v', '.mov')): 
            if file_path.endswith(('.mp4', '.m4v')):  # For mp4 and m4v, use Mutagen
                audio = MP4(file_path)
                tags = audio.tags
                if tags is None:
                    tags = MP4Tags()
                    audio.tags = tags
                tags["\xa9nam"] = title  # Title
                tags["\xa9day"] = year   # Year of publication
                audio.save()
            else:
                # For .mov we use ffmpeg 
                cmd = [
                    'ffmpeg', '-i', file_path, '-metadata',
                    f'title={title}', '-metadata', f'year={year}',
                    '-codec', 'copy', 'temp_' + file_path
                ]
                subprocess.run(cmd, check=True)  # Run the ffmpeg command with check=True
                
                # Rename the temporary file
                subprocess.run(['mv', f'temp_{file_path}', file_path], check=True)
            
            debug_print(f"DEBUG: Tags written for {file_path}")
        elif file_path.endswith('.mkv'):
            # Set only title for .mkv files
            cmd = [
                'mkvpropedit', file_path,
                '--set', f'title={title}'
            ]
            subprocess.run(cmd, check=True)  # Run the mkvpropedit command with check=True
            debug_print(f"DEBUG: Tags written for {file_path}")
    except subprocess.CalledProcessError as e:
        debug_print(f"DEBUG: Error executing subprocess command for {file_path}: {e}")
    except Exception as e:
        debug_print(f"DEBUG: Unknown error while writing tags for {file_path}: {e}")

# Create HTML page for information and search movies
def create_html_page(files_metadata, new_file_names):
    debug_print(f"DEBUG: Creating HTML page with file metadata")
    with open('PyOrganizesFilms.html', 'w', encoding='utf-8') as f:
        f.write('<html><body>')
        f.write('<h1><a href="https://github.com/MoonDragon-MD/PyOrganizesFilms">PyOrganizesFilms</a></h1>')
        f.write('<input type="text" id="searchInput" onkeyup="searchMovies()" placeholder="Film Search..">')
        f.write('<ul id="movieList">')

        for file_path, metadata in files_metadata.items():
            year = metadata.get("year")
            if year and year.isdigit():
                decade = f"{(int(year) // 10) * 10}s"
            else:
                decade = 'Unknown Decade'
            
            new_file_name = new_file_names.get(file_path)
            if new_file_name is None:
                debug_print(f"DEBUG: Warning! New name not found for {file_path}")
                continue

            # Manage the year
            if not year:
                debug_print(f"DEBUG: Year not found for {file_path}")
                year = "Unknown year"  # Missing Year Management

            file_link = os.path.join('Organized_Films', decade, new_file_name)
            file_title = metadata["title"]
            if year not in file_title:  # Add year to title if not present
                file_title = f"{file_title} - {year}"

            # Define the URL of Wikipedias
            if metadata['full_article_url']:
                full_article_url = metadata['full_article_url'].replace('file:///', '').replace('content/', '')
                wiki_url = f"http://localhost:5000/viewer#{full_article_url.replace('#/', '#')}"
                if wiki_url.startswith('http://localhost:5000/viewer#/'):
                    wiki_url = wiki_url.replace('http://localhost:5000/viewer#/', 'http://localhost:5000/viewer#')
            else:
                wiki_url = '#'

            debug_print(f"DEBUG: url wiki film: (wiki_url) ")

            # Write the list item with the movie title, VLC button and Wikipedia link
            f.write(f'<li class="file-item"><strong><a href="{file_link}" class="fileLink">{escape_html(file_title)}</a></strong><br>')
            f.write(f'<button class="copy-button" onclick="copyFolderPath(\'{file_link}\')">VLC</button> ')
            f.write(f'<a href="{wiki_url}">Wikipedia</a><br>')  # Use “wiki_url” for link to Wikipedia
            f.write(f'Directed by: {escape_html(metadata["director"])}<br>')
            f.write(f'Actors: {escape_html(metadata["actors"])}<br>')
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
                // Get the full URL of the page from the browser
                let pageUrl = window.location.href;
                // Decode URL
                pageUrl = decodeURIComponent(pageUrl);
                // Remove 'file://' from URL
                pageUrl = pageUrl.replace('file://', '');
                // Remove 'PyOrganizesFilms.html' from URL
                pageUrl = pageUrl.replace('PyOrganizesFilms.html', '');
                // Concatenate the fileLink to the obtained path
                let folderPath = pageUrl + fileLink;
                // Copy the path to the clipboard
                navigator.clipboard.writeText(folderPath).then(function() {
                    alert('vlc ' + folderPath);
                }).catch(function(err) {
                    console.error('Error copying to clipboard: ', err);
                });
            }
        </script>
        ''')
        f.write('</body></html>')

if __name__ == '__main__':
    debug_print("DEBUG: Script start")
    print("##########################################")
    print("####  PyOrganizesFilms by MoonDragon  ####")
    print("####         v.1.0 Review n29         ####")    
    print("##########################################")
    debug_print("DEBUG: Start script")
    file_types = ['*.mp4', '*.m4v', '*.avi', '*.mkv', '*.mov']
    files = []
    for dirpath, _, filenames in os.walk(CARTELLA_FILM):
        for file in filenames:
            if any(file.endswith(ext) for ext in ['.mp4', '.m4v', '.avi', '.mkv', '.mov']):
                files.append(os.path.join(dirpath, file))

    debug_print(f"DEBUG: Trovati {len(files)} file")
    use_tags = input("You want to read tags from files (note: they may be misspelled)? (yes/no): ").strip().lower() == 'yes'
    files_metadata = {}
    for file_path in files:
        metadata = get_full_metadata(file_path, use_tags)
        files_metadata[file_path] = metadata

    action = input("Do you want to move or copy files? (move/copy): ").strip().lower()
    while action not in ['move', 'copy']:
        action = input("Invalid input. Do you want to move or copy files? (move/copy): ").strip().lower()

    new_file_names = organize_files(files_metadata, action)
    create_html_page(files_metadata, new_file_names)
    debug_print("DEBUG: End script")
