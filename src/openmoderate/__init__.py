"""openmoderate — open-source image content moderation."""

from openmoderate.categories import DEFAULT_CATEGORIES, Category
from openmoderate.config import ModerationConfig
from openmoderate.moderator import Moderator
from openmoderate.result import Label, ModerationResult

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_CATEGORIES",
    "Category",
    "Label",
    "ModerationConfig",
    "ModerationResult",
    "Moderator",
    "__version__",
]
