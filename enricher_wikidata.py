import requests
from functools import lru_cache


class WikidataEnricher:

    def __init__(self):
        self.search_url = "https://www.wikidata.org/w/api.php"
        self.entity_url = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

    # ----------------------------
    # STEP 1: SEARCH ENTITY (CACHED)
    # ----------------------------
    @lru_cache(maxsize=1000)
    def search_entity(self, name):
        if not name:
            return None

        params = {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "limit": 1
        }

        try:
            r = requests.get(self.search_url, params=params, timeout=5)
            data = r.json()

            if "search" in data and len(data["search"]) > 0:
                return data["search"][0]

        except:
            return None

        return None

    # ----------------------------
    # STEP 2: GET ENTITY DETAILS (CACHED)
    # ----------------------------
    @lru_cache(maxsize=1000)
    def get_details(self, qid):
        try:
            r = requests.get(self.entity_url.format(qid), timeout=5)
            data = r.json()

            entity = data["entities"][qid]
            claims = entity.get("claims", {})

            def extract(prop):
                try:
                    return claims[prop][0]["mainsnak"]["datavalue"]["value"]
                except:
                    return None

            return {
                "website": extract("P856"),
                "phone": extract("P1329"),
                "country": extract("P17")
            }

        except:
            return {}

    # ----------------------------
    # STEP 3: MAIN ENRICH FUNCTION (FAST VERSION)
    # ----------------------------
    def enrich(self, lead):
        name = lead.get("name")

        # ----------------------------
        # SMART SKIP (VERY IMPORTANT)
        # ----------------------------
        if lead.get("website") or lead.get("phone"):
            return lead

        entity = self.search_entity(name)

        if not entity:
            return lead

        qid = entity.get("id")

        if not qid:
            return lead

        details = self.get_details(qid)

        # Only update if data exists
        for k, v in details.items():
            if v:
                lead[k] = v

        return lead