import os
import requests
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Header, HTTPException, Response
from google import genai
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.readme')


def token()->str:
    return str(os.getenv("token_github"))

client = genai.Client()
GITHUB_USERNAME = "DKDI132"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer " + token(),
    "User-Agent": "ODSWIEZACZ"
}

app = FastAPI()
def poprawny():
    return os.getenv("token")


def znajdz_zmiany(repa):
    since_time = datetime.now(timezone.utc) - timedelta(hours=24)
    active_repos = []

    for repo in repa:
        pushed_at_str = repo["pushed_at"].replace("Z", "+00:00")
        pushed_at = datetime.fromisoformat(pushed_at_str)

        if pushed_at > since_time:
            active_repos.append(repo)
    since_time_iso = since_time.isoformat()
    all_diffs = {}
    for repo in active_repos:
        repo_name=repo["name"]
        commits_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/commits"
        commit_params = {"since": since_time_iso}

        commits_response = requests.get(commits_url, headers=headers, params=commit_params)
        commits = commits_response.json()

        if not isinstance(commits, list) or len(commits) == 0:
            print(f"Brak nowych commitów w repo {repo_name} z ostatnich 24h.")
            continue
        diff_headers = {
            **headers,
            "Accept": "application/vnd.github.v3.diff"
        }
        najnowszy = commits[0]["sha"]
        najstarszy = commits[-1]

        if len(najstarszy["parents"]) == 0:
            initial_sha = najstarszy["sha"]
            commit_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/commits/{initial_sha}"
            commit_response = requests.get(commit_url, headers=diff_headers)
            diff_initial = commit_response.text if commit_response.status_code == 200 else ""

            if najnowszy != initial_sha:
                compare_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/compare/{initial_sha}...{najnowszy}"
                compare_response = requests.get(compare_url, headers=diff_headers)
                diff_rest = compare_response.text if compare_response.status_code == 200 else ""
                raw_diff = diff_initial + "\n" + diff_rest
            else:
                raw_diff = diff_initial
        else:
            stary = f"{najstarszy['sha']}~1"
            compare_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/compare/{stary}...{najnowszy}"
            compare_response = requests.get(compare_url, headers=diff_headers)
            diff_rest = compare_response.text if compare_response.status_code == 200 else ""
            raw_diff=diff_rest

        all_diffs[repo_name]={
            "diff":raw_diff,
            "language":repo.get("language") or "Python"
        }

    return all_diffs



def repa():


    repos_url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
    params = {
        "sort": "pushed",
        "direction": "desc",
        "per_page": 10
    }

    repos_response = requests.get(repos_url, headers=headers, params=params)
    repos = repos_response.json()
    return znajdz_zmiany(repos)

def ai(repa):
    prompt = f"""
        Na podstawie poniższych zmian z GitHuba z ostatnich 24h:
        {repa}

        Napisz krótkie (maksymalnie 3-4 punkty) podsumowanie dzisiejszej pracy w formacie listy Markdown odnoszac sie do kazdego projektu z osobna.
        Użyj pasujących ikon emoji do każdego punktu.
        Pisz w pierwszej osobie liczby pojedynczej (np. "Naprawiłem...", "Dodałem...").
        Zwróć TYLKO te punkty listy (czysty markdown bez dodatkowego komentarza i bez znaczników ```).
        """
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Błąd AI przy changelogu: {e}")
        return "* 🤖 Błąd generowania dzisiejszego logu przez AI."


def pobierz_szablon_readme() -> str:
    raw_headers = {
        **headers,
        "Accept": "application/vnd.github.raw"
    }

    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_USERNAME}/contents/README.md"

    response = requests.get(url, headers=raw_headers)

    if response.status_code == 200:
        return response.text
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Nie udało się pobrać szablonu README z GitHub. Status: {response.status_code}"
        )

def log_table_set(odp,zmiany):
    projekty={}
    for key in zmiany.keys():
        projekty[key]=0

    block = re.search(r"<!-- LOG_TABLE_START -->(.*?)<!-- LOG_TABLE_END -->", odp, flags=re.DOTALL).group(1).strip()
    lista = block.split("\n")[2::]
    for i in range(len(lista)):
        if not lista[i].strip():
            continue
        lista[i] = lista[i].split("|")
        for key in projekty.keys():
            if key.lower()==lista[i][1].strip().strip("**").lower():
                aktualna_data = date.today()
                lista[i][3]=" "+str(aktualna_data)+" "
                projekty[key]=1
    for i in range(len(lista)):
        if isinstance(lista[i], list):
            lista[i] = "|".join(lista[i])

    for key in projekty.keys():
        if projekty[key] == 0:
            dzisiejsza_data = date.today().strftime("%d %b. %Y")
            lang = zmiany[key]["language"]

            nowy_wiersz = f"| **{key}** | {lang} | {dzisiejsza_data} | 🔴 Offline |"
            lista.append(nowy_wiersz)

            start_tag = f"<!-- PROJECT_{key}_START -->"
            end_tag = f"<!-- PROJECT_{key}_END -->"
            nowy_szablon = f"""{start_tag}
### 📦 {key}
**{lang}**
🚀 PROJEKT NIE JEST JESZCZE SKONCZONY CO ZA TYM IDZIE OPIS ZOSTAL AUTOMATYCZNIE WYGENEROWANY I ZOSTANIE UZUPELNIONY PO DOPROWADZENIU DO BETY

Możliwości:
- Cecha 1
- Cecha 2

```
Repository: DKDI132/{key}
Language: {lang}
Last update: {dzisiejsza_data}
```

🔗 [Otwórz projekt](https://github.com/DKDI132/{key})
{end_tag}
---
"""
            odp = odp.replace("<!-- PROJECTS_LIST_END -->", f"{nowy_szablon}<!-- PROJECTS_LIST_END -->")
    naglowek = block.split("\n")[:2]
    nowy_blok_tabeli = "\n".join(naglowek + lista)
    return odp.replace(block, nowy_blok_tabeli)



@app.get("/zmiana")
def zmiana(token:str=Header()):
    if not token or token != poprawny():
        raise HTTPException(status_code=401,detail={"status":"error","message":"zostaw moj serwer prosze :C"})
    zmiany = repa()
    stan_aktualny = pobierz_szablon_readme()
    if not zmiany:
        no_activity_status = "*🤖 Status: Brak nowych commitów w ciągu ostatnich 24h. Czas na odpoczynek!* ☕"
        match = re.search(r"<!-- AUTO_CHANGELOG_START -->([\s\S]*?)<!-- AUTO_CHANGELOG_END -->", stan_aktualny)
        if match:
            stan_aktualny = stan_aktualny.replace(match.group(1), f"\n{no_activity_status}\n")
        return Response(content=stan_aktualny, media_type="text/markdown")

    zmieniony = log_table_set(stan_aktualny, zmiany)

    tekst_changelog = ai(zmiany)
    match = re.search(r"<!-- AUTO_CHANGELOG_START -->([\s\S]*?)<!-- AUTO_CHANGELOG_END -->", zmieniony)
    if match:
        zmieniony = zmieniony.replace(match.group(1), f"\n\n{tekst_changelog}\n\n")
    return Response(content=zmieniony, media_type="text/markdown")







