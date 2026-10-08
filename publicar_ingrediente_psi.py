#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INGREDIENTE PSI (ex @psi.krea) - Publicador de posteos en la nube (GitHub Actions).

Cada posteo de ingrediente-psi-queue.json tiene su propia fecha y hora exacta
(publicar_en, hora de Argentina). A diferencia de publicar_feed.py / publicar_reel.py,
que publican "el proximo pendiente" apenas corre el cron, esto SOLO publica un
posteo si su hora ya llego: evita que, si el pipeline estuvo caido unos dias, se
descargue todo el backlog junto en una sola corrida (eso fue lo que le gano un
checkpoint a la cuenta de Diamond cuando publicaba en rafaga).

Nunca mas de un posteo por corrida.
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
QUEUE_FILE = "ingrediente-psi-queue.json"
GRAPH      = "https://graph.instagram.com/v21.0"
RAW_BASE   = "https://raw.githubusercontent.com/psinanciero-spec/psi-social-cloud/main/"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def url_publica(path):
    return RAW_BASE + path.replace("\\", "/")


def main():
    with open(QUEUE_FILE, encoding="utf-8-sig") as f:
        cola = json.load(f)

    ahora = datetime.datetime.now(datetime.timezone.utc)

    pendientes_vencidos = []
    for p in cola:
        if p["status"] != "pending":
            continue
        publicar_en = datetime.datetime.fromisoformat(p["publicar_en"])
        if publicar_en <= ahora:
            pendientes_vencidos.append((publicar_en, p))

    if not pendientes_vencidos:
        log("No hay posteos vencidos para publicar todavia.")
        return

    pendientes_vencidos.sort(key=lambda t: t[0])
    _, nxt = pendientes_vencidos[0]

    if not hay_cupo():
        log(f"Cupo diario alcanzado ({publicados_hoy()}/{CUPO_MAX} entre posteos+historias+frases). Se reintenta manana.")
        return

    # Ruido en la hora: el cron es fijo y, a la larga, publicar siempre al
    # mismo segundo deja una huella de bot. Esperar un rato al azar corre
    # la publicacion dentro de la franja (mismo fix que uso Diamond).
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        espera = random.randint(0, 18 * 60)
        log(f"Esperando {espera // 60} min {espera % 60} s para no publicar siempre a la misma hora exacta.")
        time.sleep(espera)

    log(f"Posteo a publicar: dia {nxt['dia']} | {nxt['fecha']} {nxt['hora_argentina']} ARG | {nxt['tipo']}")

    urls = [url_publica(a) for a in nxt["archivos"]]
    for u in urls:
        log(f"  Archivo: {u}")

    if len(urls) == 1:
        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
            "image_url": urls[0],
            "caption": nxt["pie"],
            "access_token": TOKEN,
        }, timeout=120)
        j = r.json()
        if "id" not in j:
            log(f"ERROR creando media: {j}"); sys.exit(1)
        creation_id = j["id"]
    else:
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

        r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": nxt["pie"],
            "access_token": TOKEN,
        }, timeout=120)
        j = r.json()
        if "id" not in j:
            log(f"ERROR container carrusel: {j}"); sys.exit(1)
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
            log(f"PUBLICADO OK: dia {nxt['dia']} | Post ID: {j['id']}")
            published = True
            break
        log(f"  Intento publish {i} fallo ({j}), reintento en 20s")
        time.sleep(20)

    if not published:
        log(f"FALLO la publicacion del dia {nxt['dia']}. Se reintenta la proxima corrida.")
        sys.exit(1)

    for x in cola:
        if x["dia"] == nxt["dia"]:
            x["status"] = "published"
            x["publicado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)

    quedan = sum(1 for x in cola if x["status"] == "pending")
    log(f"Cola actualizada. Pendientes: {quedan}")


if __name__ == "__main__":
    main()
