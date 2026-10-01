#!/bin/bash

# =========================================================================
# FIN_FLOW - Script de Vérification de Déploiement
# Usage: bash deploy-check.sh [URL]
# Exemple: bash deploy-check.sh https://finflow.votredomaine.com
# =========================================================================

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URL de base (par défaut localhost)
BASE_URL="${1:-http://localhost:8080}"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   FIN_FLOW - Vérification de Déploiement      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}URL testée: ${BASE_URL}${NC}"
echo ""

# Fonction de test
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_code="${3:-200}"
    
    echo -n "  ➜ ${name}... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${endpoint}" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ ÉCHEC${NC} (HTTP $response, attendu: $expected_code)"
        return 1
    fi
}

# Fonction de test JSON
test_json_endpoint() {
    local name="$1"
    local endpoint="$2"
    local key="$3"
    
    echo -n "  ➜ ${name}... "
    
    response=$(curl -s "${BASE_URL}${endpoint}" 2>/dev/null || echo "{}")
    
    if echo "$response" | jq -e ".$key" > /dev/null 2>&1; then
        value=$(echo "$response" | jq -r ".$key")
        echo -e "${GREEN}✓ OK${NC} ($key: $value)"
        return 0
    else
        echo -e "${RED}✗ ÉCHEC${NC} (clé '$key' non trouvée)"
        return 1
    fi
}

# Compteurs
passed=0
failed=0

echo -e "${BLUE}[1/5] Frontend${NC}"
if test_endpoint "Page d'accueil" "/" 200; then ((passed++)); else ((failed++)); fi
echo ""

echo -e "${BLUE}[2/5] API REST${NC}"
if test_endpoint "API Root" "/api/v1/" 200; then ((passed++)); else ((failed++)); fi
echo ""

echo -e "${BLUE}[3/5] Santé de l'Application${NC}"
if command -v jq &> /dev/null; then
    if test_json_endpoint "Statut général" "/api/v1/health/" "status"; then ((passed++)); else ((failed++)); fi
    if test_json_endpoint "Base de données" "/api/v1/health/" "database"; then ((passed++)); else ((failed++)); fi
    if test_json_endpoint "Stockage S3" "/api/v1/health/" "storage"; then ((passed++)); else ((failed++)); fi
else
    echo -e "${YELLOW}  ⚠ jq non installé, tests JSON ignorés${NC}"
    if test_endpoint "Health endpoint" "/api/v1/health/" 200; then ((passed++)); else ((failed++)); fi
fi
echo ""

echo -e "${BLUE}[4/5] Documentation${NC}"
if test_endpoint "Swagger UI" "/api/docs/" 200; then ((passed++)); else ((failed++)); fi
if test_endpoint "Schéma OpenAPI" "/api/schema/" 200; then ((passed++)); else ((failed++)); fi
echo ""

echo -e "${BLUE}[5/5] Administration${NC}"
if test_endpoint "Django Admin" "/django-admin/" 302; then ((passed++)); else ((failed++)); fi
echo ""

# Résumé
total=$((passed + failed))
percentage=$((passed * 100 / total))

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Résumé des Tests                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Tests réussis: ${GREEN}${passed}${NC} / ${total}"
echo -e "  Tests échoués: ${RED}${failed}${NC} / ${total}"
echo -e "  Taux de réussite: ${percentage}%"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ Déploiement vérifié avec succès !         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ✗ Certains tests ont échoué                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Conseils de dépannage:${NC}"
    echo "  1. Vérifiez que tous les services sont démarrés:"
    echo "     docker compose ps"
    echo ""
    echo "  2. Consultez les logs:"
    echo "     docker compose logs backend frontend"
    echo ""
    echo "  3. Vérifiez la configuration réseau et le pare-feu"
    echo ""
    exit 1
fi
