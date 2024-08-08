import enum
from pathlib import Path

API_ROOT_PATH = Path(__file__).parent.parent


class Stage(str, enum.Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
