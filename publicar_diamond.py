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
import datetime
import hashlib
import json
import os
import random
import sys
import time

import requests

# Gold Coast (Queensland) no tiene horario de verano: siempre UTC+10.
GC = datetime.timezone(datetime.timedelta(hours=10))


def hoy_gc():
    return datetime.datetime.now(GC).date()


def cupo_del_dia(fecha):
    """Cuantos reels toca hoy. Varia solo entre 3 y 6 en vez de ser 5 clavados.

    Publicar exactamente 5 por dia a la misma hora, todos los dias del año, es lo
    que hace que una cuenta parezca un bot aunque cada pieza este bien hecha. El
    numero sale del dia con una semilla fija, asi todas las corridas de la misma
    jornada calculan el MISMO cupo sin necesidad de guardarlo en ningun lado.
    """
    semilla = int(hashlib.md5(fecha.isoformat().encode()).hexdigest()[:8], 16)
    r = random.Random(semilla)
    if fecha.weekday() == 6:        # domingo, la gente publica menos
        return r.choice([2, 3, 3, 4])
    if fecha.weekday() == 5:        # sabado
        return r.choice([3, 4, 4, 5])
    return r.choice([4, 4, 5, 5, 5, 6])


def publicados_hoy(cola):
    hoy = hoy_gc().isoformat()
    n = 0
    for x in cola:
        p = x.get("publicado")
        if not p:
            continue
        try:
            # 'publicado' se guarda en UTC; se pasa a hora Gold Coast.
            utc = datetime.datetime.strptime(p, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=datetime.timezone.utc)
            if utc.astimezone(GC).date().isoformat() == hoy:
                n += 1
        except ValueError:
            continue
    return n

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

    # --- Cuanto va hoy ---
    cupo = cupo_del_dia(hoy_gc())
    ya = publicados_hoy(cola)
    log("Hoy (%s) el cupo es %d y van %d." % (hoy_gc(), cupo, ya))
    if ya >= cupo:
        log("Cupo cumplido, esta corrida no publica.")
        return

    # --- Ruido en la hora ---
    # Los cron son fijos y a la larga dejan una huella de bot: 08:00:04, 11:00:06,
    # todos los dias. Esperar un rato al azar corre el posteo dentro de la franja.
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        espera = random.randint(0, 34 * 60)
        log("Esperando %d min %d s para no publicar siempre a la misma hora."
            % (espera // 60, espera % 60))
        time.sleep(espera)

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
