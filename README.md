# Whisper Web — MP3 et OGG vers TXT

Prérequis : Docker avec Docker Compose, une connexion Internet et une clé API OpenAI avec crédit API disponible.

## Démarrer

1. Décompressez l’archive.
2. Dans `config.py`, remplacez `COLLEZ_VOTRE_CLE_API_ICI` par votre clé API, entre les guillemets.
3. Ouvrez un terminal dans le dossier `whisper-web` et lancez :

```bash
docker compose up --build -d
```

4. Ouvrez http://localhost:8000.
5. Sélectionnez un MP3 ou OGG de moins de 25 Mo et cliquez sur « Transcrire l’audio ».
6. Consultez ou corrigez le texte puis cliquez sur « Télécharger le TXT ».

La clé est renseignée dans le code côté serveur : aucun champ de clé dans le formulaire. `config.py` est monté en lecture seule et exclu de l’image Docker. Après modification de la clé, lancez `docker compose restart`.

## Commandes

```bash
# Consulter les logs
docker compose logs -f

# Arrêter
docker compose down

# Relancer
docker compose up -d
```

## Fonctionnement et limites

- Modèle : `whisper-1`, endpoint OpenAI `/v1/audio/transcriptions`, format texte.
- Détection automatique de la langue ou sélection français, anglais, allemand, italien, espagnol.
- La transcription reste dans la page jusqu’à son rechargement. Le TXT contient les éventuelles corrections.
- Aucun historique ni volume de stockage audio. Flask peut utiliser un fichier temporaire pendant l’upload ; ces fichiers sont placés dans `/tmp`, monté en mémoire, puis fermés à la fin de la requête.
- Le MP3 est envoyé à OpenAI. Les règles de conservation d’OpenAI s’appliquent indépendamment de cette application. Les appels sont facturés au compte API.
- Fichiers de moins de 25 000 000 octets. Les fichiers plus volumineux doivent être compressés ou découpés au préalable.
- Délai API : 600 secondes. Pas de nouvelle tentative automatique pour éviter les appels répétés à votre insu.
- Par défaut, accessible uniquement sur l’ordinateur hôte (127.0.0.1). Cette application personnelle ne comporte pas de comptes utilisateurs. Une mise en ligne publique nécessite une authentification et HTTPS.
- Un seul worker conserve une session cohérente pour le jeton CSRF. Un redémarrage nécessite de recharger la page.
- La clé reste dans votre fichier local `config.py` : gardez ce fichier privé.

## Vérification effectuée

Les routes, validations, erreurs API et la réponse de transcription ont été vérifiées avec un client OpenAI simulé. Aucun appel payant n’est nécessaire pour ces tests. La construction Docker doit être effectuée sur votre machine si Docker n’est pas disponible dans l’environnement de préparation.

## Prise en charge OGG

Les fichiers `.ogg` (Vorbis ou Opus) sont convertis automatiquement par FFmpeg en MP3 mono 16 kHz à 64 kbit/s avant envoi à Whisper. FFmpeg est installé dans l’image. La taille du fichier importé et du fichier converti doit rester inférieure à 25 Mo. Conversion limitée à 60 secondes ; fichiers temporaires nettoyés après conversion, y compris en cas d’erreur.

Après mise à jour du projet, conservez votre `config.py` puis reconstruisez :

```bash
docker compose up --build -d
```
