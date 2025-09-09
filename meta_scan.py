#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
meta_scan.py — OSINT para Facebook mediante RapidAPI
Autor: HackUnderway (mejorado)
Características:
- API key desde .env (sin hardcodear)
- requests.Session con retries + backoff
- Timeouts configurables por CLI
- Flags para saltar endpoints "premium" (evitar 403 si no estás suscrito)
- Manejo de errores claro y consistente

Uso básico:
  python3 meta_scan.py -u nasa --no-page --no-posts
  python3 meta_scan.py -u nasa --connect-timeout 20 --read-timeout 60
"""

import os
import sys
import json
import argparse
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dotenv import load_dotenv
import colorama
from colorama import Fore, Back

# -----------------------------
# Constantes de endpoints
# -----------------------------

# Perfil (usando el API que compartiste)
PROFILE_HOST = "facebook-pages-scraper3.p.rapidapi.com"
PROFILE_PATH = "/get-profile-home-page-details"   # acepta urlSupplier o url

# Página y Posts (otro proveedor distinto; puede requerir suscripción)
PAGE_HOST = "social-media-scrape.p.rapidapi.com"
PAGE_DETAILS_PATH = "/get_facebook_pages_details"   # param: link
POSTS_DETAILS_PATH = "/get_facebook_posts_details"  # param: link

# Ajustes de red
DEFAULT_TIMEOUT: Tuple[int, int] = (15, 45)  # (connect, read) en segundos
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.6


# -----------------------------
# Utilidades de red / sesión
# -----------------------------

def build_session() -> requests.Session:
    """Crea una sesión requests con reintentos/backoff y User-Agent."""
    session = requests.Session()
    retries = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "meta-scan/1.0 (+https://github.com/HackUnderway/meta_scan)"})
    return session


def get_env_keys() -> Tuple[str, Optional[str], Optional[str]]:
    """
    Lee claves del .env:
    - RAPIDAPI_KEY               (común para todas las APIs)
    - RAPIDAPI_KEY_FB_SCRAPER3   (opcional, específica)
    - RAPIDAPI_KEY_SOCIAL_SCRAPE (opcional, específica)
    """
    load_dotenv()
    common = os.getenv("RAPIDAPI_KEY")
    fb_key = os.getenv("RAPIDAPI_KEY_FB_SCRAPER3", None)
    social_key = os.getenv("RAPIDAPI_KEY_SOCIAL_SCRAPE", None)
    if not common and not (fb_key or social_key):
        raise RuntimeError(
            "No se encontró RAPIDAPI_KEY en .env (o RAPIDAPI_KEY_FB_SCRAPER3 / RAPIDAPI_KEY_SOCIAL_SCRAPE)."
        )
    return common or "", fb_key, social_key


def choose_key(common: str, specific: Optional[str]) -> str:
    """Usa la clave específica si existe; si no, la común."""
    return specific.strip() if (specific and specific.strip()) else common


def rapidapi_get(
    session: requests.Session,
    host: str,
    path: str,
    params: Dict[str, Any],
    api_key: str,
    timeout: Tuple[int, int] = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """GET a RapidAPI host con manejo de errores y JSON estricto."""
    url = f"https://{host}{path}"
    headers = {
        "x-rapidapi-host": host,
        "x-rapidapi-key": api_key,
    }

    try:
        resp = session.get(url, headers=headers, params=params, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        raise RuntimeError(
            f"Connection timeout al conectar con {host}. "
            f"Prueba subir --connect-timeout o verifica tu red/VPN/Proxy."
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            f"Read timeout leyendo respuesta de {host}. "
            f"Prueba subir --read-timeout."
        )
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"No se pudo conectar a {host}: {e}. "
            f"Posibles causas: caída del proveedor, bloqueo de red/ISP, VPN/Proxy, o puerto 443 filtrado."
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error de red al consultar {host}{path}: {e}")

    if not resp.ok:
        # Intenta parsear JSON para mensaje de error más útil
        try:
            payload = resp.json()
        except Exception:
            payload = {"error": (resp.text or "")[:300]}
        raise RuntimeError(
            f"HTTP {resp.status_code} en {host}{path}. "
            f"Detalles: {json.dumps(payload, ensure_ascii=False)}"
        )

    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(
            f"Respuesta no es JSON válido desde {host}{path}: {(resp.text or '')[:300]}"
        )


# -----------------------------
# Funciones de negocio
# -----------------------------

def get_profile_details(session: requests.Session, username: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene detalles del perfil con el API 'facebook-pages-scraper3'.
    Enviamos ambos params (urlSupplier, url) para ser compatibles.
    """
    fb_url = f"https://www.facebook.com/{username}"
    params = {"urlSupplier": fb_url, "url": fb_url}
    data = rapidapi_get(session, PROFILE_HOST, PROFILE_PATH, params, api_key)

    # Normalización
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        return data["data"]
    return data if isinstance(data, dict) else None


