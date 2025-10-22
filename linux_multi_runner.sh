#!/bin/bash

SCRIPT_PATH="py_main.py"

# Farbdefinitionen
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Funktion zur Eingabe mit Default-Wert
read_with_default() {
    local prompt="$1"
    local default="$2"
    local input
    
    read -p "$(echo -e "${CYAN}$prompt${NC} [${YELLOW}$default${NC}]: ")" input
    echo "${input:-$default}"
}

# Hauptskript
echo
echo -e "${PURPLE}🎌 Aniworld Scraper Batch Processor${NC}"
echo -e "${PURPLE}===================================${NC}"

# Type auswählen
echo
echo -e "${BLUE}Choose a type:${NC}"
echo "1. Anime"
echo "2. Serie"
TYPE=$(read_with_default "Type" "1")
case $TYPE in
    1|anime) TYPE="anime" ;;
    2|serie) TYPE="serie" ;;
    *) TYPE="anime" ;;
esac

# Language auswählen  
echo
echo -e "${BLUE}Choose a language:${NC}"
echo "1. Deutsch"
echo "2. Ger-Sub" 
echo "3. English"
LANGUAGE=$(read_with_default "Language" "1")
case $LANGUAGE in
    1|deutsch) LANGUAGE="Deutsch" ;;
    2|ger-sub) LANGUAGE="Ger-Sub" ;;
    3|english) LANGUAGE="English" ;;
    *) LANGUAGE="Deutsch" ;;
esac

# Download Mode auswählen
echo
echo -e "${BLUE}Choose a download mode:${NC}"
echo "1. Movies"
echo "2. Series"
echo "3. All"
DLMODE=$(read_with_default "Download Mode" "2")
case $DLMODE in
    1|movies) DLMODE="Movies" ;;
    2|series) DLMODE="Series" ;;
    3|all) DLMODE="All" ;;
    *) DLMODE="Series" ;;
esac

# Provider auswählen
echo
echo -e "${BLUE}Choose a provider:${NC}"
echo "1. VOE"
echo "2. Vidoza"
echo "3. Streamtape"
PROVIDER=$(read_with_default "Provider" "1")
case $PROVIDER in
    1|voe) PROVIDER="VOE" ;;
    2|vidoza) PROVIDER="Vidoza" ;;
    3|streamtape) PROVIDER="Streamtape" ;;
    *) PROVIDER="VOE" ;;
esac

# Namen eingeben
echo
echo -e "${BLUE}Enter anime/series names (separated by spaces):${NC}"
echo -e "${YELLOW}Example: 'spy-x-family one-piece demon-slayer'${NC}"
read -p "Names: " NAMES

# Bestätigung
echo
echo -e "${GREEN}🚀 Starting batch processing with:${NC}"
echo -e "   Type: ${YELLOW}$TYPE${NC}"
echo -e "   Language: ${YELLOW}$LANGUAGE${NC}" 
echo -e "   Download Mode: ${YELLOW}$DLMODE${NC}"
echo -e "   Provider: ${YELLOW}$PROVIDER${NC}"
echo -e "   Names: ${YELLOW}$NAMES${NC}"
echo

# Verarbeitung starten
COUNTER=1
TOTAL=$(echo $NAMES | wc -w)

for NAME in $NAMES; do
    echo -e "${PURPLE}📦 Processing $COUNTER/$TOTAL: $NAME${NC}"
    python3 "$SCRIPT_PATH" --type "$TYPE" --name "$NAME" --lang "$LANGUAGE" --dl-mode "$DLMODE" --provider "$PROVIDER"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Success: $NAME${NC}"
    else
        echo -e "${RED}❌ Failed: $NAME${NC}"
    fi
    echo
    ((COUNTER++))
done

echo -e "${GREEN}🎉 All done! Processed $((COUNTER-1)) items.${NC}"