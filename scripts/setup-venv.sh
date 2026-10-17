# ClipDev — setup local
# O projeto usa GTK3/PyGObject do sistema, disponível apenas no /usr/bin/python3.10.
# Por isso o venv é criado com --system-site-packages apontando para o 3.10.

PY=/usr/bin/python3.10
VENV=.venv

"$PY" -m venv --system-site-packages "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip pytest

echo "venv criado em $VENV usando $PY"
echo "rodar testes: ./scripts/test.sh"