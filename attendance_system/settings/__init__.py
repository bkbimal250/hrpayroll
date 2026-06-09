import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env defaults without overriding real server environment variables.
load_dotenv(BASE_DIR / '.env', override=False)

# Choose settings based on ENVIRONMENT variable
env = os.environ.get('ENVIRONMENT', 'development').lower()

if env == 'production':
    from .prod import *
elif env == 'local':
    from .local import *
else:
    from .dev import *
