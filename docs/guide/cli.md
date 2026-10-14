# Command line

```bash
openmoderate scan ./uploads                      # files, folders (recursive) or URLs
openmoderate scan ./uploads --json               # one JSON object per image
openmoderate scan ./uploads --fail-on-violation  # exit code 1 if anything is flagged (CI, cron)
openmoderate scan img.jpg -t weapons=0.3 --exclude alcohol tobacco
openmoderate categories                          # list categories and thresholds
openmoderate download                            # pre-fetch model weights for offline use
```

Exit codes for `scan`: `0` success, `1` something was flagged (only with `--fail-on-violation`), `2` some files could not be read.
