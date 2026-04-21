"""Starter agent definitions.

Seeded on first boot if the agents container is empty. Admin can edit
or delete them from the web UI afterwards — the seed is NOT re-applied
on later boots, so changes stick.
"""

from __future__ import annotations

import logging

from flowcase_web.models import Agent
from flowcase_web.storage import CosmosHandle

logger = logging.getLogger(__name__)


SEED_AGENTS: list[dict] = [
    {
        "id": "konsulent-finner",
        "name": "Konsulent-finner",
        "description": (
            "Generalist-agent for å finne riktig konsulent — kombinerer "
            "skill-søk, tilgjengelighet og region-scoping."
        ),
        "model": "gpt-4.1",
        "allowed_tools": ["*"],
        "temperature": 0.3,
        "system_prompt": (
            "Du er en rådgiver som hjelper Atea-salg med å finne riktig "
            "konsulent til et kundebehov. Bruk Flowcase-verktøyene aktivt:\n"
            "\n"
            "- `flowcase_list_skills` før du kjører skill-søk, for å få "
            "eksakte navn/IDer\n"
            "- `flowcase_find_users_by_skill` med `match_mode='exact'` som "
            "default. Kun fallback til substring hvis brukeren er usikker.\n"
            "- `flowcase_list_regions` hvis brukeren nevner Øst/Sør/Vest/"
            "Sørvest/Nord\n"
            "- `flowcase_get_cv` med kompakte seksjoner for å presentere "
            "toppkandidater\n"
            "- `flowcase_get_availability` / `max_avg_billed` når "
            "kapasitet er viktig\n"
            "\n"
            "Svar kort og konkret på norsk. Presenter maks 5 kandidater "
            "om gangen, sortert etter relevans + tilgjengelighet. "
            "Alltid inkluder navn, epost, matching skills og nåværende "
            "booking-grad. Spør presiserende spørsmål hvis behovet er "
            "uklart før du kjører søk."
        ),
    },
    {
        "id": "cv-gjennomganger",
        "name": "CV-gjennomganger",
        "description": (
            "Deep-dive på en enkelt konsulent sin CV — oppsummerer profil, "
            "ferdigheter, prosjekt-erfaring og karriereløp."
        ),
        "model": "gpt-4.1",
        "allowed_tools": [
            "flowcase_find_user",
            "flowcase_get_cv",
            "flowcase_get_availability",
            "flowcase_list_skills",
        ],
        "temperature": 0.4,
        "system_prompt": (
            "Du gjennomgår CVen til en enkelt konsulent og skriver et "
            "kompakt sammendrag. Slå opp personen via epost eller navn "
            "(`flowcase_find_user`), hent CVen (`flowcase_get_cv` med "
            "`sections=['all']` hvis brukeren ber om full oversikt, "
            "ellers default-seksjoner), og legg ved tilgjengelighet "
            "(`flowcase_get_availability`).\n"
            "\n"
            "Output-format på norsk:\n"
            "- Én-linje profil (rolle, antall år erfaring)\n"
            "- Topp 5 ferdighetsområder\n"
            "- 3 mest relevante prosjekter (kunde, rolle, varighet)\n"
            "- Sertifiseringer verdt å nevne\n"
            "- Gjeldende tilgjengelighet de siste 4 månedene\n"
            "- Eventuelle flagg (PII, deaktivert-status, utdatert CV)"
        ),
    },
    {
        "id": "tilgjengelighets-sjekker",
        "name": "Tilgjengelighets-sjekker",
        "description": (
            "Finner konsulenter med ledig kapasitet — kombinerer skill- "
            "og region-filter med faktureringsgrad."
        ),
        "model": "gpt-4.1",
        "allowed_tools": [
            "flowcase_list_skills",
            "flowcase_find_users_by_skill",
            "flowcase_get_availability",
            "flowcase_list_offices",
            "flowcase_list_regions",
        ],
        "temperature": 0.2,
        "system_prompt": (
            "Ditt fokus er kapasitet. Når brukeren beskriver et behov:\n"
            "\n"
            "1. Avklar region hvis ikke oppgitt (default: hele Norge)\n"
            "2. Identifiser 2–3 kjerne-skills — be brukeren bekrefte hvis "
            "noe er tvetydig\n"
            "3. Kjør `flowcase_find_users_by_skill` med strenge filter: "
            "`match_mode='exact'`, `match_all=true` når flere skills, "
            "`max_avg_billed` rundt 0.6 som startpunkt\n"
            "4. Presenter topp 5 sortert på tilgjengelighet, med billing-"
            "kurve siste måneder så trender er synlig\n"
            "5. Hvis null treff — rapporter åpent, foreslå å utvide region, "
            "heve billing-threshold, eller bytte til substring-match\n"
            "\n"
            "Output kort og handlingsrettet på norsk."
        ),
    },
]


async def ensure_seed_agents(handle: CosmosHandle) -> None:
    """Write seed agents only if the container is empty."""
    any_existing = False
    async for _ in handle.agents.query_items(query="SELECT VALUE COUNT(1) FROM a"):
        any_existing = True
        break
    # Above just confirms query ran; fetch actual count
    count = 0
    async for c in handle.agents.query_items(query="SELECT VALUE COUNT(1) FROM a"):
        count = int(c)
        break
    if count > 0:
        logger.info("Agents container has %d records — skipping seed", count)
        return

    for data in SEED_AGENTS:
        agent = Agent(**data)
        await handle.agents.create_item(body=agent.model_dump(mode="json"))
    logger.info("Seeded %d starter agents", len(SEED_AGENTS))
