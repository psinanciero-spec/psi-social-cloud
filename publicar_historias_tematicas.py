#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INGREDIENTE PSI - Publicador de las series tematicas de historias (5 slides
cada una), 1 serie por dia. Las 5 imagenes se publican seguidas, como
secuencia de historias -- cuenta como UN item de cupo diario, no cinco.
"""
import datetime
import json
import os
import random
import sys
import time

import requests

from cupo_diario import hay_cupo, publicados_hoy, CUPO_MAX

TOKEN      = os.environ["PSI_KREA_TOKEN"]
IG_USER_ID = "27949964061276820"
QUEUE_FILE = "ingrediente-psi-historias-tematicas-queue.json"
GRAPH      = "https://graph.instagram.com/v21.0"
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def publicar_una_historia(url):
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "STORIES",
        "image_url": url,
        "access_token": TOKEN,
    }, timeout=120)
    j = r.json()
    if "id" not in j:
        log(f"  ERROR creando container: {j}")
        return False
    creation_id = j["id"]
    time.sleep(3)
    for i in range(5):
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish",
                          data={"creation_id": creation_id, "access_token": TOKEN},
                          timeout=120)
        j = r.json()
        if "id" in j:
            log(f"  slide OK, Story ID: {j['id']}")
            return True
        log(f"  intento publish {i} fallo ({j}), reintento en 10s")
        time.sleep(10)
    return False


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        cola = json.load(f)

    ahora = datetime.datetime.now(datetime.timezone.utc)
    vencidas = []
    for i, p in enumerate(cola):
        if p["status"] != "pending":
            continue
        if datetime.datetime.fromisoformat(p["publicar_en"]) <= ahora:
            vencidas.append((p["publicar_en"], i, p))

    if not vencidas:
        log("No hay series tematicas vencidas para publicar todavia.")
        return

    vencidas.sort(key=lambda t: t[0])
    _, idx, nxt = vencidas[0]

    if not hay_cupo():
        log(f"Cupo diario alcanzado ({publicados_hoy()}/{CUPO_MAX} entre posteos+historias+frases+series). Se reintenta manana.")
        return

    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        espera = random.randint(0, 18 * 60)
        log(f"Esperando {espera // 60} min {espera % 60} s para no publicar siempre a la misma hora exacta.")
        time.sleep(espera)

    ya_hechos = nxt.get("slides_publicados", 0)
    log(f"Serie a publicar: {nxt['serie']} | {len(nxt['archivos'])} slides (ya publicados: {ya_hechos})")

    ok_total = True
    for i, archivo in enumerate(nxt["archivos"]):
        if i < ya_hechos:
            continue
        url = RAW_BASE + archivo
        log(f"Slide {i+1}/{len(nxt['archivos'])}: {url}")
        ok = publicar_una_historia(url)
        if not ok:
            ok_total = False
            cola[idx]["slides_publicados"] = i
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(cola, f, ensure_ascii=False, indent=2)
            log(f"FALLO en el slide {i+1}. Se corta la secuencia aca, se reintenta desde ahi la proxima corrida.")
            break
        time.sleep(5)

    if not ok_total:
        sys.exit(1)

    cola[idx]["status"] = "published"
    cola[idx]["publicado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    log(f"SERIE PUBLICADA OK: {nxt['serie']}")


if __name__ == "__main__":
    main()
