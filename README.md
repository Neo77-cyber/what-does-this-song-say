What Does The Song Say?

Foreign Song Translator for Spotify

Have you ever being listening to a foreign song you love so much and you just don't get the slangs the artist says in the song. I built this app so i can always enjoy my favorite foreign songs.

Features

    Spotify Integration: One-click OAuth login to sync your library.

    Modern Design: Sleek dark-mode UI with a "Glassmorphism" translation box.

    AI-Powered: High-accuracy translations that preserve the meaning of lyrics.

Tech Stack

    Backend: Django (Python 3.9)

    Database: PostgreSQL 

    Frontend: HTML5, CSS3 (Flexbox/Grid), HTMX

    API: Spotipy (Spotify Web API)

    Deployment: Docker & Render

Local Setup (with Docker)

The fastest way to get this running locally is using Docker.

    Clone the repo:
    Bash

    git clone https://github.com/your-username/what-does-the-song-say.git
    cd what-does-the-song-say

    Set up your .env file:
    Create a .env file in the root directory and add your credentials:
    Code snippet

    SECRET_KEY=your_django_secret_key
    SPOTIPY_CLIENT_ID=your_spotify_client_id
    SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
    SPOTIPY_REDIRECT_URI=http://localhost:8000/callback/
    DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

    Run with Docker Compose:
    Bash

    docker-compose up --build

    Visit http://localhost:8000 in your browser.

    License

Distributed under the MIT License.
