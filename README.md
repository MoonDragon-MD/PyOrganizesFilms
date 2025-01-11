# PyOrganizesFilms
EN- This project started in Italian then I turned it into English but I had to change some things since Wiki in English is organized differently than in Italian
# PyOrganizzaFilm
IT- Questo progetto è iniziato in italiano poi l'ho trasformato in inglese ma ho dovuto cambiare alcune cose in quanto Wiki in inglese è organizzata diversamente che in italiano

## Description

PyOrganizesFilms is a Python script designed to organize video files (movies) into a folder structure based on file metadata. 

This script uses the file name or internal tags to extract the title and year. 

Also, using Wikipedia offline via the Kiwix server, it gets the plot and actors.

The name set “Movie name - year” is considered “optimal” and you will not be asked if the digits after the hyphen correspond to the year of publication.

In Italian only, films can be organized by genre or by year or both. In English sopo by year (not my fault but the English wiki is set up wrong).

If it finds a same filename after the arrangement, it will be added Doubling to the filename (then check by hand which version to keep).

A web page will be created to open with the browser where there will be a search bar and the list of the fixed movies with also a button with the direct code for VLC and the link to the movie page on offline wiki (if you have turned on the server again)

NB: It all works OFFLINE

## Descrizione

PyOrganizzaFilm è uno script Python progettato per organizzare i file video (film) in una struttura di cartelle basata sui metadati dei file. 

Questo script usa il nome del file oppure i tag interni per estrarre il titolo e l'anno. 

Inoltre, usando Wikipedia offline tramite il server Kiwix, ottiene la trama e gli attori.

Il nome impostato "Nome Film - anno" viene ritenuto "ottimale" e non vi verrà chiesto se le cifre dopo il trattino corrispondano all'anno di pubblicazione.

Solo in italiano i film possono essere organizzati per genere o per anno o entrambi. In inglese sopo per anno (non è colpa mia ma di wiki inglese che è impostata male)

Se trova uno stesso nome file dopo la sistemazione, verrà aggiunto Doppione al nome del file (poi controllate a mano che versione tenere).

Verrà creata una pagina web da aprire con il browser dove ci sarà una barra di ricerca e l'elenco dei film sistemati con anche un pulsante con il codice diretto per VLC e il link alla pagina del film su wiki offline (se avete acceso ancora il server)

NB: Funziona tutto OFFLINE

## Features.

- **Metadata extraction**: Uses TinyTag and Mutagen to extract metadata from video and audio files.
- **Title Cleanup**: Removes unwanted words from file titles to improve Wikipedia searches.
- **Offline Wikipedia searches**: Use Kiwix to search Wikipedia offline and get additional information about movies.
- **File organization**: Organizes files into folders based on genre and decade, depending on the user's choice.
- **Tag writing**: Writes tags to organized video files using Mutagen and ffmpeg.
- **Generating an HTML page**: Creates an HTML page with details of the organized movies, including offline Wikipedia links, director, actors and plot.
  
## Funzionalità

- **Estrazione dei metadati**: Utilizza TinyTag e Mutagen per estrarre i metadati dai file video e audio.
- **Pulizia del titolo**: Rimuove parole indesiderate dai titoli dei file per migliorare le ricerche su Wikipedia.
- **Ricerche su Wikipedia offline**: Utilizza Kiwix per effettuare ricerche su Wikipedia offline e ottenere informazioni aggiuntive sui film.
- **Organizzazione dei file**: Organizza i file in cartelle basate su genere e decade, a seconda della scelta dell'utente.
- **Scrittura dei tag**: Scrive i tag nei file video organizzati utilizzando Mutagen e ffmpeg.
- **Generazione di una pagina HTML**: Crea una pagina HTML con i dettagli dei film organizzati, inclusi link a Wikipedia offline, regista, attori e trama.

## Dependencies / Dipendenze

- mkvtoolnix
- ffmpeg
- requests
- tinytag
- mutagen
- beautifulsoup4
- Python v3.*
- Kiwix server (Wikipedia offline): [kiwix-tools](https://download.kiwix.org/release/kiwix-tools/) I used kiwix-tools_linux-x86_64-3.7.0-2.tar.gz

## Installation / Installazione

    sudo apt-get install mkvtoolnix ffmpeg
    pip install requests tinytag mutagen beautifulsoup4 

## Usage / Utilizzo

EN- Configure the variables KIWIX_FILE and CARTELLA_FILM (film folder) in the source code.

IT- Configurare le variabili KIWIX_FILE e CARTELLA_FILM nel codice sorgente.

Start the Kiwix server with the command: / Avviare il server Kiwix con il comando:

    ./kiwix-serve '/folder/cartella/FILE.zim' -p 5000

Run the Python script. / Eseguire lo script Python.

    python3 *.py 
    
 EN- Follow the on-screen instructions to choose whether to read tags from files, move or copy files, and how to organize movies.
  When finished, an HTML page will be created with the details of the organized movies.
  
 IT- Seguire le istruzioni a schermo per scegliere se leggere i tag dai file, spostare o copiare i file, e come organizzare i film.
  Al termine, verrà creata una pagina HTML con i dettagli dei film organizzati.

## Screenshots

## Debug
EN- To enable debugging, change the DEBUG variable in the source code:

IT- Per abilitare il debug, modificare la variabile DEBUG nel codice sorgente:

    DEBUG = True

## Note
EN - Pay attention to the type of fil zim you download, for example, the version “wikipedia_en_all_mini_2024-02.zim” has no plot, so I used “wikipedia_en_all_nopic_2024-06.zim”

IT - Io ho usato la versione "wikipedia_it_all_maxi_2024-03.zim" ma va bene anche quella senza immagini