def get_page_details(session: requests.Session, username: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Obtiene detalles de la página mediante 'social-media-scrape' (puede requerir suscripción)."""
    fb_url = f"https://www.facebook.com/{username}"
    params = {"link": fb_url}
    data = rapidapi_get(session, PAGE_HOST, PAGE_DETAILS_PATH, params, api_key)

    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def get_posts_details(session: requests.Session, username: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Obtiene detalles de posts mediante 'social-media-scrape' (puede requerir suscripción)."""
    fb_url = f"https://www.facebook.com/{username}"
    params = {"link": fb_url}
    data = rapidapi_get(session, PAGE_HOST, POSTS_DETAILS_PATH, params, api_key)

    if isinstance(data, dict) and "data" in data:
        return data
    if isinstance(data, list):
        return {"data": {"posts": data}}
    return None


# -----------------------------
# Presentación por consola
# -----------------------------

def print_banner():
    colorama.init(autoreset=True)
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦🟦🟦🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜⬜🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦⬜⬜⬜⬜🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Fore.BLUE + "   🟦🟦🟦🟦🟦⬜⬜🟦🟦")
    print(Back.GREEN + Fore.BLACK + "  By HackUnderway  ")


def show_profile(profile: Dict[str, Any]):
    print(Fore.GREEN + "\nDetalles del perfil:\n")
    print(Fore.YELLOW + f"ID: {profile.get('id', 'N/A')}")
    print(Fore.YELLOW + f"Tipo: {profile.get('type_name', profile.get('type', 'N/A'))}")
    print(Fore.YELLOW + f"Nombre: {profile.get('name', 'N/A')}")
    print(Fore.YELLOW + f"Género: {profile.get('gender', 'N/A')}")
    print(Fore.YELLOW + f"Foto de perfil: {profile.get('profile_picture', 'N/A')}")
    print(Fore.YELLOW + f"Foto de portada: {profile.get('cover_photo', 'N/A')}\n")

    intro_cards = profile.get('INTRO_CARDS') or profile.get('intro_cards') or {}
    if isinstance(intro_cards, dict) and intro_cards:
        print(Fore.YELLOW + "Detalles adicionales:")
        for key, value in intro_cards.items():
            k = str(key).replace('INTRO_CARD_', '').replace('_', ' ').title()
            print(Fore.YELLOW + f" - {k}: {value}")

    photos = profile.get('PHOTOS') or profile.get('photos')
    if isinstance(photos, list) and photos:
        print(Fore.YELLOW + "\nFotos:")
        for p in photos[:20]:
            uri = p.get('uri') or p.get('url') or 'N/A'
            pid = p.get('id', 'N/A')
            print(Fore.YELLOW + f" - {uri} (ID: {pid})")


def show_page(page_info: Dict[str, Any]):
    print(Fore.GREEN + "\nDetalles de la página:\n")
    print(Fore.YELLOW + f"Título: {page_info.get('title', 'N/A')}")
    print(Fore.YELLOW + f"Descripción: {page_info.get('description', 'N/A')}")
    print(Fore.YELLOW + f"Imagen: {page_info.get('image', 'N/A')}")
    print(Fore.YELLOW + f"URL: {page_info.get('url', 'N/A')}")
    print(Fore.YELLOW + f"Usuario ID: {page_info.get('user_id', 'N/A')}")
    print(Fore.YELLOW + f"Redirigido a: {page_info.get('redirected_url', 'N/A')}\n")


def show_posts(posts_data: Dict[str, Any]):
    posts = (((posts_data or {}).get('data') or {}).get('posts')) or []
    if not posts:
        print(Fore.RED + "\nNo se encontraron publicaciones (o tu plan no las incluye).")
        return

    print(Fore.GREEN + "\nDetalles de las publicaciones:\n")
    for post in posts:
        details = post.get('details', {})
        reactions = post.get('reactions', {})
        values = post.get('values', {})

        print(Fore.YELLOW + f"Post ID: {details.get('post_id', 'N/A')}")
        print(Fore.YELLOW + f"Texto: {values.get('text', 'N/A')}")
        print(Fore.YELLOW + f"Reacciones totales: {reactions.get('total_reaction_count', 'N/A')}")
        print(Fore.YELLOW + f"Comentarios: {details.get('comments_count', 'N/A')}")
        print(Fore.YELLOW + f"Compartidos: {details.get('share_count', 'N/A')}\n")

        attachments = post.get('attachments') or []
        for att in attachments:
            t = att.get('__typename')
            if t == 'Photo':
                img = ((att.get('photo_image') or {}).get('uri')) or 'N/A'
                print(Fore.YELLOW + f" - Imagen: {img}")


