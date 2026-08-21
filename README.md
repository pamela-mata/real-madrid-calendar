# Calendario del Real Madrid — LaLiga 2026/27

Calendario `.ics` público que se actualiza solo. Te suscribes una vez desde
Google Calendar (o cualquier cliente de calendario) y los cambios de fecha y
horario que publique LaLiga llegan solos, sin volver a importar nada.

## URL de suscripción

```
https://pamela-mata.github.io/real-madrid-calendar/real-madrid.ics
```

En Google Calendar: **Otros calendarios → + → Desde URL** y pega esa dirección.

> Google Calendar refresca los calendarios por URL en su propio ciclo, que suele
> tardar entre unas horas y un par de días. No es configurable desde aquí.

## Fuente de datos

La API pública oficial de LaLiga, la misma que consume
[laliga.com](https://www.laliga.com/clubes/real-madrid/proximos-partidos):

```
https://apim.laliga.com/public-service/api/v1/matches
```

No hay scraping de HTML: se leen los partidos como JSON estructurado.

## Qué contiene cada evento

- **Título:** `⚽ Real Madrid vs FC Barcelona` (local vs visitante).
- **Hora:** almacenada como hora local de Madrid con `TZID=Europe/Madrid`, así
  que tu calendario la convierte solo a tu zona horaria.
- **Descripción:** competición, temporada, jornada y enlace a la fuente oficial.
- **Ubicación:** estadio y ciudad.
- **Disponibilidad:** los eventos se marcan como **ocupado** (`TRANSP:OPAQUE`),
  así que bloquean el hueco frente a "buscar un hueco" y a quien consulte tu
  disponibilidad.
- **Sin alarmas:** los calendarios suscritos ignoran las alarmas del archivo, así
  que cada quien configura sus recordatorios desde su propio cliente.

Cuando LaLiga todavía no ha confirmado el horario, el partido aparece como
**evento de día completo** y la descripción lo dice explícitamente. En cuanto se
confirme la hora, ese mismo evento pasa a tener horario: no se duplica.

## Cómo conserva la temporada completa

La página de "próximos partidos" va retirando los partidos ya jugados. El script
**nunca borra** eventos del `.ics`: lee el archivo existente, lo fusiona con lo
que devuelve la API y solo añade o actualiza. Cada evento usa un `UID` estable
derivado del id de partido de LaLiga, de modo que un cambio de fecha modifica el
evento existente en lugar de crear uno nuevo.

## Frecuencia de actualización

Automática **todos los días a las 14:00 UTC** (08:00 en Ciudad de México). Solo
se crea commit si el `.ics` cambió realmente, así que los días sin novedades no
dejan rastro en el historial.

## Actualización manual

Desde la web: pestaña **Actions → Update Real Madrid calendar → Run workflow**.

Desde la terminal:

```bash
gh workflow run update-calendar.yml
```

## Ejecutar el script localmente

Requiere **Python 3.10 o superior**.

```bash
pip install -r requirements.txt
python scripts/update_calendar.py
```

Escribe o actualiza `real-madrid.ics` en la raíz del repositorio.

## Competiciones

Ahora mismo el calendario cubre **LaLiga EA SPORTS 2026/27** (38 jornadas), que
es lo único que la API tiene publicado para esta temporada. El script ya consulta
también Copa del Rey y Supercopa de España; en cuanto LaLiga las publique tras
los sorteos, entran solas sin tocar el código.
