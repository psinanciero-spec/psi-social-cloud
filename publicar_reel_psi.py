#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSI FINANCIERO - Publicador de Reels en la nube (GitHub Actions)
Publica el proximo reel pendiente de psi-reels-queue.json en @psi.financiero.

Los videos salen de las placas verticales del banco creativo, armados con
ADS\\systems\\psi-financiero\\outputs\\reels\\armar-reels.py.
"""
import os
import sys
import json
import time
import requests

TOKEN      = os.environ["PSI_FIN_TOKEN"]
IG_USER_ID = "27246132295017842"
QUEUE_FILE = "psi-reels-queue.json"
VIDEO_DIR  = "reels-psi"
GRAPH      = "https://graph.instagram.com/v21.0"
# Los videos se sirven directo desde el repo publico (GitHub raw).
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def url_publica(path):
    return RAW_BASE + path.replace("\\", "/")


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        queue = json.load(f)

    nxt = next((x for x in queue if x["status"] == "pending"), None)
    if not nxt:
        log("No hay reels pendientes. Nada que hacer.")
        return

    log(f"Reel a publicar: {nxt['id']} | {nxt['file']}")

    video_path = os.path.join(VIDEO_DIR, nxt["file"])
    if not os.path.exists(video_path):
        log(f"ERROR: no existe el archivo {video_path}")
        sys.exit(1)
    video_url = url_publica(f"{VIDEO_DIR}/{nxt['file']}")
    log(f"  Video URL: {video_url}")

    # 1. Crear container REELS
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": nxt["caption"],
        "access_token": TOKEN,
    }, timeout=120)
    j = r.json()
    if "id" not in j:
        log(f"ERROR creando container: {j}")
        sys.exit(1)
    container = j["id"]
    log(f"  Container: {container}")

    # 2. Esperar a que Instagram termine de procesar el video
    ready = False
    for _ in range(40):
        time.sleep(10)
        s = requests.get(f"{GRAPH}/{container}",
                         params={"fields": "status_code", "access_token": TOKEN},
                         timeout=60).json()
        code = s.get("status_code")
        if code == "FINISHED":
            ready = True
            break
        if code == "ERROR":
            log(f"  ERROR procesando video: {s}")
            sys.exit(1)
    if not ready:
        log("El video no termino de procesarse a tiempo.")
        sys.exit(1)

    # 3. Publicar (con reintentos por errores transitorios de Meta)
    published = False
    for i in range(8):
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish",
                          data={"creation_id": container, "access_token": TOKEN},
                          timeout=120)
        j = r.json()
        if "id" in j:
            log(f"PUBLICADO OK: {nxt['id']} | Reel ID: {j['id']}")
            published = True
            break
        log(f"  Intento publish {i} fallo ({j}), reintento en 20s")
        time.sleep(20)

    if not published:
        log(f"FALLO la publicacion de {nxt['id']}.")
        sys.exit(1)

    # 4. Marcar como publicado y guardar
    for x in queue:
        if x["id"] == nxt["id"]:
            x["status"] = "published"
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    sig = next((x["id"] for x in queue if x["status"] == "pending"), "ninguno")
    log(f"Cola actualizada. Siguiente: {sig}")


if __name__ == "__main__":
    main()
