#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

VENVPATH="${VENVPATH:-./venv}"
PROJECT="${PROJECT:-gingrwrapp}"
POSTGRES_USER="${POSTGRES_USER:-K9}"
POSTGRES_PASSWORD="i1SxA5hvCxakezpJnQSEe8UVWGZipaCwe+C2Jn+GJSU="
POSTGRES_DB="${POSTGRES_DB:-gingrwrapp_db}"

# Dependency Management

venv() {
    if [[ -d "${VENVPATH}/bin" ]]; then
        echo "source ${VENVPATH}/bin/activate"
    else
        echo "source ${VENVPATH}/Scripts/activate"
    fi
}

make-venv() {
    python -m venv "${VENVPATH}"
}

reset-venv() {
    rm -rf "${VENVPATH}"
    make-venv
}

wrapped-python() {
    # unix
    if [[ -d "${VENVPATH}/bin" ]]; then
        "${VENVPATH}"/bin/python "$@"
    # windows
    elif [[ -d "${VENVPATH}/Scripts" ]]; then
        "${VENVPATH}"/Scripts/python "$@"
    else
        echo
        echo "No virtual environment"
        echo "Hint: ./run.sh install"
        echo
    fi
}

wrapped-pip() {
    wrapped-python -m pip "$@"
}

python-deps() {
    wrapped-pip install --upgrade pip setuptools wheel

    local pip_extras="${1:-}"
    if [[ -z "${pip_extras}" ]]; then
        wrapped-pip install .
    else
        wrapped-pip install ".[${pip_extras}]"
    fi
}

install() {
    if [[ -d "${VENVPATH}" ]]; then
        python-deps "$@"
    else
        make-venv && python-deps "$@"
    fi
}

postgres() {
    podman pull docker.io/postgres:15
    mkdir -p "${HOME}/.var/postgres/data"
    podman run --detach --name postgresql-server \
        --userns=keep-id \
        -p 5432:5432 \
        -e POSTGRES_DB="${PROJECT}" \
        -e POSTGRES_USER="${POSTGRES_USER}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
        -e POSTGRES_HOST_AUTH_METHOD="trust" \
        -v "${HOME}/.var/postgres/data:/var/lib/postgresql/data:Z" \
        docker.io/postgres:latest
}

clean-postgres() {
    echo "Warning! This will delete all data in the postgres database."
    echo "Continue? [y/n]"
    read -r continue
    if [[ "$continue" == "y" ]]; then
        podman stop postgresql-server
        podman rm postgresql-server
        rm -rf ~/.var/postgres
    fi
}

reset-db() {
    clean-postgres
    sleep 4
    postgres
    sleep 6
    clean-migrations
    init-migrations
}

copy-datamigrations() {
    cp -v data_migrations/accounts/000* accounts/migrations/
    # cp -v data_migrations/projects/000* projects/migrations/
}

clean-migrations() {
    rm -f */migrations/0*.py
}

init-migrations() {
    wrapped-python manage.py makemigrations &&
    wrapped-python manage.py migrate &&
    copy-datamigrations &&
    wrapped-python manage.py migrate
}

psql() {
    /usr/bin/psql -U bobdabuilda -h localhost -d buildsure
}

# Drop all tables
drop-tables() {
    /usr/bin/psql -U bobdabuilda -h localhost -d buildsure -c "\dt" \
        | grep table | awk '{print "DROP TABLE IF EXISTS "$3 " CASCADE;"}' \
        | /usr/bin/psql -U bobdabuilda -h localhost -d buildsure
}

# Utils

build() {
    python -m build
}

publish() {
    lint && tests && clean && build
    python -m twine upload dist/*
}

clean() {
    rm -rf dist/
    rm -rf .eggs/
    rm -rf build/
    rm -rf staticfiles/
    find . -name '*.pyc' -exec rm -f {} +
    find . -name '*.pyo' -exec rm -f {} +
    find . -name '*~' -exec rm -f {} +
    find . -name '__pycache__' -exec rm -fr {} +
    find . -name '.mypy_cache' -exec rm -fr {} +
    find . -name '.pytest_cache' -exec rm -fr {} +
    find . -name '*.egg-info' -exec rm -fr {} +
}

lint() {
    wrapped-python -m ruff check .
}

tests() {
    wrapped-python -X dev -m unittest gingrwrapp/client/tests.py
}

test() {
    wrapped-python -X dev \
        -m unittest "gingrwrapp.client.tests.ClientTestCase.test_${1}"
}

prodserver() {
    # run uwsgi and caddy in parallel
    (trap 'kill 0' SIGINT; caddy run --config Caddyfile & "${VENVPATH}"/bin/uwsgi --ini uwsgi.ini)
}

docs() {
  pdoc --docformat=google "${PROJECT}"
}

help() {
    echo
    echo "./run.sh                          # alias bin/gingrwrapp"
    echo "./run.sh build                    # whl and sdist"
    echo "./run.sh docs                     # local pdoc"
    echo "./run.sh install                  # configure venv and install deps"
    echo "./run.sh install dev,doc          # optional dependencies"
    echo "./run.sh tests                    # run full set of client tests"
    echo "./run.sh test get_reservations    # run test for single func/method"
    echo "./run.sh lint                     # ruff"
    echo "./run.sh clean                    # rm files not source controlled"
    echo "./run.sh help                     # print this helpful message"
    echo
}

default() {
    DEBUG=1 wrapped-python -X dev "${PROJECT}"
}

TIMEFORMAT="Task completed in %3lR"
time "${@:-default}"
