import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_V2_URL = os.environ.get('API_V2_URL')
CIDC_WORKING_DIR = os.path.join(Path.home(), '.cidc')
TOKEN_CACHE_PATH = os.path.join(CIDC_WORKING_DIR, 'id_token')
UPLOAD_WORKSPACE = os.path.join(CIDC_WORKING_DIR, 'upload-workspace')
