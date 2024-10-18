import colorama
from colorama import Fore, Back
import requests

def get_profile_details(username):
    fb_url = f"https://www.facebook.com/{username}"
    api_url = f"https://facebook-pages-scraper3.p.rapidapi.com/get-profile-home-page-details?urlSupplier={fb_url}"
    headers = {
        'x-rapidapi-host': 'facebook-pages-scraper3.p.rapidapi.com',
        'x-rapidapi-key': 'YOUR_API_KEY'
    }
    
    response = requests.get(api_url, headers=headers)
    return response.json() if response.ok else None

def get_page_details(username):
    fb_url = f"https://www.facebook.com/{username}"
    api_url = f"https://social-media-scrape.p.rapidapi.com/get_facebook_pages_details?link={fb_url}"
    headers = {
        'x-rapidapi-host': 'social-media-scrape.p.rapidapi.com',
        'x-rapidapi-key': 'YOUR_API_KEY'
    }

    response = requests.get(api_url, headers=headers)
    return response.json() if response.ok else None

def get_posts_details(username):
    fb_url = f"https://www.facebook.com/{username}"
    api_url = f"https://social-media-scrape.p.rapidapi.com/get_facebook_posts_details?link={fb_url}"
    headers = {
        'x-rapidapi-host': 'social-media-scrape.p.rapidapi.com',
        'x-rapidapi-key': 'YOUR_API_KEY'
    }

    response = requests.get(api_url, headers=headers)
    return response.json() if response.ok else None

def main():
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

    username = input(Fore.RED + "\n[*] Escribe tu nombre de usuario: ")

    # Obtener detalles del perfil
    profile_data = get_profile_details(username)
    if profile_data:
        print(Fore.GREEN + "\nDetalles del perfil:\n")
        print(Fore.YELLOW + f"ID: {profile_data.get('id', 'N/A')}")
        print(Fore.YELLOW + f"Tipo: {profile_data.get('type_name', 'N/A')}")
        print(Fore.YELLOW + f"Nombre: {profile_data.get('name', 'N/A')}")
        print(Fore.YELLOW + f"Género: {profile_data.get('gender', 'N/A')}")
        print(Fore.YELLOW + f"Foto de perfil: {profile_data.get('profile_picture', 'N/A')}")
        print(Fore.YELLOW + f"Foto de portada: {profile_data.get('cover_photo', 'N/A')}\n")
        
        print(Fore.YELLOW + "Detalles adicionales:")
        intro_cards = profile_data.get('INTRO_CARDS', {})
        for key, value in intro_cards.items():
            print(Fore.YELLOW + f" - {key.replace('INTRO_CARD_', '').replace('_', ' ').title()}: {value}")

        # Imprimir fotos
        if 'PHOTOS' in profile_data:
            print(Fore.YELLOW + "\nFotos:")
            for photo in profile_data['PHOTOS']:
                print(Fore.YELLOW + f" - {photo['uri']} (ID: {photo['id']})")
    else:
        print(Fore.RED + "\nError al obtener los detalles del perfil.")

    # Obtener detalles de la página
    page_data = get_page_details(username)
    if page_data:
        page_info = page_data[0]  # Asumiendo que la respuesta es una lista
        print(Fore.GREEN + "\nDetalles de la página:\n")
        print(Fore.YELLOW + f"Título: {page_info.get('title', 'N/A')}")
        print(Fore.YELLOW + f"Descripción: {page_info.get('description', 'N/A')}")
        print(Fore.YELLOW + f"Imagen: {page_info.get('image', 'N/A')}")
        print(Fore.YELLOW + f"URL: {page_info.get('url', 'N/A')}")
        print(Fore.YELLOW + f"Usuario ID: {page_info.get('user_id', 'N/A')}")
        print(Fore.YELLOW + f"Redirigido a: {page_info.get('redirected_url', 'N/A')}\n")
    else:
        print(Fore.RED + "\nNo se pudieron obtener los detalles de la página (Necesitas la API premium).")

    # Obtener detalles de las publicaciones
    posts_data = get_posts_details(username)
    if posts_data and 'data' in posts_data and 'posts' in posts_data['data']:
        print(Fore.GREEN + "\nDetalles de las publicaciones:\n")
        for post in posts_data['data']['posts']:
            post_details = post['details']
            reactions = post['reactions']
            values = post['values']
            
            print(Fore.YELLOW + f"Post ID: {post_details['post_id']}")
            print(Fore.YELLOW + f"Texto: {values['text']}")
            print(Fore.YELLOW + f"Reacciones totales: {reactions['total_reaction_count']}")
            print(Fore.YELLOW + f"Comentarios: {post_details['comments_count']}")
            print(Fore.YELLOW + f"Compartidos: {post_details['share_count']}\n")
            
            # Imprimir medios si están disponibles
            if 'attachments' in post:
                for attachment in post['attachments']:
                    if attachment['__typename'] == 'Photo':
                        print(Fore.YELLOW + f" - Imagen: {attachment['photo_image']['uri']}")
    else:
        print(Fore.RED + "\nNo se pudieron obtener los detalles de las publicaciones (Necesitas la API premium).")

if __name__ == "__main__":
    main()
