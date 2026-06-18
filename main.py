import os
import sys

import customtkinter as ctk
from dotenv import load_dotenv

import config


def load_config() -> dict | None:
    load_dotenv(config.ENV_FILE, override=True)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    player1 = os.getenv("PLAYER1_USERNAME", "").strip()
    player2 = os.getenv("PLAYER2_USERNAME", "").strip()
    if token and player1 and player2:
        return {"token": token, "player1": player1, "player2": player2}
    return None


def run_setup() -> dict | None:
    """Show first-run wizard and return the saved config, or None if cancelled."""
    root = ctk.CTk()
    root.withdraw()

    from gui.setup_wizard import SetupWizard
    wizard = SetupWizard(root)
    root.wait_window(wizard)
    result = wizard.result
    root.destroy()
    return result


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    cfg = load_config()

    if cfg is None:
        cfg = run_setup()
        if cfg is None:
            sys.exit(0)

    from gui.app import App
    app = App(cfg)
    app.mainloop()


if __name__ == "__main__":
    main()
