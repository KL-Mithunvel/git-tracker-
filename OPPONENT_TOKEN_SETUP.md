# How to Create Your GitHub Token

Follow these steps to generate a GitHub personal access token so your commits are tracked in the battle.

---

## Step 1 — Sign in to GitHub

Go to [github.com](https://github.com) and sign in to your account.

---

## Step 2 — Open Token Settings

1. Click your **profile picture** in the top-right corner.
2. Select **Settings** from the dropdown.
3. In the left sidebar, scroll down and click **Developer settings**.
4. Click **Personal access tokens** → **Tokens (classic)**.

---

## Step 3 — Generate a New Token

1. Click the **Generate new token** button (top right).
2. Select **Generate new token (classic)**.
3. You may be asked to confirm your password — enter it and continue.

---

## Step 4 — Configure the Token

Fill in the form as follows:

| Field | Value |
|-------|-------|
| **Note** | `git-battle-tracker` (or any name you like) |
| **Expiration** | Set a date beyond the competition end date |
| **Scopes** | Check `public_repo` and `read:user` |

> Only `public_repo` and `read:user` are needed. Do not grant more permissions than these.

---

## Step 5 — Copy the Token

1. Click **Generate token** at the bottom of the page.
2. GitHub shows the token **once** — copy it immediately.
   It looks like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

> If you close the page without copying, you will need to regenerate a new token.

---

## Step 6 — Share the Token

Send the copied token to your opponent so they can add it to the tracker as `PLAYER2_TOKEN` in the `.env` file.

---

## What this token is used for

The token lets the tracker read your public GitHub activity (commits, PRs, etc.).  
It **cannot** modify your account, delete anything, or access private repositories with these scopes.

---

## Points in this competition

Only **commits** count toward your score. The other stats (PRs, issues, code reviews, repos created) are displayed on the scoreboard for reference but do not add points.

| Metric | Points |
|--------|--------|
| Commit | 10 pts each |
| PR opened | — (display only) |
| PR merged | — (display only) |
| Issue created | — (display only) |
| Code review | — (display only) |
| Repo created | — (display only) |
