#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INGREDIENTE PSI - Publicador de frases (imagen + pie) en la nube.
3 por dia (08:00, 13:30, 22:00 ARG), independiente del posteo principal
y de las historias. Solo publica si ya vencio su horario, nunca mas de
una por corrida.
"""
import datetime
import json
import os
import sys
import time

import requests

TOKEN      = os.environ["PSI_KREA_TOKEN"]
IG_USER_ID = "27949964061276820"
QUEUE_FILE = "ingrediente-psi-frases-queue.json"
GRAPH      = "https://graph.instagram.com/v21.0"
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


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
        log("No hay frases vencidas para publicar todavia.")
        return

    vencidas.sort(key=lambda t: t[0])
    _, idx, nxt = vencidas[0]

    url = RAW_BASE + nxt["archivo"]
    log(f"Frase a publicar: {nxt['fecha']} {nxt['hora_argentina']} | {url}")

    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "image_url": url,
        "caption": nxt["pie"],
        "access_token": TOKEN,
    }, timeout=120)
    j = r.json()
    if "id" not in j:
        log(f"ERROR creando media: {j}"); sys.exit(1)
    creation_id = j["id"]
    log(f"  Creation ID: {creation_id}")
    time.sleep(5)

    published = False
    for i in range(8):
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish",
                          data={"creation_id": creation_id, "access_token": TOKEN},
                          timeout=120)
        j = r.json()
        if "id" in j:
            log(f"PUBLICADA OK: {nxt['fecha']} {nxt['hora_argentina']} | Post ID: {j['id']}")
            published = True
            break
        log(f"  Intento publish {i} fallo ({j}), reintento en 20s")
        time.sleep(20)

    if not published:
        log("FALLO la publicacion. Se reintenta la proxima corrida.")
        sys.exit(1)

    cola[idx]["status"] = "published"
    cola[idx]["publicado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    quedan = sum(1 for x in cola if x["status"] == "pending")
    log(f"Cola actualizada. Frases pendientes: {quedan}")


if __name__ == "__main__":
    main()
