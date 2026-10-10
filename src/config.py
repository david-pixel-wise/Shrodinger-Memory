#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Central configuration for all Schrödinger Memory experiments.

This is the ONLY file you need to edit to switch between:
  - running everything on your own machine (Aer simulator), or
  - running on a real IBM Quantum processor via qiskit-ibm-runtime.

Requires (only for BACKEND_MODE = "ibm"):
    pip install qiskit-ibm-runtime

You must also have saved your IBM Quantum credentials once, e.g.:
    from qiskit_ibm_runtime import QiskitRuntimeService
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="YOUR_TOKEN")
(or set IBM_TOKEN below directly).
"""

# -------------------------------------------------------------------
# THE SWITCH
# -------------------------------------------------------------------
# "simulator" -> AerSimulator, runs locally, instant, exact statevectors.
# "ibm"       -> a real IBM Quantum backend, queued, noisy, no exact
#                statevector available (Bloch vectors are estimated from
#                measured Pauli expectation values instead).
BACKEND_MODE = "ibm"          # "simulator"  or  "ibm"

# -------------------------------------------------------------------
# IBM Quantum settings (only read when BACKEND_MODE == "ibm")
# -------------------------------------------------------------------
IBM_CHANNEL  = "ibm_quantum_platform"     # "ibm_quantum" or "ibm_cloud"
IBM_INSTANCE = None                       # e.g. "ibm-q/open/main"; None = default
IBM_TOKEN    = None                       # None -> use a previously saved account
IBM_BACKEND  = None                       # None -> auto-pick the least-busy real QPU
IBM_SHOTS    = 1024                       # shots per circuit/observable on hardware
