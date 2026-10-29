"""
Configuration du projet AéroTrack.

Les valeurs sensibles (clé secrète, mode debug, hôtes autorisés) sont lues
dans le fichier .env, qui n'est jamais versionné.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(nom, defaut=False):
    """Lit une variable d'environnement booléenne (true/1/yes/oui)."""
    valeur = os.getenv(nom)
    if valeur is None:
        return defaut
    return valeur.strip().lower() in ("1", "true", "yes", "oui")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY est absente : copiez .env.example en .env et renseignez-la."
    )

DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Modules AéroTrack
    "comptes",
    "referentiels",
    "emplacements",
    "equipements",
    "interventions",
    "journal",
    "tableau_bord",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Toutes les pages exigent une connexion, sauf celles marquées login_not_required.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aerotrack.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "comptes.context_processors.role",
            ],
        },
    },
]

WSGI_APPLICATION = "aerotrack.wsgi.application"

# --- Base de données (SQLite) -----------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.getenv("SQLITE_PATH", "db.sqlite3"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Mots de passe ----------------------------------------------------------

if "test" in sys.argv:
    # Hachage rapide pendant les tests uniquement (le hachage réel est volontairement lent).
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Connexion ---------------------------------------------------------------

LOGIN_URL = "comptes:connexion"
LOGIN_REDIRECT_URL = "tableau_bord:accueil"
LOGOUT_REDIRECT_URL = "comptes:connexion"

# Session fermée après 8 heures (une vacation) ou à la fermeture du navigateur
SESSION_COOKIE_AGE = 8 * 60 * 60

# --- Langue et fuseau horaire -----------------------------------------------

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques -----------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # rempli par collectstatic en production

# --- Sécurité ---------------------------------------------------------------

SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Site servi en HTTPS (PythonAnywhere, ou Nginx avec un certificat) :
# cookies envoyés uniquement sur une connexion chiffrée, et formulaires
# acceptés depuis l'adresse https:// des hôtes autorisés.
if env_bool("DJANGO_HTTPS", False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]
