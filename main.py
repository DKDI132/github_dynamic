import os
import requests
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi import Header,HTTPException
from google import genai
import re
from datetime import date



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
            active_repos.append(repo["name"])
    since_time_iso = since_time.isoformat()
    all_diffs = {}
    for repo_name in active_repos:
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
            compare_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/commits/{najnowszy}"
        else:
            stary = f"{najstarszy['sha']}~1"
            compare_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/compare/{stary}...{najnowszy}"

        compare_response =requests.get(compare_url, headers=diff_headers)

        if compare_response.status_code == 200:
            raw_diff = compare_response.text
            all_diffs[repo_name]=raw_diff
        else:
            print(f"Nie udało się pobrać zmian dla {repo_name}. Status: {compare_response.status_code}")
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
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="JESTES WIRTUALNYM ASYSTENTEM PROGRAMISTY ZAJMUJESZ SIE PISANIEM CHANGELOGA W GITHUB I OPISYWANIEM PROJEKTOW"
    )


def pobierz_szablon_readme() -> str:
    raw_headers = {
        **headers,
        "Accept": "application/vnd.github.raw"
    }

    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_USERNAME}/contents/README_template.md"

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
            dzisiejsza_data = date.today()
            nowy_wiersz = f"| **{key}** | Python | {dzisiejsza_data} | 🔴 Offline |"
            lista.append(nowy_wiersz)
    naglowek = block.split("\n")[:2]

    nowy_blok_tabeli = "\n".join(naglowek + lista)
    nowy_odp = odp.replace(block, nowy_blok_tabeli)
    return nowy_odp



@app.get("/zmiana")
def zmiana(token:str=Header()):
    if not token or token != poprawny():
        raise HTTPException(status_code=401,detail={"status":"error","message":"zostaw moj serwer prosze :C"})
    zmiany = repa()
    stan_aktualny = pobierz_szablon_readme()
    nowy_readme = log_table_set(stan_aktualny,zmiany)




