# Log — real-madrid-calendar

## Objetivo

Calendario `.ics` suscribible con los partidos del Real Madrid 2026/27 (LaLiga,
Copa del Rey, Supercopa y fase liga de la Champions), actualizado a diario por
GitHub Actions.

## Piezas

- `scripts/update_calendar.py`: consulta la API pública de LaLiga, añade la
  Champions desde una tabla fija en el script y fusiona todo con el `.ics`
  existente sin borrar eventos.
- `.github/workflows/update-calendar.yml`: corre el script todos los días a las
  14:00 UTC y commitea solo si el `.ics` cambió.
- `real-madrid.ics`: el calendario publicado. Lo actualiza el bot, no se edita a mano.

## Historial de sesiones

### 2026-09-26 — Reintentos ante caídas de la API de LaLiga

- **Qué pasó:** la corrida #41 (2026-09-25) falló porque `apim.laliga.com` no
  respondió en 30 s a ninguna de las tres competiciones. El script terminó con
  error a propósito, sin tocar el `.ics`, y la corrida del día siguiente salió
  bien. Fue una falla pasajera de la API, no un bug.
- **Decidido (lo aprobó Pamela, "haz ambos"):**
  - Reintentar cada petición hasta 3 veces con espera creciente (el primero
    de inmediato, luego a los 10 s y a los 20 s) ante timeouts, errores de
    conexión y respuestas 429/5xx. El 404 ("competición aún no publicada") no
    se reintenta. Por qué: evitar la
    notificación de "All jobs have failed" por caídas de unos minutos.
  - Subir `actions/checkout` a v5 y `actions/setup-python` a v6 para quitar la
    advertencia de Node.js 20.
- **Costo aceptado:** si la API de verdad está caída, la corrida tarda unos
  7 min en fallar en lugar de ~2 min.
- **Pendiente de comprobar:** que la primera corrida en GitHub con las actions
  nuevas salga en verde.
- **Por vigilar:** `ubuntu-latest` pasa a Ubuntu 26 desde el 2026-10-19. No se
  espera impacto, pero conviene revisar la primera corrida después de esa fecha.
