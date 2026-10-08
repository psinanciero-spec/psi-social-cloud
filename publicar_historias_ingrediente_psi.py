#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INGREDIENTE PSI - Publicador de historias en la nube (GitHub Actions).

Cada historia reusa la imagen del posteo (ya en 1080x1920, sin texto ni pie)
y se publica aprox. 3 semanas despues de ese posteo, nunca el mismo dia.
Igual que el publicador de posteos: solo publica si ya vencio, nunca mas de
una por corrida.
"""
import datetime
import json
import os
import random
import sys
import time

import requests

TOKEN      = os.environ["PSI_KREA_TOKEN"]
IG_USER_ID = "27949964061276820"
QUEUE_FILE = "ingrediente-psi-historias-queue.json"
GRAPH      = "https://graph.instagram.com/v21.0"
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        cola = json.load(f)

    ahora = datetime.datetime.now(datetime.timezone.utc)

    vencidas = []
    for h in cola:
        if h["status"] != "pending":
            continue
        publicar_en = datetime.datetime.fromisoformat(h["publicar_en"])
        if publicar_en <= ahora:
            vencidas.append((publicar_en, h))

    if not vencidas:
        log("No hay historias vencidas para publicar todavia.")
        return

    vencidas.sort(key=lambda t: t[0])
    _, nxt = vencidas[0]

    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        espera = random.randint(0, 18 * 60)
        log(f"Esperando {espera // 60} min {espera % 60} s para no publicar siempre a la misma hora exacta.")
        time.sleep(espera)

    url = RAW_BASE + nxt["archivo"]
    log(f"Historia a publicar: dia {nxt['dia']} | {url}")

    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "STORIES",
        "image_url": url,
        "access_token": TOKEN,
    }, timeout=120)
    j = r.json()
    if "id" not in j:
        log(f"ERROR creando container de historia: {j}"); sys.exit(1)
    creation_id = j["id"]
    log(f"  Creation ID: {creation_id}")
    time.sleep(3)

    published = False
    for i in range(6):
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish",
                          data={"creation_id": creation_id, "access_token": TOKEN},
                          timeout=120)
        j = r.json()
        if "id" in j:
            log(f"PUBLICADA OK: dia {nxt['dia']} | Story ID: {j['id']}")
            published = True
            break
        log(f"  Intento publish {i} fallo ({j}), reintento en 15s")
        time.sleep(15)

    if not published:
        log(f"FALLO la publicacion de la historia del dia {nxt['dia']}. Se reintenta la proxima corrida.")
        sys.exit(1)

    for x in cola:
        if x["dia"] == nxt["dia"]:
            x["status"] = "published"
            x["publicado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    quedan = sum(1 for x in cola if x["status"] == "pending")
    log(f"Cola actualizada. Historias pendientes: {quedan}")


if __name__ == "__main__":
    main()
