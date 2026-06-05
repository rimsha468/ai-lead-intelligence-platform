import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def extract_emails(url):

    try:
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # ----------------------------
        # EMAIL FROM MAIN PAGE
        # ----------------------------
        emails = set(
            re.findall(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                r.text
            )
        )

        # ----------------------------
        # FIND CONTACT / ABOUT LINKS
        # ----------------------------
        links_to_check = []

        for a in soup.find_all("a", href=True):
            href = a["href"].lower()

            if "contact" in href or "about" in href:
                links_to_check.append(urljoin(url, a["href"]))

        # ----------------------------
        # SCRAPE EXTRA PAGES
        # ----------------------------
        for link in links_to_check[:3]:

            try:
                r2 = requests.get(link, headers=headers, timeout=10)

                if r2.status_code == 200:

                    emails.update(
                        re.findall(
                            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                            r2.text
                        )
                    )

            except:
                continue

        return list(emails)

    except:
        return None