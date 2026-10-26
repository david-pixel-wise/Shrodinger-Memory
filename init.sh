pipx install uv
rm -rf .venv
uv venv --python 3.9 .venv
source .venv/bin/activate
uv pip install --upgrade pip setuptools wheel
uv pip install pyqt6 pyqt6-tools notebook
uv pip install qiskit-aer matplotlib
uv pip install qiskit_ibm_runtime
export PATH="$PWD/.venv/bin:$PWD/.venv/lib/python3.9/site-packages/qt6_applications/Qt/bin/:$PATH"
alias designer='designer -platform xcb'
chmod +x ./src/exp1_no_entanglement_random_qubits.py
