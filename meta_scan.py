#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
meta_scan.py — OSINT para Facebook mediante RapidAPI (solo endpoints funcionales)
Autor: HackUnderway (mejorado)
Características:
- API key desde .env o interactiva
- requests.Session con retries + backoff
- Timeouts configurables
- Múltiples endpoints del mismo host (perfil + negocio)
- Guardado en JSON y TXT opcional

Uso:
  python3 meta_scan.py -u nasa
  python3 meta_scan.py -u nasa --no-business --out-json ./salida
  python3 meta_scan.py --set-api
  python3 meta_scan.py --donate
"""

import os
import sys
import json
import argparse
import time
import random
import string
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dotenv import load_dotenv
import colorama
from colorama import Fore, Back, Style

# -----------------------------
# Constantes
# -----------------------------
PROFILE_HOST = "facebook-pages-scraper3.p.rapidapi.com"

# Endpoints disponibles
PROFILE_PATH = "/get-profile-home-page-details"
BUSINESS_HOME_PATH = "/get-business-home-page-details"
BUSINESS_ABOUT_PATH = "/get-business-about-details-page"
BUSINESS_TRANSPARENCY_PATH = "/get-business-about-profile-transparency-page-details"

DEFAULT_TIMEOUT: Tuple[int, int] = (15, 45)
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.6

# -----------------------------
# Configuración de sesión
# -----------------------------
def build_session() -> requests.Session:
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
    session.headers.update({"User-Agent": "meta-scan/2.0 (+https://github.com/HackUnderway/meta_scan)"})
    return session

# -----------------------------
# Manejo de API Key
# -----------------------------
def setup_api_key() -> str:
    print(Fore.YELLOW + "\n🔑 Configuración inicial de API Key\n")
    key = input("👉 Introduce tu clave de RapidAPI: ").strip()
    if not key:
        print(Fore.RED + "❌ Clave vacía. Saliendo.")
        sys.exit(1)
    with open(".env", "w") as f:
        f.write(f"RAPIDAPI_KEY={key}\n")
    print(Fore.GREEN + "✅ RAPIDAPI_KEY guardada en .env\n")
    return key

def get_api_key() -> str:
    load_dotenv()
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        key = setup_api_key()
    return key

# -----------------------------
# Llamadas a la API
# -----------------------------
def rapidapi_get(
    session: requests.Session,
    host: str,
    path: str,
    params: Dict[str, Any],
    api_key: str,
    timeout: Tuple[int, int] = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    url = f"https://{host}{path}"
    headers = {
        "x-rapidapi-host": host,
        "x-rapidapi-key": api_key,
    }
    try:
        resp = session.get(url, headers=headers, params=params, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"Error de red: {e}")

    if not resp.ok:
        try:
            payload = resp.json()
        except:
            payload = {"error": (resp.text or "")[:300]}
        raise RuntimeError(
            f"HTTP {resp.status_code} en {host}{path}. "
            f"Detalles: {json.dumps(payload, ensure_ascii=False)}"
        )
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(f"Respuesta no JSON: {(resp.text or '')[:300]}")

def get_profile_details(session, username, api_key):
    url = f"https://www.facebook.com/{username}"
    params = {"urlSupplier": url, "url": url}
    return rapidapi_get(session, PROFILE_HOST, PROFILE_PATH, params, api_key)

def get_business_home_details(session, username, api_key):
    url = f"https://www.facebook.com/{username}"
    params = {"urlSupplier": url}
    return rapidapi_get(session, PROFILE_HOST, BUSINESS_HOME_PATH, params, api_key)

def get_business_about_details(session, username, api_key):
    url = f"https://www.facebook.com/{username}"
    params = {"urlSupplier": url}
    return rapidapi_get(session, PROFILE_HOST, BUSINESS_ABOUT_PATH, params, api_key)

def get_business_transparency_details(session, username, api_key):
    url = f"https://www.facebook.com/{username}"
    params = {"urlSupplier": url}
    return rapidapi_get(session, PROFILE_HOST, BUSINESS_TRANSPARENCY_PATH, params, api_key)

# -----------------------------
# Presentación en consola
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

def print_section(title):
    print(Fore.CYAN + f"\n{'─' * 60}\n{title}\n{'─' * 60}")

def show_profile(profile: Dict[str, Any], show_raw=False):
    if show_raw:
        print(Fore.YELLOW + json.dumps(profile, indent=2, ensure_ascii=False))
        return

    print_section("📋 PERFIL")
    # Campos principales que interesan
    fields = [
        ("ID", "id"),
        ("Nombre", "name"),
        ("Tipo", "type_name"),
        ("Género", "gender"),
        ("Email", "email"),
        ("Teléfono", "phone"),
        ("Sitio web", "website"),
        ("Seguidores", "followers"),
        ("Me gusta", "likes"),
        ("Categorías", "categories"),
        ("Rango de precios", "priceRange"),
        ("Descripción", "best_description"),
        ("URL del perfil", "profile_url"),
        ("Foto de portada", "cover_photo"),
        ("Foto de perfil (grande)", "profile_pic_large"),
    ]
    for label, key in fields:
        val = profile.get(key)
        if val is not None and val != "":
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            print(Fore.YELLOW + f"{label:>20}: {Style.RESET_ALL}{val}")

    # Intro Cards
    intro = profile.get("INTRO_CARDS") or profile.get("intro_cards") or {}
    if intro:
        print(Fore.YELLOW + "\n📌 Información adicional:")
        for k, v in intro.items():
            kk = k.replace("INTRO_CARD_", "").replace("_", " ").title()
            print(Fore.YELLOW + f"   {kk:>18}: {Style.RESET_ALL}{v}")

    # Fotos (opcional, solo mostramos las primeras 5)
    photos = profile.get("PHOTOS") or profile.get("photos") or []
    if photos:
        print(Fore.YELLOW + f"\n🖼️  Fotos ({len(photos)}):")
        for p in photos[:5]:
            uri = p.get("uri") or p.get("url") or "N/A"
            print(Fore.YELLOW + f"   - {uri}")

def show_business_home(data: Dict[str, Any], show_raw=False):
    if show_raw:
        print(Fore.YELLOW + json.dumps(data, indent=2, ensure_ascii=False))
        return
    print_section("🏢 BUSINESS HOME")
    # Imprime todas las claves de primer nivel
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool)):
            print(Fore.YELLOW + f"{k:>25}: {Style.RESET_ALL}{v}")

def show_business_about(data: Dict[str, Any], show_raw=False):
    if show_raw:
        print(Fore.YELLOW + json.dumps(data, indent=2, ensure_ascii=False))
        return
    print_section("📝 ABOUT")
    about = data.get("about_text", "")
    if about:
        print(Fore.WHITE + about)
    else:
        print(Fore.RED + "No se encontró texto 'About'.")

def show_business_transparency(data: Dict[str, Any], show_raw=False):
    if show_raw:
        print(Fore.YELLOW + json.dumps(data, indent=2, ensure_ascii=False))
        return
    print_section("🔍 TRANSPARENCIA")
    ad_status = data.get("ad_status", "N/A")
    creation = data.get("creation_date", "N/A")
    print(Fore.YELLOW + f"Estado de anuncios: {Style.RESET_ALL}{ad_status}")
    print(Fore.YELLOW + f"Fecha de creación:  {Style.RESET_ALL}{creation}")

# -----------------------------
# Guardado de resultados
# -----------------------------
def save_json_if_requested(out_dir: Optional[str], username: str,
                           profile: Optional[Dict],
                           business_home: Optional[Dict],
                           business_about: Optional[Dict],
                           business_transparency: Optional[Dict]) -> None:
    if not out_dir:
        return
    try:
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        base = os.path.join(out_dir, f"{username}_{timestamp}_{rand}")
        payload = {
            "username": username,
            "profile": profile,
            "business_home": business_home,
            "business_about": business_about,
            "business_transparency": business_transparency,
        }
        out_path = f"{base}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(Fore.CYAN + f"\n[✔] Guardado en JSON: {out_path}")
    except Exception as e:
        print(Fore.RED + f"\n[!] Error guardando JSON: {e}")

# -----------------------------
# MAIN
# -----------------------------
def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Meta Scan OSINT para Facebook (RapidAPI)")
    parser.add_argument("-u", "--username", help="Nombre de usuario/permalink de Facebook")
    parser.add_argument("--no-business", action="store_true", help="Omitir todos los endpoints de negocio")
    parser.add_argument("--show-raw", action="store_true", help="Mostrar JSON crudo de cada respuesta")
    parser.add_argument("--connect-timeout", type=int, default=15, help="Timeout de conexión (segundos)")
    parser.add_argument("--read-timeout", type=int, default=45, help="Timeout de lectura (segundos)")
    parser.add_argument("--out-json", help="Directorio para guardar salida JSON combinada")
    parser.add_argument("--set-api", action="store_true", help="Configurar la API key en .env")
    parser.add_argument("--donate", action="store_true", help="Mostrar información de donación")
    args = parser.parse_args()

    if args.donate:
        print(Fore.MAGENTA + "\n💖 Apoya el proyecto\n")
        print(Fore.CYAN + "☕ https://buymeacoffee.com/HackUnderway")
        print(Fore.WHITE + "🙏 ¡Gracias por tu apoyo!\n")
        return

    if args.set_api:
        setup_api_key()
        return

    username = args.username or input(Fore.RED + "\n[*] Introduce el nombre de usuario: ").strip()
    if not username:
        print(Fore.RED + "Usuario vacío. Saliendo.")
        sys.exit(1)

    api_key = get_api_key()
    session = build_session()

    # Actualizar timeouts
    global DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = (args.connect_timeout, args.read_timeout)

    profile = None
    business_home = None
    business_about = None
    business_transparency = None

    # ---- Perfil (siempre)
    try:
        print(Fore.WHITE + f"\n🔍 Obteniendo perfil de @{username}...")
        profile = get_profile_details(session, username, api_key)
        if profile:
            show_profile(profile, args.show_raw)
        else:
            print(Fore.RED + "No se obtuvo perfil (respuesta vacía).")
    except Exception as e:
        print(Fore.RED + f"\nError en perfil: {e}")

    # ---- Business endpoints (si no se omiten)
    if not args.no_business:
        # Business Home
        try:
            print(Fore.WHITE + f"\n🔍 Obteniendo datos de negocio (home) de @{username}...")
            business_home = get_business_home_details(session, username, api_key)
            if business_home:
                show_business_home(business_home, args.show_raw)
            else:
                print(Fore.RED + "No se obtuvieron datos de business home.")
        except Exception as e:
            print(Fore.RED + f"\nError en business home: {e}")

        # Business About
        try:
            print(Fore.WHITE + f"\n🔍 Obteniendo texto 'About' de @{username}...")
            business_about = get_business_about_details(session, username, api_key)
            if business_about:
                show_business_about(business_about, args.show_raw)
            else:
                print(Fore.RED + "No se obtuvo 'About'.")
        except Exception as e:
            print(Fore.RED + f"\nError en business about: {e}")

        # Business Transparency
        try:
            print(Fore.WHITE + f"\n🔍 Obteniendo datos de transparencia de @{username}...")
            business_transparency = get_business_transparency_details(session, username, api_key)
            if business_transparency:
                show_business_transparency(business_transparency, args.show_raw)
            else:
                print(Fore.RED + "No se obtuvieron datos de transparencia.")
        except Exception as e:
            print(Fore.RED + f"\nError en transparencia: {e}")
    else:
        print(Fore.YELLOW + "\n[Saltado] Endpoints de negocio por --no-business")

    # Guardado
    save_json_if_requested(args.out_json, username,
                           profile, business_home, business_about, business_transparency)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n⚠️ Escaneo interrumpido\n")
        sys.exit(0)
