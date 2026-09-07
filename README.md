# Psi Social Cloud

Publicación automática en la nube (GitHub Actions). No depende de ninguna PC encendida.

## Reels en @psi.krea

- Videos cortos de YouTube republicados como Reels, con @psi.financiero como colaborador.
- Corre 2 veces por día: **09:00 y 21:00 hora Argentina**.
- Cada corrida publica el **próximo video pendiente** de `reels-queue.json`.
- Pie obligatorio: `Comenta "Mas"...` + crédito al autor original.

### Cómo agregar más videos
1. Poné el `.mp4` (convertido a H.264, <90s) en `videos/`.
2. Agregá una entrada en `reels-queue.json` con `status: "pending"`.
3. Commit + push. El sistema lo publica solo en el próximo horario.

### Correr a mano
Actions → "Psi Krea - Publicar Reels" → Run workflow.

## Secrets necesarios
- `PSI_KREA_TOKEN` — token long-lived de Instagram Graph API de @psi.krea.

El token vence cada 60 días: renovar con el endpoint `refresh_access_token` y actualizar el secret.

---

## Reels en @diamondcleaning.gc (Diamond Cleaning)

Otro cliente, mismo repo. Archivos propios: `publicar_diamond.py`, `diamond-queue.json`,
carpeta `diamond/` y workflow `diamond.yml`. Secret propio: `DIAMOND_IG_TOKEN`.

**4 reels por día, hora de Gold Coast** (UTC+10, Queensland no tiene horario de verano):
**08:00 · 12:00 · 16:00 · 19:30**.

### Está partido en dos a propósito

| Dónde | Qué hace | Cuándo |
|---|---|---|
| La PC (`ADS\preparar_diamond.ps1`) | Baja los videos de YouTube, los subtitula, los comprime y **les escribe el pie**. | Una vez por semana |
| La nube (`diamond.yml`) | Agarra el próximo pendiente y lo publica. No calcula nada. | 4 veces por día, sola |

La parte pesada se queda en la PC porque en los runners de GitHub yt-dlp se come el
bloqueo de YouTube y whisper por CPU es lento.

### El pie viene ya escrito

Cada entrada de `diamond-queue.json` trae su `caption` completo. **La nube no lo arma.**

Es la corrección de un bug real: antes se armaba en el momento con un contador
compartido, y cuando dos corridas caían juntas las dos leían el mismo número y
publicaban el mismo texto. El 02/09/2026 salieron dos reels idénticos con 21 segundos
de diferencia.

Cada video se lleva **una lección propia** de `ADS\diamond-copy.json` que no se repite
en toda la cola: cómo se limpia eso y por qué funciona así. El argumento comercial, el
crédito y los hashtags rotan aparte.

```
Lección de limpieza, distinta en cada video

Por qué elegirnos + presupuesto por WhatsApp

Crédito al creador, aclarando que no trabaja para nosotros

Hashtags
```

**Sin emojis, nunca.** "Insured" se puede usar, "bonded" no.

### Qué videos entran

Solo limpieza real. Quedan afuera reviews de producto, vlogs, hauls de ropa,
presentaciones personales, decoración, alfombras de auto y limpieza comercial.
Lista negra en `ADS\diamond-videos\videos_excluidos.json`.

Subtítulo obligatorio: si el video ya trae el texto quemado del autor se sube tal cual
(nunca encimar dos); si no trae, se subtitula; si no se puede, no se publica.

### Recargar la cola

```powershell
cd C:\Users\nicom\Desktop\ADS
.\preparar_diamond.ps1 -Cantidad 40 -Push
```

Cuando quedan menos de 4 pendientes, el log de Actions avisa.
