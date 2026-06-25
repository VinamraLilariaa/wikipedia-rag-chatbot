import requests


class WikiMetadataService:

    API = "https://en.wikipedia.org/w/api.php"

    def get_metadata(self, title: str):

        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages|categories",
            "piprop": "original",
            "cllimit": 20,
            "format": "json",
        }

        response = requests.get(
            self.API,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        pages = response.json()["query"]["pages"]

        page = next(iter(pages.values()))

        image = None

        if "original" in page:
            image = page["original"]["source"]

        categories = []

        if "categories" in page:

            categories = [

                c["title"].replace("Category:", "")

                for c in page["categories"]
            ]

        return {

            "image": image,

            "categories": categories,
        }