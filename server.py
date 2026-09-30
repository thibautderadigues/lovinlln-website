"""Serveur local : sert la page, enregistre les inscriptions dans inscriptions.csv
et envoie un mail à chaque inscription.

Lancer :  python3 server.py   puis ouvrir http://localhost:8000

Mail : mettre dans un fichier .env à côté de ce script
    GMAIL_USER=contact.lovin.lln@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
(mot de passe d'application Google, pas le mot de passe du compte).
"""
import csv
import json
import os
import smtplib
import threading
from email.message import EmailMessage
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT, "inscriptions.csv")
FIELDS = ["date", "prenom", "nom", "sexe", "age", "email", "instagram"]
PORT = int(os.environ.get("PORT", 8000))
NOTIFY_TO = "contact.lovin.lln@gmail.com"


def load_env():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def send_signup_mail(row):
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        print("Mail non envoyé : GMAIL_USER / GMAIL_APP_PASSWORD manquants dans .env")
        return
    msg = EmailMessage()
    msg["Subject"] = f"Nouvelle inscription : {row['prenom']} {row['nom']}"
    msg["From"] = user
    msg["To"] = NOTIFY_TO
    msg["Reply-To"] = row["email"]
    msg.set_content(
        "Nouvelle inscription Lovin' LLN\n\n"
        f"Prénom : {row['prenom']}\n"
        f"Nom : {row['nom']}\n"
        f"Sexe : {row['sexe']}\n"
        f"Âge : {row['age']}\n"
        f"Email : {row['email']}\n"
        f"Instagram : {row['instagram']}\n"
        f"Date : {row['date']}\n"
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(user, password.replace(" ", ""))
            smtp.send_message(msg)
        print(f"Mail envoyé à {NOTIFY_TO}")
    except Exception as err:
        print(f"Mail non envoyé : {err}")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_POST(self):
        if self.path != "/api/signup":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            row = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prenom": str(data["firstname"]).strip(),
                "nom": str(data["lastname"]).strip(),
                "sexe": str(data.get("sex", "")).strip(),
                "age": str(data.get("age", "")).strip(),
                "email": str(data["email"]).strip().lower(),
                "instagram": "@" + str(data["instagram"]).strip().lstrip("@"),
            }
        except (ValueError, KeyError):
            return self.send_error(400)

        new_file = not os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        print(f"Nouvelle inscription : {row['prenom']} {row['nom']} ({row['email']})")
        # Send in the background so the visitor isn't kept waiting
        threading.Thread(target=send_signup_mail, args=(row,), daemon=True).start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


if __name__ == "__main__":
    load_env()
    print(f"Speed Dating LLN : http://localhost:{PORT}")
    print(f"Inscriptions enregistrées dans {CSV_PATH}")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
