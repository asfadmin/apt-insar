import os
from argparse import ArgumentParser
from zipfile import ZipFile

import requests
from jinja2 import Template


CHUNK_SIZE = 5242880
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION_IDS = [
    "C1214470488-ASF",  # SENTINEL-1A_SLC
    "C1327985661-ASF",  # SENTINEL-1B_SLC
]
USER_AGENT = "python3 asfdaac/apt-insar"


def get_xml_template():
    with open('topsApp_template.xml', 'r') as t:
        template_text = t.read()
    template = Template(template_text)
    return template


def write_topsApp_xml(reference_granule, secondary_granule):
    data = {
        'reference_granule': reference_granule,
        'secondary_granule': secondary_granule,
    }
    template = get_xml_template()
    rendered = template.render(data)
    with open('topsApp.xml', 'w') as f:
        f.write(rendered)


def download_file(url):
    print(f"\nDownloading granule from {url}")
    local_filename = url.split("/")[-1]
    headers = {"User-Agent": USER_AGENT}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
    return local_filename


def write_netrc_file(username, password):
    netrc_file = os.environ["HOME"] + "/.netrc"
    with open(netrc_file, "w") as f:
        f.write(f"machine urs.earthdata.nasa.gov login {username} password {password}")


def get_download_url(granule):
    print("\nFetching granule information")

    params = {
        "readable_granule_name": granule,
        "provider": "ASF",
        "collection_concept_id": COLLECTION_IDS
    }
    response = requests.get(url=CMR_URL, params=params)
    response.raise_for_status()
    cmr_data = response.json()

    if not cmr_data["feed"]["entry"]:
        return None

    entry = cmr_data["feed"]["entry"][0]
    for product in cmr_data["feed"]["entry"][0]["links"]:
        if "data" in product["rel"]:
            return product["href"]

    return None


if __name__ == "__main__":
    parser = ArgumentParser(description="Sentinel-1 InSAR using ISCE")
    parser.add_argument("--reference-granule", "-r", type=str, help="Reference granule name.", required=True)
    parser.add_argument("--secondary-granule", "-s", type=str, help="Secondary granule name.", required=True)
    parser.add_argument("--username", "-u", type=str, help="Earthdata Login username.")
    parser.add_argument("--password", "-p", type=str, help="Earthdata Login password.")
    args = parser.parse_args()

    write_netrc_file(args.username, args.password)

    reference_url = get_download_url(args.reference_granule)
    reference_file = download_file(reference_url)
    with ZipFile(reference_file, 'r') as zip_handle:
        zip_handle.extractall()
    os.unlink(reference_file)

    secondary_url = get_download_url(args.secondary_granule)
    secondary_file = download_file(secondary_url)
    with ZipFile(secondary_file, 'r') as zip_handle:
        zip_handle.extractall()
    os.unlink(secondary_file)

    write_topsApp_xml(args.reference_granule, args.secondary_granule)
