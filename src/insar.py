import os
import subprocess
from argparse import ArgumentParser
from zipfile import ZipFile
from getpass import getpass

import requests
from jinja2 import Template


CHUNK_SIZE = 5242880
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
QC_URL = "https://qc.sentinel1.eo.esa.int/api/v1/"
COLLECTION_IDS = [
    "C1214470488-ASF",  # SENTINEL-1A_SLC
    "C1327985661-ASF",  # SENTINEL-1B_SLC
]
USER_AGENT = "python3 asfdaac/apt-insar"


def update_xml_with_image_type(input_file):
    xml_file = input_file + ".xml"
    sed_command = 's|</imageFile>|<property name="image_type"><value>unw</value><doc>Image type used for displaying.</doc></property></imageFile>|'
    system_call(["sed", "-i", sed_command, xml_file])


def create_browse(input_file, output_file):
    temp_png_file = os.path.basename(input_file) + ".png"
    update_xml_with_image_type(input_file)
    system_call(["mdx.py", input_file, "-kml", "browse.kml"])
    system_call(["gdal_translate", "-of", "PNG", "-outsize", "0", "1024", temp_png_file, output_file])


def create_geotiff(input_file, output_file, input_band=1):
    temp_file = "tmp.tif"
    system_call(["gdal_translate", "-of", "GTiff", "-a_nodata", "0", "-b", str(input_band), input_file, temp_file])
    system_call(["gdaladdo", "-r", "average", temp_file, "2", "4", "6", "8"])
    system_call(["gdal_translate", "-co", "TILED=YES", "-co", "COPY_SRC_OVERVIEWS=YES", "-co", "COMPRESS=DEFLATE", temp_file, output_file])
    os.unlink(temp_file)


def generate_output_files(start_date, end_date, input_folder="merged", output_folder="/output"):
    name = f"S1-INSAR-{start_date}-{end_date}"
    create_geotiff(f"{input_folder}/phsig.cor.geo", f"{output_folder}/{name}-COR.tif")
    create_geotiff(f"{input_folder}/filt_topophase.unw.geo", f"{output_folder}/{name}-AMP.tif", input_band=1)
    create_geotiff(f"{input_folder}/filt_topophase.unw.geo", f"{output_folder}/{name}-UNW.tif", input_band=2)
    create_browse(f"{input_folder}/filt_topophase.unw.geo", f"{output_folder}/{name}.png")


def system_call(params):
    print(" ".join(params))
    return_code = subprocess.call(params)
    if return_code:
        exit(return_code)


def get_xml_template():
    with open("topsApp_template.xml", "r") as t:
        template_text = t.read()
    template = Template(template_text)
    return template


def write_topsApp_xml(reference_granule, secondary_granule, dem_filename=None):
    template = get_xml_template()
    rendered = template.render(reference_granule=reference_granule, secondary_granule=secondary_granule, dem_filename=dem_filename)
    with open("topsApp.xml", "w") as f:
        f.write(rendered)


def run_topsApp(reference_granule, secondary_granule, dem_filename=None):
    write_topsApp_xml(reference_granule, secondary_granule, dem_filename)
    system_call(["topsApp.py", "--steps", "--end=geocode"])


def get_orbit_url(granule, orbit_type):
    platform = granule[0:3]
    date_time = f"{granule[17:21]}-{granule[21:23]}-{granule[23:25]}T{granule[26:28]}:{granule[28:30]}:{granule[30:32]}"

    params = {
        "product_type": orbit_type,
        "product_name__startswith": platform,
        "validity_start__lt": date_time,
        "validity_stop__gt": date_time,
        "ordering": "-creation_date",
        "page_size": "1",
    }

    response = requests.get(url=QC_URL, params=params)
    response.raise_for_status()
    qc_data = response.json()

    orbit_url = None
    if qc_data["results"]:
        orbit_url = qc_data["results"][0]["remote_url"]
    return orbit_url


def get_orbit_file(granule):
    orbit_url = get_orbit_url(granule, "AUX_POEORB")
    if not orbit_url:
        orbit_url = get_orbit_url(granule, "AUX_RESORB")
    orbit_file = download_file(orbit_url)
    return orbit_file


def unzip(zip_file):
    print(f"Extracting {zip_file}")
    with ZipFile(zip_file, "r") as zip_handle:
        zip_handle.extractall()
    os.unlink(zip_file)


def download_file(url):
    print(f"Downloading {url}")
    local_filename = url.split("/")[-1]
    headers = {"User-Agent": USER_AGENT}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
    return local_filename


def get_download_url(granule):
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

    for product in cmr_data["feed"]["entry"][0]["links"]:
        if "data" in product["rel"]:
            return product["href"]

    return None


def get_granule(granule):
    print(f"\nPreparing {granule}")

    granule_url = get_download_url(granule)
    granule_zip = download_file(granule_url)
    unzip(granule_zip)

    orbit_file = get_orbit_file(granule)

    return {
        "directory": f"{granule}.SAFE",
        "orbit_file": orbit_file,
        "aquisition_date": granule[17:25]
    }


def write_netrc_file(username, password):
    netrc_file = os.environ["HOME"] + "/.netrc"
    with open(netrc_file, "w") as f:
        f.write(f"machine urs.earthdata.nasa.gov login {username} password {password}")


def get_args():
    parser = ArgumentParser(description="Sentinel-1 InSAR using ISCE")
    parser.add_argument("--reference-granule", "-r", type=str, help="Reference granule name.", required=True)
    parser.add_argument("--secondary-granule", "-s", type=str, help="Secondary granule name.", required=True)
    parser.add_argument("--username", "-u", type=str, help="Earthdata Login username.")
    parser.add_argument("--password", "-p", type=str, help="Earthdata Login password.")
    parser.add_argument("--dem", "-d", type=str, help="Digital Elevation Model. ASF automatically selects the best geoid-corrected NED/SRTM DEM.  SRTM uses ISCE's default settings.", choices=["ASF", "SRTM"], default="ASF")
    args = parser.parse_args()
    
    if not args.username:
        args.username = input("\nEarthdata Login username: ")

    if not args.password:
        args.password = getpass("\nEarthdata Login password: ")
        
    return args


if __name__ == "__main__":

    args = get_args()

    write_netrc_file(args.username, args.password)

    reference_granule = get_granule(args.reference_granule)
    secondary_granule = get_granule(args.secondary_granule)
    if args.dem == "ASF":
        dem_filename = None
    else:
        dem_filename = None

    run_topsApp(reference_granule, secondary_granule, dem_filename)

    generate_output_files(reference_granule["aquisition_date"], secondary_granule["aquisition_date"])
