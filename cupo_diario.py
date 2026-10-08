#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tope diario COMPARTIDO entre las 3 colas de Ingrediente Psi (posteos,
historias y frases). Sin esto, si las tres colas tienen algo pendiente el
mismo dia, la cuenta podria recibir hasta 5 publicaciones en un dia -- mas
de lo que le hizo falta a Diamond para que Instagram le pusiera un
checkpoint el 01-04/10/2026.

CUPO_MAX es el techo duro: ningun dia, sumando las 3 colas, se publica
mas que eso. Si ya se llego al tope, el publicador de turno espera a la
proxima corrida (no se pierde nada, solo se corre un dia).
"""
import datetime
import json
import os

ARG = datetime.timezone(datetime.timedelta(hours=-3))
CUPO_MAX = 4

COLAS = [
    "ingrediente-psi-queue.json",
    "ingrediente-psi-historias-queue.json",
    "ingrediente-psi-frases-queue.json",
]


def hoy_arg():
    return datetime.datetime.now(ARG).date()


def publicados_hoy():
    hoy = hoy_arg().isoformat()
    total = 0
    for nombre in COLAS:
        if not os.path.exists(nombre):
            continue
        with open(nombre, encoding="utf-8-sig") as f:
            cola = json.load(f)
        for item in cola:
            if item.get("status") != "published":
                continue
            pub = item.get("publicado")
            if not pub:
                continue
            try:
                # 'publicado' se guarda en UTC (hora del runner); se pasa a ARG.
                utc = datetime.datetime.strptime(pub, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=datetime.timezone.utc)
                if utc.astimezone(ARG).date().isoformat() == hoy:
                    total += 1
            except ValueError:
                continue
    return total


def hay_cupo():
    return publicados_hoy() < CUPO_MAX
