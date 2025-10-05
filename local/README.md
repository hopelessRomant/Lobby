# Local
This part of Lobby is resposible for all the local machine script that relays the unsigned trasaction to AWS.

>This project uses poetry for dependency management instead of a traditional pip.  

## Getting Started

1. Install `poetry` using the official script for linux 

```bash
curl -sSL https://install.python-poetry.org | python3 -.  
``` 

3. By default, Poetry creates virtual environments inside your user cache. If you want to create venvs inside each project, run
```bash
poetry config virtualenvs.in-project true
```

2. Once `poetry` is installed, you can install the project dependencies defined in `pyproject.toml` by running:

```bash
poetry install --no-root
```