# Calendario del Real Madrid — LaLiga y Champions 2026/27

Calendario `.ics` público que se actualiza solo, con **LaLiga y la Champions
League**. Te suscribes una vez desde Google Calendar (o cualquier cliente de
calendario) y los cambios de fecha y horario llegan solos, sin volver a importar
nada.

## URL de suscripción

```
https://pamela-mata.github.io/real-madrid-calendar/real-madrid.ics
```

En Google Calendar: **Otros calendarios → + → Desde URL** y pega esa dirección.

> Google Calendar refresca los calendarios por URL en su propio ciclo, que suele
> tardar entre unas horas y un par de días. No es configurable desde aquí.

## Fuentes de datos

**Competiciones españolas** — la API pública oficial de LaLiga, la misma que
consume [laliga.com](https://www.laliga.com/clubes/real-madrid/proximos-partidos):

```
https://apim.laliga.com/public-service/api/v1/matches
```

No hay scraping de HTML: se leen los partidos como JSON estructurado.

**Champions League** — la API de LaLiga solo publica competiciones españolas, así
que la fase liga europea vive en la tabla `CHAMPIONS_LEAGUE_PHASE` de
`scripts/update_calendar.py`, con el calendario oficial que la UEFA publicó tras
el sorteo del 27/08/2026 y que
[recogió el club](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/calendarios-del-real-madrid-en-la-primera-fase-de-la-champions-2026-27-29-08-2026).

## Qué contiene cada evento

- **Título:** `⚽ Real Madrid vs FC Barcelona` (local vs visitante).
- **Hora:** almacenada como hora local de Madrid con `TZID=Europe/Madrid`, así
  que tu calendario la convierte solo a tu zona horaria.
- **Descripción:** competición, temporada, jornada y enlace a la fuente oficial.
- **Ubicación:** estadio y ciudad.
- **Disponibilidad:** los partidos con horario confirmado se marcan como
  **ocupado** (`TRANSP:OPAQUE`) y bloquean sus dos horas frente a "buscar un
  hueco" y a quien consulte tu disponibilidad. Los que aún no tienen horario se
  quedan como **libre**, para no bloquear un día entero por un partido cuya hora
  todavía se desconoce; pasan a ocupado solos en cuanto LaLiga confirma la hora.
- **Sin alarmas:** los calendarios suscritos ignoran las alarmas del archivo, así
  que cada quien configura sus recordatorios desde su propio cliente.

Cuando LaLiga todavía no ha confirmado el horario, el partido aparece como
**evento de día completo** y la descripción lo dice explícitamente. En cuanto se
confirme la hora, ese mismo evento pasa a tener horario: no se duplica.

## Cómo conserva la temporada completa

La página de "próximos partidos" va retirando los partidos ya jugados. El script
**nunca borra** eventos del `.ics`: lee el archivo existente, lo fusiona con lo
que devuelve la API y solo añade o actualiza. Cada evento usa un `UID` estable
(el id de partido de LaLiga, o el número de jornada en la Champions), de modo que
un cambio de fecha modifica el evento existente en lugar de crear uno nuevo.

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

- **LaLiga EA SPORTS 2026/27** (38 jornadas), vía API.
- **UEFA Champions League 2026/27**, fase liga (8 jornadas), desde la tabla del
  script.
- **Copa del Rey** y **Supercopa de España**: el script ya las consulta; en
  cuanto LaLiga las publique tras los sorteos, entran solas sin tocar el código.

### Fase liga de la Champions

| Jornada | Partido | Fecha | Hora (Madrid) |
| --- | --- | --- | --- |
| 1 | Real Madrid – Inter de Milán | mar 8 sep 2026 | 21:00 |
| 2 | AS Roma – Real Madrid | mié 14 oct 2026 | 21:00 |
| 3 | Real Madrid – RB Leipzig | mié 21 oct 2026 | 21:00 |
| 4 | AEK de Atenas – Real Madrid | mié 4 nov 2026 | 18:45 |
| 5 | Real Madrid – PSV Eindhoven | mar 24 nov 2026 | 21:00 |
| 6 | Arsenal FC – Real Madrid | mié 9 dic 2026 | 21:00 |
| 7 | Real Madrid – LASK | mar 19 ene 2027 | 21:00 |
| 8 | Shakhtar Donetsk – Real Madrid | mié 27 ene 2027 | 21:00 |

Las horas están guardadas con `TZID=Europe/Madrid`, así que tu calendario las
convierte solo a tu zona horaria.

Como esos ocho partidos no llegan por API, **una modificación de la UEFA se
recoge editando la tabla del script**, no sola. El `UID` de cada evento depende
solo del número de jornada, así que corregir ahí una fecha o una hora actualiza
el evento que ya está en tu calendario en lugar de duplicarlo. Las eliminatorias
se añadirán como filas nuevas cuando se sorteen.