# -----------------------------
# Guardado opcional (JSON)
# -----------------------------

def save_json_if_requested(out_dir: Optional[str], username: str,
                           profile: Optional[Dict[str, Any]],
                           page: Optional[Dict[str, Any]],
                           posts: Optional[Dict[str, Any]]) -> None:
    if not out_dir:
        return
    try:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, username.replace("/", "_") or "output")

        payload = {
            "username": username,
            "profile": profile,
            "page": page,
            "posts": posts,
        }
        out_path = f"{base}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(Fore.CYAN + f"\n[✔] Guardado en JSON: {out_path}")
    except Exception as e:
        print(Fore.RED + f"\n[!] Error guardando JSON: {e}")


# -----------------------------
# Main / CLI
# -----------------------------

def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Meta Scan OSINT para Facebook (RapidAPI)")
    parser.add_argument("-u", "--username", help="Nombre de usuario/permalink de Facebook (ej: nasa)")
    parser.add_argument("--no-page", action="store_true", help="No consultar detalles de página (endpoint premium).")
    parser.add_argument("--no-posts", action="store_true", help="No consultar posts (endpoint premium).")
    parser.add_argument("--connect-timeout", type=int, default=15, help="Timeout de conexión en segundos.")
    parser.add_argument("--read-timeout", type=int, default=45, help="Timeout de lectura en segundos.")
    parser.add_argument("--out-json", help="Directorio para guardar salida combinada en JSON (ej: ./salida).")
    args = parser.parse_args()

    # Actualiza timeouts por lo pedido en CLI
    global DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = (args.connect-timeout if hasattr(args, "connect-timeout") else args.connect_timeout,
                       args.read-timeout if hasattr(args, "read-timeout") else args.read_timeout)

    # Python no permite guiones en attrs; por compat, corregimos:
    # (arriba está el fallback por si la CLI inyecta con guion; normalmente no pasa)
    DEFAULT_TIMEOUT = (args.connect_timeout, args.read_timeout)

    username = args.username or input(Fore.RED + "\n[*] Escribe tu nombre de usuario: ").strip()
    if not username:
        print(Fore.RED + "Usuario vacío. Saliendo.")
        sys.exit(1)

    try:
        common, fb_key, social_key = get_env_keys()
    except Exception as e:
        print(Fore.RED + f"[Config] {e}")
        sys.exit(1)

    session = build_session()

    # Acumular resultados por si queremos guardarlos
    profile = None
    page = None
    posts = None

    # ---- Perfil (facebook-pages-scraper3)
    try:
        profile = get_profile_details(session, username, choose_key(common, fb_key))
        if profile:
            show_profile(profile)
        else:
            print(Fore.RED + "\nNo se obtuvo perfil (respuesta vacía).")
    except Exception as e:
        print(Fore.RED + f"\nError al obtener los detalles del perfil: {e}")

    # ---- Página (social-media-scrape; puede requerir suscripción)
    if not args.no_page:
        try:
            page = get_page_details(session, username, choose_key(common, social_key))
            if page:
                show_page(page)
            else:
                print(Fore.RED + "\nNo se pudieron obtener los detalles de la página (¿endpoint premium?).")
        except Exception as e:
            print(Fore.RED + f"\nError al obtener los detalles de la página: {e}")
    else:
        print(Fore.YELLOW + "\n[Saltado] Detalles de página por --no-page")

    # ---- Posts (social-media-scrape; puede requerir suscripción)
    if not args.no_posts:
        try:
            posts = get_posts_details(session, username, choose_key(common, social_key))
            if posts:
                show_posts(posts)
            else:
                print(Fore.RED + "\nNo se pudieron obtener los detalles de las publicaciones (¿endpoint premium?).")
        except Exception as e:
            print(Fore.RED + f"\nError al obtener los detalles de las publicaciones: {e}")
    else:
        print(Fore.YELLOW + "\n[Saltado] Detalles de publicaciones por --no-posts")

    # Guardado opcional a JSON
    save_json_if_requested(args.out_json, username, profile, page, posts)


if __name__ == "__main__":
    main()
