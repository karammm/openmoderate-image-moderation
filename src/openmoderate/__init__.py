"""openmoderate — open-source image and video content moderation.

Quick start:

```python
from openmoderate import Moderator

result = Moderator().analyze("upload.jpg")
if not result.is_safe:
    print(result.violations)
```

Everything importable from this top-level package is public API and follows semantic
versioning. Submodules that are not re-exported here (and names starting with ``_``) may
change in minor releases.
"""

from openmoderate.categories import DEFAULT_CATEGORIES, SAFE_PROMPTS, Category
from openmoderate.config import PRESETS, ModerationConfig
from openmoderate.io import ImageLoadError
from openmoderate.moderator import LabelSpec, Moderator
from openmoderate.result import Label, ModerationResult
from openmoderate.training.head import LinearHead
from openmoderate.video import VideoLoadError, VideoModerationResult, VideoSegment

__version__ = "1.1.3"

__all__ = [
    "DEFAULT_CATEGORIES",
    "SAFE_PROMPTS",
    "Category",
    "ImageLoadError",
    "Label",
    "LabelSpec",
    "LinearHead",
    "ModerationConfig",
    "ModerationResult",
    "Moderator",
    "PRESETS",
    "VideoLoadError",
    "VideoModerationResult",
    "VideoSegment",
    "__version__",
]
