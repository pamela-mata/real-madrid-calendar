#!/usr/bin/env python3
"""
Genera y actualiza `real-madrid.ics` con los partidos del Real Madrid.

Fuente: API pública oficial de LaLiga (la misma que consume laliga.com).

    https://apim.laliga.com/public-service/api/v1/matches

Reglas de fusión (merge), no de regeneración:

  * El .ics existente se lee y se conserva. Los partidos ya jugados que LaLiga
    deja de publicar en "próximos partidos" NO se borran.
  * El UID de cada evento se deriva del id numérico de partido de LaLiga, que es
    estable durante toda la temporada. Un cambio de fecha u hora actualiza el
    mismo evento en lugar de crear un duplicado.
  * Si LaLiga aún no ha confirmado el horario (campo `time` a null) el evento se
    crea como evento de día completo y se marca como provisional en DESCRIPTION.
    Cuando después aparece el horario, ese mismo UID pasa a evento con hora.
  * Nunca se inventa un horario.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar, Event, Timezone

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

API_BASE = "https://apim.laliga.com/public-service/api/v1"

# Clave de suscripción pública del portal laliga.com. No es un secreto: viaja en
# el bundle JavaScript que sirve la propia web a cualquier visitante.
API_KEY = os.environ.get("LALIGA_API_KEY", "c13c3a8e2f6b46da9c5c425cf61fab3e")

TEAM_SLUG = "real-madrid"
TEAM_NAME = "Real Madrid"
SEASON = "2026/27"

# Competiciones a consultar. Las que aún no existen en la API (sorteo sin
# celebrar) devuelven 404 y simplemente se omiten; en cuanto LaLiga las publique
# entran solas en el calendario sin tocar el script.
SUBSCRIPTION_SLUGS = [
    "laliga-easports-2026",
    "copa-del-rey-2026",
    "supercopa-de-espana-2026",
]

SOURCE_URL = "https://www.laliga.com/clubes/real-madrid/proximos-partidos"

MADRID = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")

ICS_PATH = Path(__file__).resolve().parent.parent / "real-madrid.ics"

CALENDAR_NAME = f"Real Madrid {SEASON}"
PRODID = "-//real-madrid-calendar//LaLiga fixtures//ES"
UID_DOMAIN = "real-madrid-calendar.github"

MATCH_DURATION = timedelta(hours=2)

# VTIMEZONE compacta y estable para Europe/Madrid. Se incrusta literal en vez de
# derivarla de la base tzdata porque esa versión ocupa ~60 líneas de RDATE y
# ensuciaría el diff de cada commit automático.
MADRID_VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Madrid
X-LIC-LOCATION:Europe/Madrid
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""

REQUEST_TIMEOUT = 30

PENDING_NOTE = "Horario pendiente de confirmación por LaLiga."
PROVISIONAL_NOTE = (
    "Fecha provisional: LaLiga puede modificar el día y la hora de este partido."
)


# --------------------------------------------------------------------------- #
# Descarga
# --------------------------------------------------------------------------- #


def fetch_matches(subscription: str) -> list[dict[str, Any]]:
    """Devuelve los partidos del equipo en una competición. [] si no existe."""
    matches: list[dict[str, Any]] = []
    offset = 0
    limit = 100

    while True:
        response = requests.get(
            f"{API_BASE}/matches",
            params={
                "subscriptionSlug": subscription,
                "teamSlug": TEAM_SLUG,
                "limit": limit,
                "offset": offset,
                "orderField": "date",
                "orderType": "asc",
            },
            headers={
                "Ocp-Apim-Subscription-Key": API_KEY,
                "Accept": "application/json",
                "Content-Language": "es",
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 404:
            print(f"  · {subscription}: aún no publicada en la API, se omite")
            return []

        response.raise_for_status()
        payload = response.json()
        page = payload.get("matches") or []
        matches.extend(page)

        total = payload.get("total", len(matches))
        offset += limit
        if len(page) < limit or offset >= total:
            break

    print(f"  · {subscription}: {len(matches)} partidos")
    return matches


def fetch_all_matches() -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    errors: list[str] = []

    for subscription in SUBSCRIPTION_SLUGS:
        try:
            matches.extend(fetch_matches(subscription))
        except requests.RequestException as exc:
            errors.append(f"{subscription}: {exc}")
            print(f"  ! {subscription}: error de red ({exc})", file=sys.stderr)

    if not matches:
        detail = "; ".join(errors) if errors else "la API no devolvió partidos"
        raise SystemExit(f"No se pudo obtener ningún partido de LaLiga ({detail})")

    return matches


# --------------------------------------------------------------------------- #
# Traducción partido -> evento
# --------------------------------------------------------------------------- #


def team_label(team: dict[str, Any] | None) -> str:
    if not team:
        return "Por determinar"
    for key in ("nickname", "boundname", "name"):
        value = (team.get(key) or "").strip()
        if value:
            return value
    return "Por determinar"


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def match_uid(match: dict[str, Any]) -> str:
    return f"laliga-match-{match['id']}@{UID_DOMAIN}"


def build_event(match: dict[str, Any]) -> Event | None:
    home = team_label(match.get("home_team"))
    away = team_label(match.get("away_team"))

    kickoff = parse_utc(match.get("time"))
    provisional_day = parse_utc(match.get("date"))

    if kickoff is None and provisional_day is None:
        # Sin fecha alguna no hay evento que crear; no se inventa nada.
        return None

    competition = (match.get("competition") or {}).get("name") or "LaLiga"
    gameweek = match.get("gameweek") or {}
    venue = match.get("venue") or {}

    event = Event()
    event.add("uid", match_uid(match))
    event.add("summary", f"⚽ {home} vs {away}")
    event.add("dtstamp", datetime.now(tz=UTC))

    description_lines = [f"{competition} {SEASON}"]
    if gameweek.get("name"):
        description_lines.append(str(gameweek["name"]))

    if kickoff is not None:
        # El horario oficial se almacena en hora local de Madrid con TZID, para
        # que Google Calendar lo convierta solo a la zona de quien lo lee.
        start_local = kickoff.astimezone(MADRID)
        event.add("dtstart", start_local)
        event.add("dtend", start_local + MATCH_DURATION)
    else:
        assert provisional_day is not None
        day: date = provisional_day.date()
        event.add("dtstart", day)
        event.add("dtend", day + timedelta(days=1))
        description_lines.append("")
        description_lines.append(PENDING_NOTE)
        description_lines.append(PROVISIONAL_NOTE)

    if venue.get("name"):
        location = venue["name"]
        if venue.get("city"):
            location = f"{location}, {venue['city']}"
        event.add("location", location)

    description_lines.extend(["", "Fuente oficial: LaLiga", SOURCE_URL])
    event.add("description", "\n".join(description_lines))

    if match.get("slug"):
        event.add(
            "url",
            f"https://www.laliga.com/partido/{match['slug']}",
        )

    # OPAQUE = el evento cuenta como tiempo ocupado en el calendario.
    event.add("transp", "OPAQUE")
    return event


# --------------------------------------------------------------------------- #
# Fusión con el .ics existente
# --------------------------------------------------------------------------- #


def load_existing_events() -> dict[str, Event]:
    if not ICS_PATH.exists():
        return {}

    try:
        calendar = Calendar.from_ical(ICS_PATH.read_bytes())
    except ValueError as exc:
        print(f"  ! .ics existente ilegible, se regenera desde cero ({exc})",
              file=sys.stderr)
        return {}

    events: dict[str, Event] = {}
    for component in calendar.walk("VEVENT"):
        uid = str(component.get("uid") or "")
        if uid:
            events[uid] = component
    return events


def event_signature(event: Event) -> tuple:
    """Campos que definen si un evento cambió, ignorando DTSTAMP."""
    keys = (
        "SUMMARY",
        "DTSTART",
        "DTEND",
        "DESCRIPTION",
        "LOCATION",
        "URL",
        "TRANSP",
    )
    return tuple(
        event.get(key).to_ical() if event.get(key) is not None else None
        for key in keys
    )


def sort_key(event: Event) -> tuple[int, str]:
    value = event.get("dtstart")
    if value is None:
        return (1, "")
    start = value.dt
    if isinstance(start, datetime):
        return (0, start.astimezone(UTC).isoformat())
    return (0, datetime(start.year, start.month, start.day, tzinfo=UTC).isoformat())


def build_calendar(events: Iterable[Event]) -> Calendar:
    calendar = Calendar()
    calendar.add("prodid", PRODID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", CALENDAR_NAME)
    calendar.add("x-wr-caldesc", f"Partidos del {TEAM_NAME}. Fuente: LaLiga.")
    calendar.add("x-wr-timezone", "Europe/Madrid")
    # Sin VALARM: los calendarios suscritos en Google Calendar ignoran las alarmas
    # del archivo y cada persona configura las suyas desde la interfaz.

    # La VTIMEZONE va antes de los eventos que la referencian.
    calendar.add_component(Timezone.from_ical(MADRID_VTIMEZONE))

    for event in sorted(events, key=sort_key):
        calendar.add_component(event)

    return calendar


def main() -> int:
    print(f"Consultando la API de LaLiga para {TEAM_NAME} ({SEASON})…")
    matches = fetch_all_matches()

    existing = load_existing_events()
    merged: dict[str, Event] = dict(existing)

    added = updated = pending = 0
    seen: set[str] = set()

    for match in matches:
        event = build_event(match)
        if event is None:
            continue

        uid = str(event["uid"])
        seen.add(uid)
        if event.get("dtstart") is not None and not isinstance(
            event["dtstart"].dt, datetime
        ):
            pending += 1

        previous = existing.get(uid)
        if previous is None:
            added += 1
        elif event_signature(previous) != event_signature(event):
            updated += 1
        else:
            # Sin cambios: se conserva el DTSTAMP anterior para no generar
            # diffs (ni commits) espurios en cada ejecución.
            event["dtstamp"] = previous["dtstamp"]

        merged[uid] = event

    # Partidos que ya no aparecen en la API (LaLiga los retira al jugarse) pero
    # que siguen en el .ics: nunca se borran.
    preserved = len(set(existing) - seen)

    calendar = build_calendar(merged.values())
    ICS_PATH.write_bytes(calendar.to_ical())

    print(f"\nPartidos en la API:        {len(matches)}")
    print(f"Eventos nuevos:            {added}")
    print(f"Eventos actualizados:      {updated}")
    print(f"Sin horario confirmado:    {pending}")
    print(f"Conservados del .ics:      {preserved} (ya no listados por LaLiga)")
    print(f"Total en {ICS_PATH.name}: {len(merged)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
