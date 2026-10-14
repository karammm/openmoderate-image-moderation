# API reference

Generated from the docstrings. Everything on this page is public API.

::: openmoderate.Moderator

## Results

::: openmoderate.ModerationResult

::: openmoderate.Label

::: openmoderate.LabelSpec

## Videos

::: openmoderate.VideoModerationResult

::: openmoderate.VideoSegment

## Configuration

::: openmoderate.ModerationConfig

::: openmoderate.Category

## Trained heads

::: openmoderate.LinearHead

## Errors

::: openmoderate.ImageLoadError

::: openmoderate.VideoLoadError

## Framework integrations

::: openmoderate.integrations

::: openmoderate.integrations.fastapi
    options:
      members: [moderated, moderated_files]

::: openmoderate.integrations.flask
    options:
      members: [moderate_uploads, OpenModerate]

::: openmoderate.integrations.django
    options:
      members: [ModerationValidator, ModerationMiddleware]
