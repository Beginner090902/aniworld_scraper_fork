from bs4 import BeautifulSoup

from src.custom_logging import setup_logger

logger = setup_logger(__name__)


class ProviderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class LanguageError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

language_mapping = ["Deutsch", "Ger-Sub", "English"]

def restructure_dict(given_dict):
    new_dict = {}
    already_seen = set()
    for key, value in given_dict.items():
        new_dict[value] = set([element.strip() for element in key.split(',')])
    return_dict = {}
    for key, values in new_dict.items():
        for value in values:
            if value in already_seen and value in return_dict:
                del return_dict[value]
                continue
            if value not in already_seen and value not in return_dict:
                return_dict[value] = key
                already_seen.add(value)
    return return_dict


def extract_lang_key_mapping(soup):
    lang_key_mapping = {}
    
    # Version 1: Alte Struktur mit changeLanguageBox
    change_language_div = soup.find("div", class_="changeLanguageBox")
    if change_language_div:
        lang_elements = change_language_div.find_all("img")
        for lang_element in lang_elements:
            language = lang_element.get("alt", "") + "," + lang_element.get("title", "")
            data_lang_key = lang_element.get("data-lang-key", "")
            if language and data_lang_key:
                lang_key_mapping[language] = data_lang_key
        logger.debug("Alte Struktur gefunden")
        ret = restructure_dict(lang_key_mapping)
        logger.debug(f"Restructured language mapping: {ret}")
        return ret
    
    # Version 2: Neue Struktur
    logger.debug("Suche in neuer Struktur...")
    
    # Methode 1: Direkt nach Buttons mit data-language-label und data-language-id suchen
    language_buttons = soup.find_all("button", {"data-language-id": True, "data-language-label": True})
    for button in language_buttons:
        lang_id = button.get("data-language-id", "")
        lang_label = button.get("data-language-label", "")
        if lang_label and lang_id:
            # Erstelle den gleichen Key wie in der alten Struktur
            language_key = f"{lang_label}, {lang_label}"
            lang_key_mapping[language_key] = lang_id
            logger.debug(f"Button gefunden: {lang_label} -> {lang_id}")
    
    # Methode 2: Suche nach der neuen Container-Struktur
    if not lang_key_mapping:
        # Finde alle Container mit Sprach-Headern
        language_containers = soup.find_all("div", class_="col-12")
        for container in language_containers:
            # Suche nach dem h5 Element mit der Sprache
            lang_heading = container.find("h5", class_=lambda c: c and "text-muted" in c)
            if lang_heading:
                lang_name = lang_heading.text.strip()
                # Suche nach Buttons in diesem Container
                provider_buttons = container.find_all("button", {"data-language-id": True})
                for button in provider_buttons:
                    lang_id = button.get("data-language-id", "")
                    if lang_name and lang_id:
                        language_key = f"{lang_name}, {lang_name}"
                        lang_key_mapping[language_key] = lang_id
                        logger.debug(f"Container gefunden: {lang_name} -> {lang_id}")
    
    # Methode 3: Suche nach img-Elementen als Fallback
    if not lang_key_mapping:
        lang_images = soup.find_all("img", alt=True)
        for img in lang_images:
            alt_text = img.get("alt", "")
            title_text = img.get("title", "")
            
            # Prüfe ob es ein Sprach-Bild ist
            if any(term in alt_text.lower() or term in title_text.lower() 
                   for term in ['german', 'deutsch', 'english', 'spanish', 'french', 'sprache', 'flagge']):
                
                language = f"{alt_text},{title_text}"
                data_lang_key = img.get("data-lang-key", "")
                
                # Suche nach data-lang-key im übergeordneten Element
                if not data_lang_key:
                    parent = img.find_parent()
                    if parent:
                        data_lang_key = parent.get("data-lang-key", "") or parent.get("data-language-id", "")
                
                if language and data_lang_key:
                    lang_key_mapping[language] = data_lang_key
                    logger.debug(f"Img gefunden: {language} -> {data_lang_key}")
    
    ret = restructure_dict(lang_key_mapping)
    logger.debug(f"Restructured language mapping: {ret}")
    return ret


def get_href_by_language(html_content, language, provider):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # NEU: Direkte Suche nach dem Button in der neuen Struktur
    # Das ist der zuverlässigste Weg für die neue Seite
    direct_buttons = soup.find_all("button", {"data-provider-name": True, "data-language-label": True})
    for button in direct_buttons:
        provider_name = button.get("data-provider-name", "")
        language_label = button.get("data-language-label", "")
        language_id = button.get("data-language-id", "")
        play_url = button.get("data-play-url", "")
        
        logger.debug(f"Direkter Button - Provider: {provider_name}, Language: {language_label}, ID: {language_id}")
        
        # Prüfe ob Provider und Sprache übereinstimmen
        if provider_name.upper() == provider.upper():
            if language_label and language.lower() in language_label.lower():
                logger.info(f"Direkter Button gefunden für {provider} - {language}")
                return play_url, language
            # Fallback: Prüfe über language-id (1 = Deutsch)
            if language_id == "1" and language.lower() == "deutsch":
                logger.info(f"Direkter Button über ID gefunden für {provider} - {language}")
                return play_url, language
    
    # Fallback: Alte Methode mit language_mapping
    try:
        lang_key_mapping = extract_lang_key_mapping(soup)
        
        # Hier musst du prüfen, wie dein language_mapping aussieht
        # Wahrscheinlich ist es ein Dictionary wie {"Deutsch": "1", "English": "2", ...}
        filtered_mapping = {}
        for key, value in lang_key_mapping.items():
            if language.lower() in key.lower():
                filtered_mapping[key] = value
        
        if not filtered_mapping:
            logger.error(f"Kein Language Mapping für '{language}' gefunden")
            logger.debug(f"Verfügbare Sprachen: {list(lang_key_mapping.keys())}")
            raise LanguageError(f"No language mapping found for '{language}'")
        
        # Nimm den ersten passenden Eintrag
        lang_key = list(filtered_mapping.values())[0]
        used_lang = list(filtered_mapping.keys())[0]
        
        logger.debug(f"Verwende Language Key: {lang_key} für {used_lang}")
        
        # Alte Struktur: Suche nach li-Elementen
        matching_li_elements = soup.find_all("li", {"data-lang-key": lang_key})
        matching_li_element = next((li_element for li_element in matching_li_elements
                                    if li_element.find("h4") and li_element.find("h4").get_text() == provider), None)
        
        if matching_li_element:
            href = matching_li_element.get("data-link-target", "")
            return href, used_lang
            
    except Exception as e:
        logger.error(f"Fehler bei der alten Methode: {e}")
    
    # Wenn wir hier ankommen, wurde nichts gefunden
    logger.error(f"Kein passender Download für Sprache '{language}' und Provider '{provider}' gefunden")
    
    # Debug: Zeige alle gefundenen Provider und Sprachen
    all_buttons = soup.find_all("button", {"data-provider-name": True})
    for button in all_buttons:
        logger.debug(f"Verfügbarer Button - Provider: {button.get('data-provider-name')}, "
                    f"Language: {button.get('data-language-label')}, "
                    f"ID: {button.get('data-language-id')}")
    
    raise ProviderError(f"No matching download found for language '{language}' and provider '{provider}'")