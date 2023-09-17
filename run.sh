#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

VENVPATH="${VENVPATH:-./venv}"
PROJECT="${PROJECT:-gingrwrapp}"

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

build() {
    python -m build
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
    find . -name '.ruff_cache' -exec rm -fr {} +
    find . -name '.mypy_cache' -exec rm -fr {} +
    find . -name '.pytest_cache' -exec rm -fr {} +
    find . -name '*.egg-info' -exec rm -fr {} +
}

lint() {
    wrapped-python -m ruff check .
    wrapped-python -m mypy gingrwrapp
}

tests() {
    wrapped-python -X dev -m unittest tests/test_client.py
}

test() {
    wrapped-python -X dev \
        -m unittest "tests.test_client.ClientTestCase.test_${1}"
}

docs() {
    wrapped-python -m pdoc --docformat=google "${PROJECT}"
}

help() {
    echo
    echo "./run.sh build                    # whl and sdist packages"
    echo "./run.sh docs                     # local pdoc server"
    echo "./run.sh install                  # configure venv and install deps"
    echo "./run.sh install dev,doc          # optional dependencies"
    echo "./run.sh tests                    # run full set of client tests"
    echo "./run.sh test get_reservations    # run test for single func/method"
    echo "./run.sh lint                     # ruff and mypy"
    echo "./run.sh clean                    # rm files not source controlled"
    echo "./run.sh help                     # print this helpful message"
    echo
}

default() {
    help
}

TIMEFORMAT="Task completed in %3lR"
time "${@:-default}"
