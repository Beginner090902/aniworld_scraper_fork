import re
from src.custom_logging import  setup_logger

logger = setup_logger(__name__)

filename = "network_setting/network_conection_data.txt"
def update_config_variable(variable_name, new_value):
    """Aktualisiert eine Variable in einer Config-Datei"""
    gefunden = False
    try:
        # Datei lesen
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Variable suchen und ersetzen
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{variable_name}="):
                gefunden = True
                lines[i] = f"{variable_name}={new_value}\n"
                updated = True
                break
        
        # Falls Variable nicht existiert, am Ende hinzufügen
        if not gefunden:
            logger.info(f"ℹ️ Variable '{variable_name}' nicht gefunden.") 
                  
        # Datei schreiben
        if gefunden:
            with open(filename, 'w', encoding='utf-8') as file:
                file.writelines(lines)
                logger.info(f"✅ Variable '{variable_name}' auf '{new_value}' gesetzt")
            return True
        
    except Exception as e:
        logger.error(f"❌ Fehler: {str(e)}")
        return False

def read_config_variable(variable_name, default=None):
    """Liest eine Variable aus der Config-Datei"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith(f"{variable_name}="):
                    if variable_name == "output_root":
                        return str(line.split('=', 1)[1].strip())
                    elif variable_name == "disable_thread_timer":
                        return str(line.split('=', 1)[1].strip())
                    else:
                        return int(line.split('=', 1)[1].strip())
        return logger.info("variable not found")
    except:
        return logger.info(f"variable not found")


