# System zarzadzania zadaniami dla zespolu programistycznego

Aplikacja wspiera prace zespolu programistycznego: pozwala definiowac
projekty, przypisywac do nich zadania (taski), zmieniac status zadan, dodawac
komentarze oraz przeszukiwac i filtrowac liste zadan.

## Spis tresci

1. [Opis funkcjonalnosci](#opis-funkcjonalnosci)
2. [Instrukcja uruchomienia](#instrukcja-uruchomienia)
3. [Uruchamianie testow](#uruchamianie-testow)

## 1. Opis funkcjonalnosci
- System logowania i autentykacji oparty o wbudowane widoki `django.contrib.auth`
- Zarzadzanie projektami: lista, tworzenie, edycja, widok szczegolow z lista
  zadan nalezacych do projektu
- Lista zadan z polem wyszukiwania oraz filtrem
  statusu (`To do`, `In progress`, `Done`)
- Tworzenie, edycja oraz usuwanie zadan (CRUD)
- Widok szczegółów zadania z mozliwoscia dodawania komentarzy przez zalogowanych
  uzytkownikow
- Walidacja danych po stronie serwera (formularze `TaskForm`, `ProjectForm`,
  `CommentForm`).


## 2. Instrukcja uruchomienia
### 2.1 Lokalnie
Wszystkie zaleznosci sa wymienione w pliku `project_MVC/requirements.txt`.

```bash
cd project_MVC

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python3 manage.py migrate
python3 manage.py loaddata project_app/fixtures/sample_data.json
python3 manage.py createsuperuser

python3 manage.py runserver
```
Aplikacja bedzie dostepna pod adresem <http://127.0.0.1:8000/>.


## 2.2 Uruchomienie w Dockerze

```bash
cd project_MVC
docker build -t mvc-app .
docker run --rm -p 8000:8000 mvc-app
```

## 3. Testy jednostkowe

```bash
cd project_MVC
python3 -m pytest -v
```


