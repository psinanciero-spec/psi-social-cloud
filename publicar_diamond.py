#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAMOND CLEANING - Publicador de Reels en la nube (GitHub Actions).

Publica el proximo pendiente de diamond-queue.json en @diamondcleaning.gc.

El pie NO se arma aca: viene ya escrito en cada entrada, calculado por
preparar_diamond.ps1 en la PC. Antes se armaba en el momento con un contador
compartido y, cuando dos corridas caian juntas, las dos leian el mismo numero y
publicaban el MISMO texto (paso el 02/09/2026, dos reels identicos con 21
segundos de diferencia). Con el pie precalculado eso no puede pasar.
"""
import json
import os
import sys
import time

import requests

TOKEN = os.environ["DIAMOND_IG_TOKEN"]
IG_USER_ID = "38503730179240667"
QUEUE_FILE = "diamond-queue.json"
VIDEO_DIR = "diamond"
GRAPH = "https://graph.instagram.com/v21.0"
# Los videos se sirven desde el repo publico por GitHub raw: litterbox y otros
# hosts bloquean las IPs de los runners de Actions.
RAW_BASE = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"
# ID de la pagina de Facebook de Diamond, que tiene direccion real cargada
# (283 Reedy Creek Rd, Burleigh, QLD 4220). Instagram valida este ID.
LOCATION_ID = "1024620414070638"


def log(msg):
    print("[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        cola = json.load(f)

    sig = next((x for x in cola if x["status"] == "pending"), None)
    if not sig:
        log("No hay reels pendientes. Correr preparar_diamond.ps1 en la PC.")
        return

    ruta = os.path.join(VIDEO_DIR, sig["file"])
    if not os.path.exists(ruta):
        log("ERROR: no existe %s" % ruta)
        sys.exit(1)

    video_url = RAW_BASE + "%s/%s" % (VIDEO_DIR, sig["file"])
    log("Reel: %s | %s | tema=%s" % (sig["id"], sig["file"], sig.get("tema", "?")))

    # 1. Container
    j = requests.post("%s/%s/media" % (GRAPH, IG_USER_ID), data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": sig["caption"],
        "location_id": LOCATION_ID,
        "share_to_feed": "true",
        "access_token": TOKEN,
    }, timeout=120).json()
    if "id" not in j:
        log("ERROR creando container: %s" % j)
        sys.exit(1)
    creation_id = j["id"]
    log("  container %s" % creation_id)

    # 2. Esperar el procesamiento
    listo = False
    for _ in range(40):
        time.sleep(10)
        try:
            st = requests.get("%s/%s" % (GRAPH, creation_id), params={
                "fields": "status_code", "access_token": TOKEN}, timeout=60).json()
            if st.get("status_code") == "FINISHED":
                listo = True
                break
            if st.get("status_code") == "ERROR":
                log("ERROR: Instagram rechazo el video: %s" % st)
                sys.exit(1)
        except requests.RequestException as e:
            log("  reintento del estado: %s" % e)
    if not listo:
        log("ERROR: el video no termino de procesarse")
        sys.exit(1)

    # 3. Publicar, con reintentos: Meta tira errores transitorios
    pub = None
    for i in range(6):
        j = requests.post("%s/%s/media_publish" % (GRAPH, IG_USER_ID), data={
            "creation_id": creation_id, "access_token": TOKEN}, timeout=120).json()
        if "id" in j:
            pub = j
            break
        log("  intento %d fallido: %s" % (i + 1, j))
        time.sleep(15)
    if not pub:
        log("ERROR: media_publish fallo tras 6 intentos")
        sys.exit(1)

    log("PUBLICADO ig_id=%s" % pub["id"])

    for x in cola:
        if x["id"] == sig["id"]:
            x["status"] = "published"
            x["ig_id"] = pub["id"]
            x["publicado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    quedan = sum(1 for x in cola if x["status"] == "pending")
    log("Cola actualizada. Pendientes: %d (%d dias a 4 por dia)" % (quedan, quedan // 4))
    if quedan <= 4:
        log("AVISO: queda menos de un dia. Correr preparar_diamond.ps1 en la PC.")


if __name__ == "__main__":
    main()
