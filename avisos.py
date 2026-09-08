#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisa que no se este por cortar la publicacion, y avisa antes de que pase.

Existe porque las dos veces que se corto la publicacion nadie se entero: el
workflow falla en silencio y la cuenta queda muerta. A Psi Financiero le paso un
mes entero por un token vencido.

Mira dos cosas:
  1. Cuantos posteos quedan en cada cola.
  2. Si los tokens siguen vivos, y cuantos dias faltan para que haya que renovarlos.

Imprime una linea por problema. Si no hay problemas no imprime nada, y el
workflow no abre ningun issue.
"""
import datetime
import io
import json
import os
import sys

import requests

HOY = datetime.date.today()

# Cuando quedan menos que esto, hay que recargar.
# Solo las dos cuentas que le importan al usuario. Psi Krea queda afuera a
# proposito: no la esta trabajando y avisar por ella era ruido.
COLAS = [
    ("Diamond reels (@diamondcleaning.gc)", "diamond-queue.json", 5, 15),
    ("Psi Financiero carruseles", "feed-queue.json", 1, 4),
    ("Psi Financiero reels", "psi-reels-queue.json", 1, 4),
]

TOKENS = [
    ("DIAMOND_IG_TOKEN", "Diamond (@diamondcleaning.gc)", "2026-10-15"),
    ("PSI_FIN_TOKEN", "Psi Financiero (@psi.financiero)", "2026-10-25"),
]

DIAS_AVISO = 12   # avisa con margen para que no llegue justo

problemas = []

# ---- Colas ----
for nombre, archivo, porDia, minimo in COLAS:
    if not os.path.exists(archivo):
        continue
    with io.open(archivo, encoding="utf-8-sig") as f:
        cola = json.load(f)
    quedan = sum(1 for x in cola if x.get("status") == "pending")
    dias = quedan // porDia if porDia else quedan
    if quedan <= minimo:
        problemas.append(
            "**%s**: quedan %d posteos (%d dias). Recargar la cola."
            % (nombre, quedan, dias))

# ---- Tokens ----
for env, nombre, renovar in TOKENS:
    token = os.environ.get(env)
    if not token:
        continue
    try:
        r = requests.get("https://graph.instagram.com/v21.0/me",
                         params={"fields": "id,username", "access_token": token},
                         timeout=30)
        if "username" not in r.json():
            problemas.append(
                "**%s**: el token NO SIRVE MAS. No se esta publicando nada. "
                "Hay que reautorizar y actualizar el secret `%s`." % (nombre, env))
            continue
    except requests.RequestException as e:
        problemas.append("**%s**: no se pudo chequear el token (%s)." % (nombre, e))
        continue

    if renovar:
        faltan = (datetime.date.fromisoformat(renovar) - HOY).days
        if faltan <= DIAS_AVISO:
            problemas.append(
                "**%s**: el token vence en %d dias (%s). Renovarlo antes o la "
                "cuenta deja de publicar sin avisar." % (nombre, faltan, renovar))

if problemas:
    print("\n".join("- " + p for p in problemas))
    sys.exit(0)
