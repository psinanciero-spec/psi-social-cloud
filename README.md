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
