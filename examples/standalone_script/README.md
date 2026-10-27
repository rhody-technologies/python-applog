# Standalone script example

The smallest possible integration: one `applog.configure()` call at the top
of `main()`, then plain `logging` calls everywhere else.

## Run it

```bash
pip install -e .            # from the repo root, installs applog
python examples/standalone_script/app.py
```

## What to look at

- `app.py` calls `applog.configure(...)` exactly once, in `main()`.
- Every other function just does `logging.getLogger(__name__)` and logs
  normally — no awareness of applog beyond that one `import`.
- Output goes to `standalone-example.jsonl` next to this script, and
  (because `console=True`) is also echoed to stderr so you can watch it
  run.
- The `logger.exception(...)` call demonstrates the standardized exception
  shape: look for the `"exception"` object in that line.
