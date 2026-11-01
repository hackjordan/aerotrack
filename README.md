# AéroTrack

Application web de gestion des équipements techniques de la tour de contrôle de l'aéroport de Douala.
Elle est développée pour l'ASECNA (Activité Maintenance IRE, Unité RSI).

Technologies : Python 3, Django 5, SQLite, Bootstrap 5, Chart.js.
Bootstrap, Chart.js, Lucide et la police Inter sont servis en local depuis `static/vendor/`.
L'application fonctionne donc sur l'intranet sans accès à Internet.

## Installation (poste de développement, Windows)

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

Dans `.env`, renseignez `DJANGO_SECRET_KEY`. Pour générer une clé :

```powershell
.\venv\Scripts\python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Mettez aussi `DJANGO_DEBUG=True` sur le poste de développement. Ensuite :

```powershell
.\venv\Scripts\python manage.py migrate
.\venv\Scripts\python manage.py runserver
```

L'application est alors accessible sur http://127.0.0.1:8000/.

Pour accéder à l'interface d'administration (http://127.0.0.1:8000/admin/), créez d'abord un compte :

```powershell
.\venv\Scripts\python manage.py createsuperuser
```

## Tests

```powershell
.\venv\Scripts\python manage.py test
```

## Hébergement sur PythonAnywhere

Le site est accessible sur `https://<nom>.pythonanywhere.com`, où `<nom>` est votre nom d'utilisateur PythonAnywhere.
Un compte gratuit suffit. Dans les commandes ci-dessous, remplacez `<nom>` par ce nom d'utilisateur.

### 1. Récupérer le code

Dans l'onglet **Consoles**, ouvrez une console **Bash** :

```bash
git clone <url-du-depot-github> aerotrack
cd aerotrack
python3.11 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Ouvrez ensuite `aerotrack/.env` depuis l'onglet **Files** et renseignez :

```
DJANGO_SECRET_KEY=<la clé affichée par la dernière commande>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<nom>.pythonanywhere.com
DJANGO_HTTPS=True
SQLITE_PATH=db.sqlite3
```

### 2. Préparer la base et les fichiers statiques

```bash
venv/bin/python manage.py migrate
venv/bin/python manage.py init_donnees
venv/bin/python manage.py init_demo
venv/bin/python manage.py createsuperuser
venv/bin/python manage.py collectstatic --noinput
```

`init_demo` ajoute des équipements fictifs. Lancez-la seulement pour une démonstration.

### 3. Créer l'application web

Dans l'onglet **Web**, cliquez sur **Add a new web app**. Choisissez **Manual configuration** (et non « Django »), puis **Python 3.11**.

Sur la page de l'application, renseignez :

| Rubrique | Valeur |
|---|---|
| Source code | `/home/<nom>/aerotrack` |
| Virtualenv | `/home/<nom>/aerotrack/venv` |
| Static files | URL `/static/`, Directory `/home/<nom>/aerotrack/staticfiles` |
| Force HTTPS | activé |

Cliquez ensuite sur le lien **WSGI configuration file** et remplacez tout son contenu par :

```python
import sys

chemin = "/home/<nom>/aerotrack"
if chemin not in sys.path:
    sys.path.insert(0, chemin)

from aerotrack.wsgi import application  # noqa: E402,F401
```

Cliquez enfin sur **Reload**. En cas de problème, consultez le **Error log** dans l'onglet **Web**.

### Mettre le site à jour

```bash
cd ~/aerotrack
git pull
venv/bin/pip install -r requirements.txt
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
```

Puis cliquez sur **Reload** dans l'onglet **Web**.

### Charger les techniciens et les interventions

Ces données ne passent pas par GitHub : elles contiennent des noms et des mots de passe chiffrés.

Sur votre poste, créez le fichier `donnees_hebergeur.json` :

```powershell
.\venv\Scripts\python manage.py exporter_donnees
```

Dans l'onglet **Files**, ouvrez `/home/<nom>/aerotrack/` et envoyez ce fichier avec **Upload a file**. Ensuite, dans une console **Bash** :

```bash
cd ~/aerotrack
git pull
venv/bin/python manage.py charger_donnees
rm donnees_hebergeur.json
```

Les équipements doivent déjà exister sur le serveur (`init_demo` ou base importée). Sinon, rien n'est chargé.
La commande peut être relancée : ce qui existe déjà est ignoré, et un compte existant garde son mot de passe.

Avec un compte gratuit, cliquez sur **Run until 3 months from today** dans l'onglet **Web** au moins une fois tous les 3 mois.
Sinon, PythonAnywhere désactive le site.
