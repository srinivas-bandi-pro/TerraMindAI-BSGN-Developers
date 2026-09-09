"""Direct terminal entry point for the AgriSmart AI application.

Run from the VS Code integrated terminal with: ``python main.py``.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
