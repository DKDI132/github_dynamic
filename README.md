# ⚡ github_dynamic

Automatyczny silnik (backend) w FastAPI dedykowany do generowania i aktualizowania dynamicznego profilu README na GitHubie przy użyciu sztucznej inteligencji (**Gemini 3.5 Flash**) oraz **GitHub Actions**.

---

## 🚀 Jak to działa? (Architektura)

Projekt działa w bezstanowym, bezpiecznym przepływie (flow) oddzielającym generowanie treści od uprawnień do zapisu w repozytorium:

```
[ GitHub Actions (Cron) ] 
       │
       ▼ (Zapytanie GET z tokenem w nagłówku)
[ Nginx (Reverse Proxy) ] ──► [ FastAPI (Python) ]
                                   │
                                   ├─► [ GitHub API ] (Pobieranie commitów i diffów z 24h)
                                   ├─► [ Gemini API ] (Wygenerowanie changeloga)
                                   └─► [ README.md ] (Odesłanie zaktualizowanego kodu Markdown)
                                   
       ┌───────────────────────────┘
       ▼
[ GitHub Actions ] ──► (Zapis i commit pliku README.md na profilu)
```

---

## 🛠️ Kluczowe Funkcjonalności

1. **AI Daily Standup:** Automatycznie generuje codzienne podsumowanie Twojej pracy w pierwszej osobie liczby pojedynczej na podstawie skumulowanych diffów z commitów z ostatnich 24h.
2. **Automatyczna Tabela Aktywności:** Skanuje Twoje repozytoria i aktualizuje w tabeli datę ostatniej aktywności dla projektów, które modyfikowałeś.
3. **Wykrywanie Nowych Projektów:** Jeśli stworzysz nowe repozytorium i spushujesz tam kod, backend automatycznie dopisze nowy wiersz do tabeli, rozpozna język projektu z metadanych gita i doklei na koniec listy projektów gotowy szablon sekcji do uzupełnienia opisu.

---

## ⚙️ Wymagane Zmienne Środowiskowe (.env)

Aby backend działał poprawnie, musisz ustawić następujące zmienne środowiskowe na swoim serwerze (lub w pliku `.env` lokalnie):

* `token_github` – Twój GitHub Personal Access Token (PAT) z uprawnieniami do odczytu publicznych repozytoriów (Read-only).
* `token` – Dowolne hasło autoryzacyjne, które zdefiniujesz do komunikacji między GitHub Actions a Twoim backendem (zapobiega nieautoryzowanym żądaniom).
* `GEMINI_API_KEY` – Klucz API do Google AI Studio (obsługujący model `gemini-3.5-flash`).

---

## 📦 Uruchomienie lokalne

1. Zainstaluj wymagane pakiety:
   ```bash
   pip install -r requirements.txt
   ```
2. Skonfiguruj zmienne w pliku `.env`.
3. Uruchom serwer uvicorn:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
4. Wyślij testowe zapytanie przez cURL (lub Postmana):
   ```bash
   curl -H "token: TWÓJ_TOKEN" http://127.0.0.1:8000/zmiana
   ```
