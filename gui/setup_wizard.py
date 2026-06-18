import threading

import customtkinter as ctk

import config


def _write_env(token: str, player1: str, player2: str):
    """Write credentials to the .env secrets file."""
    content = (
        "# Git Battle — secrets file\n"
        "# NEVER commit this file to git\n"
        "\n"
        f"GITHUB_TOKEN={token}\n"
        f"PLAYER1_USERNAME={player1}\n"
        f"PLAYER2_USERNAME={player2}\n"
    )
    with open(config.ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)


class SetupWizard(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Git Battle — Setup")
        self.geometry("520x480")
        self.resizable(False, False)
        self.configure(fg_color=config.COLORS["bg"])
        self.result = None
        self._build_ui()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="⚔  Git Battle",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=config.COLORS["text_primary"],
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self,
            text="One-time setup — connect your GitHub account",
            text_color=config.COLORS["text_secondary"],
            font=ctk.CTkFont(size=13),
        ).pack(pady=(0, 20))

        card = ctk.CTkFrame(self, fg_color=config.COLORS["surface"], corner_radius=12)
        card.pack(fill="x", padx=30, pady=0)

        def field(parent, label, hint, placeholder, show=""):
            ctk.CTkLabel(
                parent, text=label, anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=config.COLORS["text_primary"],
            ).pack(fill="x", padx=18, pady=(16, 2))
            if hint:
                ctk.CTkLabel(
                    parent, text=hint, anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color=config.COLORS["text_secondary"],
                ).pack(fill="x", padx=18, pady=(0, 4))
            var = ctk.StringVar()
            ctk.CTkEntry(
                parent, textvariable=var, placeholder_text=placeholder,
                show=show, height=36,
            ).pack(fill="x", padx=18, pady=(0, 2))
            return var

        self.token_var = field(
            card,
            "GitHub Personal Access Token",
            "Create at github.com/settings/tokens  (scopes: public_repo, read:user)",
            "ghp_xxxxxxxxxxxxxxxxxxxx",
            show="*",
        )
        self.p1_var = field(
            card,
            "Your GitHub Username",
            "",
            "MithunvelKL",
        )
        self.p1_var.set("MithunvelKL")

        self.p2_var = field(
            card,
            "Competitor's GitHub Username",
            "yeses03",
            "yeses03",
        )

        ctk.CTkFrame(card, height=16, fg_color="transparent").pack()

        self.error_label = ctk.CTkLabel(
            self, text="", text_color=config.COLORS["danger"],
            font=ctk.CTkFont(size=12),
        )
        self.error_label.pack(pady=(12, 4))

        self.save_btn = ctk.CTkButton(
            self,
            text="Start Tracking  ⚔",
            command=self._validate_and_save,
            fg_color="#238636",
            hover_color="#2ea043",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.save_btn.pack(padx=30, fill="x", pady=(0, 24))

    def _validate_and_save(self):
        token = self.token_var.get().strip()
        p1 = self.p1_var.get().strip()
        p2 = self.p2_var.get().strip()

        if not token:
            self.error_label.configure(text="GitHub token is required")
            return
        if not p1 or not p2:
            self.error_label.configure(text="Both usernames are required")
            return
        if p1 == p2:
            self.error_label.configure(text="Usernames must be different")
            return

        self.save_btn.configure(state="disabled", text="Verifying token...")
        self.error_label.configure(text="")

        def verify():
            from api.github_client import GitHubClient
            client = GitHubClient(token)
            ok = client.verify_token()
            if ok:
                _write_env(token, p1, p2)
                self.result = {"token": token, "player1": p1, "player2": p2}
                self.after(0, self.destroy)
            else:
                self.after(0, lambda: (
                    self.error_label.configure(text="Token verification failed — check the token and try again"),
                    self.save_btn.configure(state="normal", text="Start Tracking  ⚔"),
                ))

        threading.Thread(target=verify, daemon=True).start()
