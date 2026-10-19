import secrets
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, OpenAIError
from werkzeug.utils import secure_filename

import config

app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(MAX_CONTENT_LENGTH=26_000_000, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Strict')
MAX_AUDIO_BYTES = 25_000_000


@app.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.get('/')
def index():
    session.setdefault('csrf', secrets.token_urlsafe(32))
    return render_template('index.html', csrf=session['csrf'])


@app.post('/transcribe')
def transcribe():
    token = session.get('csrf', '')
    if not token or not secrets.compare_digest(token, request.headers.get('X-CSRF-Token', '')):
        return jsonify(error='Session expirée. Rechargez la page.'), 403
    audio = request.files.get('audio')
    if not audio or not audio.filename:
        return jsonify(error='Sélectionnez un fichier MP3 ou OGG.'), 400
    filename = secure_filename(audio.filename)
    if Path(filename).suffix.lower() not in ('.mp3', '.ogg'):
        return jsonify(error='Le fichier doit avoir l’extension .mp3 ou .ogg.'), 400
    language = request.form.get('language', '')
    if language not in ('', 'fr', 'en', 'de', 'it', 'es'):
        return jsonify(error='Langue invalide.'), 400
    if not config.OPENAI_API_KEY.strip() or config.OPENAI_API_KEY == 'COLLEZ_VOTRE_CLE_API_ICI':
        return jsonify(error='Renseignez OPENAI_API_KEY dans config.py, puis relancez la transcription.'), 503
    data = audio.stream.read(MAX_AUDIO_BYTES + 1)
    if not data:
        return jsonify(error='Le fichier est vide.'), 400
    if len(data) >= MAX_AUDIO_BYTES:
        return jsonify(error='Le fichier doit faire moins de 25 Mo.'), 413
    if Path(filename).suffix.lower() == '.ogg':
        try:
            with tempfile.TemporaryDirectory(prefix='whisper-') as directory:
                source = Path(directory) / 'input.ogg'
                target = Path(directory) / 'output.mp3'
                source.write_bytes(data)
                subprocess.run(
                    ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                     '-protocol_whitelist', 'file,pipe', '-i', str(source),
                     '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000',
                     '-c:a', 'libmp3lame', '-b:a', '64k',
                     '-fs', str(MAX_AUDIO_BYTES), str(target)],
                    check=True, capture_output=True, timeout=60)
                if target.stat().st_size >= MAX_AUDIO_BYTES:
                    return jsonify(error='L’audio converti dépasse 25 Mo. Découpez l’enregistrement.'), 413
                data = target.read_bytes()
                if not data:
                    return jsonify(error='Le fichier OGG ne contient aucun audio exploitable.'), 400
                filename = Path(filename).stem + '.mp3'
        except subprocess.TimeoutExpired:
            return jsonify(error='Conversion trop longue. Découpez votre fichier OGG.'), 400
        except subprocess.CalledProcessError:
            return jsonify(error='Fichier OGG invalide ou sans piste audio lisible.'), 400
        except OSError:
            return jsonify(error='Conversion indisponible. Vérifiez l’installation de FFmpeg et l’espace temporaire.'), 503
    try:
        options = {'language': language} if language else {}
        with OpenAI(api_key=config.OPENAI_API_KEY, timeout=600.0, max_retries=0) as client:
            text = client.audio.transcriptions.create(
                model='whisper-1', file=(filename, data, 'audio/mpeg'),
                response_format='text', **options)
        return jsonify(text=text, filename=Path(filename).stem + '.txt')
    except AuthenticationError:
        return jsonify(error='Clé API invalide ou autorisation insuffisante.'), 401
    except RateLimitError:
        return jsonify(error='Quota, crédit API ou limite de débit atteint. Vérifiez votre compte OpenAI.'), 429
    except APIConnectionError:
        return jsonify(error='Connexion à OpenAI impossible ou délai dépassé. Réessayez plus tard.'), 502
    except OpenAIError:
        return jsonify(error='OpenAI n’a pas pu transcrire ce fichier. Vérifiez que le fichier contient un audio valide.'), 502


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error='Fichier trop volumineux : maximum 25 Mo.'), 413
