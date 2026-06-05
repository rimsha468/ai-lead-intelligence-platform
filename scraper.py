import requests


class LeadScraper:

    # ----------------------------
    # INDUSTRY → OSM TAG MAPPING
    # ----------------------------
    INDUSTRY_MAP = {
        # Food
        "restaurant": [("amenity", "restaurant")],
        "cafe": [("amenity", "cafe")],
        "fast_food": [("amenity", "fast_food")],
        "bakery": [("shop", "bakery")],
        "hotel": [("tourism", "hotel")],

        # Health
        "dentist": [("amenity", "dentist")],
        "clinic": [("amenity", "clinic")],
        "hospital": [("amenity", "hospital")],
        "pharmacy": [("amenity", "pharmacy")],
        "veterinary": [("amenity", "veterinary")],

        # Education
        "school": [("amenity", "school")],
        "college": [("amenity", "college")],
        "university": [("amenity", "university")],

        # Finance
        "bank": [("amenity", "bank")],
        "atm": [("amenity", "atm")],

        # Fitness
        "gym": [("leisure", "fitness_centre")],

        # Retail
        "supermarket": [("shop", "supermarket")],
        "convenience_store": [("shop", "convenience")],
        "clothing_store": [("shop", "clothes")],
        "shoe_store": [("shop", "shoes")],
        "electronics_store": [("shop", "electronics")],
        "furniture_store": [("shop", "furniture")],
        "bookstore": [("shop", "books")],
        "jewelry_store": [("shop", "jewelry")],
        "leather_goods": [("shop", "leather")],

        # Automotive
        "car_dealer": [("shop", "car")],
        "car_repair": [("shop", "car_repair")],
        "gas_station": [("amenity", "fuel")],

        # Religious
        "church": [("building", "church")],
        "mosque": [("building", "mosque")],
    }

    # ----------------------------
    # MAIN SEARCH FUNCTION
    # ----------------------------
    def search(self, industry, coords):

        lat, lon = coords

        south, west = lat - 0.15, lon - 0.15
        north, east = lat + 0.15, lon + 0.15

        overpass_url = "https://overpass-api.de/api/interpreter"

        headers = {"User-Agent": "Mozilla/5.0"}

        industry_key = industry.lower()

        tags_list = self.INDUSTRY_MAP.get(
            industry_key,
            [("amenity", industry_key)]
        )

        results = []

        for tag in tags_list:

            if len(tag) == 2:
                key, value = tag
                extra = ""
            else:
                key, value, extra_key, extra_value = tag
                extra = f'["{extra_key}"="{extra_value}"]'

            query = f"""
            [out:json][timeout:25];

            (
              node["{key}"="{value}"]{extra}({south},{west},{north},{east});
              way["{key}"="{value}"]{extra}({south},{west},{north},{east});
              relation["{key}"="{value}"]{extra}({south},{west},{north},{east});
            );

            out center tags;
            """

            try:
                r = requests.post(
                    overpass_url,
                    data=query.encode("utf-8"),
                    headers=headers,
                    timeout=25
                )

                if r.status_code != 200:
                    continue

                data = r.json().get("elements", [])

                for item in data:
                    tags = item.get("tags", {})

                    name = tags.get("name")

                    if name:
                        results.append({
                            "name": name,
                            "type": tags.get("amenity") or tags.get("shop") or tags.get("tourism"),

                            "address": self.build_address(tags),

                            "phone": tags.get("phone") or tags.get("contact:phone"),

                            "website": tags.get("website") or tags.get("contact:website"),

                            "lat": item.get("lat") or item.get("center", {}).get("lat"),
                            "lon": item.get("lon") or item.get("center", {}).get("lon")
                        })

            except:
                continue

        return results

    # ----------------------------
    # ADDRESS BUILDER
    # ----------------------------
    def build_address(self, tags):
        street = tags.get("addr:street", "")
        number = tags.get("addr:housenumber", "")
        city = tags.get("addr:city", "")

        address = f"{number} {street}, {city}".strip(", ")

        return address if address else None