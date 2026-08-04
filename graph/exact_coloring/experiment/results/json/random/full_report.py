#!/usr/bin/env python3
"""
full_report.py
==============

Ce script est destiné à être placé dans un répertoire contenant plusieurs
sous-dossiers (ex : 30_vertices, 40_vertices, 50_vertices).

Pour chaque sous-dossier contenant un fichier `stats.html`, le script :
  1. crée un dossier `full_report` dans le répertoire courant ;
  2. copie le `stats.html` dans ce dossier en le préfixant avec le nombre
     de sommets extrait du nom du sous-dossier (ex : `50_stats.html`).

Exemple d'utilisation :
    python3 full_report.py
"""

import os
import re
import shutil


def extract_vertex_count(folder_name: str) -> str:
    """
    Extrait le nombre de sommets depuis le nom d'un dossier.

    Exemples :
        "50_vertices"  -> "50"
        "30_vertices2" -> "30"
        "my_folder"    -> "my_folder"  (repli sur le nom complet)
    """
    match = re.match(r"^(\d+)", folder_name)
    if match:
        return match.group(1)
    return folder_name


def main() -> None:
    # Répertoire contenant le script (portable : fonctionne même si on
    # exécute le script depuis un autre répertoire de travail).
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Création du dossier full_report
    report_dir = os.path.join(base_dir, "full_report")
    os.makedirs(report_dir, exist_ok=True)

    copied = 0

    # 2. Parcours des sous-dossiers du répertoire courant
    for entry in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, entry)

        # On ne traite que les vrais dossiers (et on ignore full_report lui-même)
        if not os.path.isdir(folder_path) or entry == "full_report":
            continue

        stats_path = os.path.join(folder_path, "stats.html")
        if not os.path.isfile(stats_path):
            print(f"[skip] {entry}/ : pas de stats.html")
            continue

        # 3. Copie avec préfixe = nombre de sommets
        prefix = extract_vertex_count(entry)
        dest_name = f"{prefix}_stats.html"
        dest_path = os.path.join(report_dir, dest_name)

        shutil.copy2(stats_path, dest_path)
        print(f"[ok]   {entry}/stats.html  ->  full_report/{dest_name}")
        copied += 1

    print(f"\nTerminé : {copied} fichier(s) copié(s) dans "
          f"{os.path.join(base_dir, 'full_report')}.")


if __name__ == "__main__":
    main()