#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSI FINANCIERO - Publicador de carruseles en la nube (GitHub Actions)
Publica el proximo carrusel pendiente de feed-queue.json en @psi.financiero.
"""
import os
import sys
import json
import time
import requests

TOKEN      = os.environ["PSI_FIN_TOKEN"]
IG_USER_ID = "27246132295017842"
QUEUE_FILE = "feed-queue.json"
IMG_DIR    = "feed"
GRAPH      = "https://graph.instagram.com/v21.0"
# Las imagenes se sirven directo desde el repo publico (GitHub raw).
# Instagram las descarga desde aca, sin depender de hosts externos.
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def url_publica(path):
    # path es relativo al repo, ej: feed/c10_1.jpg
    return RAW_BASE + path.replace("\\", "/")


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        queue = json.load(f)

    nxt = next((x for x in queue if x["status"] == "pending"), None)
    if not nxt:
        log("No hay carruseles pendientes. Nada que hacer.")
        return

    n_slides = nxt["slides"]
    log(f"Carrusel a publicar: {nxt['id']} | {n_slides} slides")

    # 1. Subir cada slide a hosting publico
    urls = []
    for i in range(1, n_slides + 1):
        path = os.path.join(IMG_DIR, f"{nxt['id']}_{i}.jpg")
        if not os.path.exists(path):
            log(f"ERROR: falta el archivo {path}")
            sys.exit(1)
        url = url_publica(f"{IMG_DIR}/{nxt['id']}_{i}.jpg")
        log(f"  Slide {i}: {url}")
        urls.append(url)

    # Carrusel necesita 2+ imagenes; si es 1 sola, post simple
    if n_slides == 1:
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
            "image_url": urls[0],
            "caption": nxt["caption"],
            "access_token": TOKEN,
        }, timeout=120)
        j = r.json()
        if "id" not in j:
            log(f"ERROR creando media: {j}"); sys.exit(1)
        creation_id = j["id"]
    else:
        # 2. Containers hijos
        child_ids = []
        for url in urls:
            r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": TOKEN,
            }, timeout=120)
            j = r.json()
            if "id" not in j:
                log(f"ERROR container hijo: {j}"); sys.exit(1)
            child_ids.append(j["id"])
            time.sleep(1)

        # 3. Container carrusel
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": nxt["caption"],
            "access_token": TOKEN,
        }, timeout=120)
        j = r.json()
        if "id" not in j:
            log(f"ERROR container carrusel: {j}"); sys.exit(1)
        creation_id = j["id"]

    log(f"  Creation ID: {creation_id}")
    time.sleep(5)

    # 4. Publicar (con reintentos por errores transitorios)
    published = False
    for i in range(8):
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish",
                          data={"creation_id": creation_id, "access_token": TOKEN},
                          timeout=120)
        j = r.json()
        if "id" in j:
            log(f"PUBLICADO OK: {nxt['id']} | Post ID: {j['id']}")
            published = True
            break
        log(f"  Intento publish {i} fallo ({j}), reintento en 20s")
        time.sleep(20)

    if not published:
        log(f"FALLO la publicacion de {nxt['id']}."); sys.exit(1)

    # 5. Marcar publicado
    for x in queue:
        if x["id"] == nxt["id"]:
            x["status"] = "published"
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    sig = next((x["id"] for x in queue if x["status"] == "pending"), "ninguno")
    log(f"Cola actualizada. Siguiente: {sig}")


if __name__ == "__main__":
    main()
