#!/usr/bin/env bash
# Installe les navigateurs Playwright (Chromium) pour le moteur V2 (Crawl4AI).
# À exécuter une fois après : pip install -r requirements.txt
# Usage : ./scripts/install_playwright.sh   ou   bash scripts/install_playwright.sh

set -e
playwright install chromium
echo "Playwright Chromium installé. Vous pouvez utiliser le moteur V2 dans l'app."
