"""Briefcase desktop app entry point.

Briefcase runs this module as the app startup. It launches the
XinYu Runtime desktop app (FastAPI server + pywebview window).
"""


def main():
    """Launch the XinYu Runtime desktop app."""
    from xinyu_runtime.serving.web import _run_desktop_app_blocking

    _run_desktop_app_blocking()


if __name__ == "__main__":
    main()
