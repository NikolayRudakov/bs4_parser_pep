from pathlib import Path

MAIN_DOC_URL = "https://docs.python.org/3/"
PEP_URL = "https://peps.python.org/"
BASE_DIR = Path(__file__).parent
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
OUTPUT_CHOICE_ARGUMENTS = ("pretty", "file")
EXPECTED_STATUS = {
    "A": ("Active", "Accepted"),
    "D": ("Deferred",),
    "F": ("Final",),
    "P": ("Provisional",),
    "R": ("Rejected",),
    "S": ("Superseded",),
    "W": ("Withdrawn",),
    "": ("Draft", "Active"),
}
