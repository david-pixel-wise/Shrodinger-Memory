#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quantum enhanced memory matching game (Qt 6 + Qiskit 2.2.3 + Aer 0.17.2).

* UI is built completely in Python (no .ui file).
* Deck (sign + emoji) is generated once by a quantum circuit.
* Hidden cards are black with a white “❓”.
* Revealed cards are white with black text.
* After a correct match a modal popup shows the Bloch spheres of the two
  sign qubits (code adapted for Aer 0.17.2).
"""

# -------------------------------------------------
# 1. Imports
# -------------------------------------------------
import sys
import random
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt6 import QtWidgets, QtCore, QtGui
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_bloch_multivector, plot_bloch_vector
import config
import quantum_backend
import edu_viz

# -----------------------------------------------------------------
# 2. Matplotlib canvas import – works with both Qt5 and Qt6
# -----------------------------------------------------------------
try:
    # Qt‑Agg backend works for both Qt5 and Qt6 (since Matplotlib 3.5)
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:          # very old matplotlib (<3.4)
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    warnings.filterwarnings("ignore", category=DeprecationWarning)

# -------------------------------------------------
# 3. Emoji table (index 0‑7)
# -------------------------------------------------
EMOJIS = [
    "🐱", "🐶", "🦊", "🐮",
    "🐵", "🐷", "🐻", "🐸"
]

# -------------------------------------------------
# 4. Quantum helper functions
# -------------------------------------------------
def bits_to_card(bitstring: str) -> str:
    """Convert a 4 bit result (q3 q2 q1 q0) into '+🐱' / '-🐸'."""
    sign = '➕' if bitstring[-1] == '0' else '➖'
    idx  = int(bitstring[-4:-1], 2)          # three bits → 0‑7
    return f"{sign}{EMOJIS[idx]}"


def make_card_circuit(entangle: bool = False) -> QuantumCircuit:
    """Four qubit circuit that yields any of the 16 sign emoji states."""
    qc = QuantumCircuit(4, 4)                # 4 qubits, 4 classical bits
    for q in range(4):
        qc.h(q)                              # uniform superposition
    if entangle:
        qc.cx(1, 0)                          # optional parity entanglement
    qc.measure(range(4), range(4))
    return qc


# -------------------------------------------------
# 5. Dialog that displays a Matplotlib figure (Bloch spheres)
# -------------------------------------------------
class BlochDialog(QtWidgets.QDialog):
    """Modal dialog that embeds a Matplotlib Figure."""
    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entanglement Growth — Bloch Spheres & Concurrence Trend")
        self.setMinimumSize(1000, 560)   # bigger popup -- readability was cramped at 600x300

        layout = QtWidgets.QVBoxLayout(self)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)


# -------------------------------------------------
# 6. Main window (Qt 6)
# -------------------------------------------------
class MemoryGameWindow(QtWidgets.QMainWindow):
    # -----------------------------------------------------------------
    # Configuration constants – edit here if you wish
    # -----------------------------------------------------------------
    ENTANGLE = True               # parity entanglement of sign & number
    CARD_BACK = "❓"
    BACK_COLOR_HIDDEN = "darkgray"
    TEXT_COLOR_HIDDEN = "white"
    BACK_COLOR_REVEALED = "white"
    TEXT_COLOR_REVEALED = "black"
    GRID_SIZE = 4                 # 4×4 board → 16 cards

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Schrödinger Memory")
        self.setFixedSize(540, 560)

        # -------------------------------------------------
        # 6.1 Simulator – used only for deck generation
        # -------------------------------------------------
        # Backend (simulator or real IBM hardware) is selected in config.py;
        # see quantum_backend.py for the abstraction used below.

        # -------------------------------------------------
        # 6.2 Generate the deck once (quantum part)
        # -------------------------------------------------
        self.deck = self.generate_deck()     # shuffled list of 16 distinct cards

        # -------------------------------------------------
        # 6.3 Build the UI (grid of buttons) completely in Python
        # -------------------------------------------------
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        grid = QtWidgets.QGridLayout()
        central.setLayout(grid)

        self.buttons = []                    # indexed 0 … 15
        for pos in range(self.GRID_SIZE ** 2):
            btn = QtWidgets.QPushButton(self.CARD_BACK)
            btn.setFixedSize(110, 110)
            btn.setFont(QtGui.QFont(font_emoji, 64))
            btn.setStyleSheet(
                f"background-color: {self.BACK_COLOR_HIDDEN}; "
                f"color: {self.TEXT_COLOR_HIDDEN};"
            )
            btn.clicked.connect(self._make_click_handler(pos))
            row = pos // self.GRID_SIZE
            col = pos % self.GRID_SIZE
            grid.addWidget(btn, row, col)
            self.buttons.append(btn)

        # -------------------------------------------------
        # 6.4 Game state
        # -------------------------------------------------
        self.revealed = {}            # idx → label (e.g. '+🐱')
        self.first_pick = None        # (idx, label) of the first card of the turn
        self.pairs_found = 0
        self.concurrence_history = []  # one entry per match, for the trend graph
        self.locked = False           # ← prevents a third click while waiting

    # -----------------------------------------------------------------
    # 6.5 Deck generation – quantum circuit is called **only here**
    # -----------------------------------------------------------------
    def generate_deck(self):
        """Run a 4 qubit circuit until all 16 distinct sign emoji outcomes are collected."""
        needed = {f"+{e}" for e in EMOJIS} | {f"-{e}" for e in EMOJIS}
        obtained = set()
        deck = []

        while len(deck) < 16:
            qc = make_card_circuit(entangle=self.ENTANGLE)
            bits = quantum_backend.run_deck_circuit(qc)   # simulator or real IBM QPU, per config.py
            card = bits_to_card(bits)

            if card not in obtained:
                obtained.add(card)
                deck.append(card)

        random.shuffle(deck)
        return deck

    # -----------------------------------------------------------------
    # 6.6 Helper to create a closure that remembers the button index
    # -----------------------------------------------------------------
    def _make_click_handler(self, idx: int):
        def handler():
            if self.locked:                     # ← ignore clicks while locked
                return
            if idx in self.revealed:            # already matched, ignore click
                return
            self.reveal_card(idx)
        return handler

    # -----------------------------------------------------------------
    # 6.7 Reveal a card – no quantum call here, just show the preset label
    # -----------------------------------------------------------------
    def reveal_card(self, idx: int):
        label = self.deck[idx]

        btn = self.buttons[idx]
        btn.setText(label[1:])   # show only the emoji -- the +/- sign is internal
                                 # bookkeeping (deck generation + match rule), not a
                                 # real 'positive/negative qubit' concept worth showing
        btn.setStyleSheet(
            f"background-color: {self.BACK_COLOR_REVEALED}; "
            f"color: {self.TEXT_COLOR_REVEALED};"
        )
        self.revealed[idx] = label

        if self.first_pick is None:
            # first card of the current turn
            self.first_pick = (idx, label)
        else:
            # second card – evaluate the pair
            first_idx, first_lbl = self.first_pick
            second_idx, second_lbl = idx, label

            same_emoji = first_lbl[1:] == second_lbl[1:]   # same emoji
            opp_sign   = first_lbl[0] != second_lbl[0]     # opposite sign

            if same_emoji and opp_sign:
                # ---------- MATCH ----------
                self.pairs_found += 1
                self.first_pick = None

                # Show Bloch‑sphere of the two sign‑qubits
                self.show_bloch_pair(first_lbl, second_lbl)

                if self.pairs_found == (self.GRID_SIZE ** 2) // 2:
                    # Minimal QMessageBox pattern straight from the Qt6 docs:
                    # construct with a parent, setText, exec -- no manual
                    # label-alignment workarounds needed.
                    win_box = QtWidgets.QMessageBox(self)
                    win_box.setWindowTitle("Congratulations")
                    win_box.setText("All pairs have been found! Well done.")
                    win_box.exec()
                # matched cards stay face‑up – nothing else needed
            else:
                # ---------- NOT A MATCH ----------
                self.locked = True                     # ← lock the UI
                QtCore.QTimer.singleShot(
                    1000,
                    lambda: self.hide_pair(first_idx, second_idx))

    # -----------------------------------------------------------------
    # 6.8 Hide the two cards that were not a match
    # -----------------------------------------------------------------
    def hide_pair(self, idx1: int, idx2: int):
        for i in (idx1, idx2):
            btn = self.buttons[i]
            btn.setText(self.CARD_BACK)
            btn.setStyleSheet(
                f"background-color: {self.BACK_COLOR_HIDDEN}; "
                f"color: {self.TEXT_COLOR_HIDDEN};"
            )
            self.revealed.pop(i, None)
        self.first_pick = None
        self.locked = False            # ← unlock again after hiding

    # -----------------------------------------------------------------
    # 6.9 Bloch‑sphere popup for the two sign‑qubits of a matching pair
    # -----------------------------------------------------------------
    def show_bloch_pair(self, first_lbl: str, second_lbl: str):
        """
        Build a 2-qubit state whose entanglement strength grows with game
        progress (tunable RY angle instead of a fixed Hadamard). Backend
        (simulator or real IBM hardware) is selected entirely by
        config.BACKEND_MODE. The popup shows the two qubits' Bloch
        spheres next to a graph of concurrence across every match so far
        in this game, so growth over time is visible at a glance -- same
        single BlochDialog, richer figure.
        """
        import math

        theta = math.pi / 2 * min(self.pairs_found / 8, 1.0)   # 0 -> pi/2 as game progresses

        qc = QuantumCircuit(2)
        qc.ry(theta, 0)
        qc.cx(0, 1)                        # entangling gate, strength set by theta
        if first_lbl[0] == '➖':
            qc.x(0)                        # encode sign of the first card
        if second_lbl[0] == '➖':
            qc.x(1)                        # encode sign of the second card

        formula = f"cos({theta/2:.2f})|00⟩ + sin({theta/2:.2f})|11⟩  (before sign encoding)"

        # qc has entangling gates only (no measure/save_statevector) -- the
        # backend abstraction appends whatever each backend needs.
        vectors, statevec = quantum_backend.get_bloch_vectors(qc, n_qubits=2)

        import matplotlib.pyplot as plt

        if statevec is not None:
            # --- simulator: exact statevector + exact concurrence ---
            c = quantum_backend.safe_concurrence(statevec)
            vectors = quantum_backend.marginal_bloch_vectors_from_statevector(statevec, 2)
            # Same noise-index function used in real-hardware mode -- here
            # it compares the exact vectors against themselves, so it's
            # always exactly 0.0%, an explicit "this is the noiseless
            # baseline" anchor to compare real QPU runs against later.
            noise_pct = quantum_backend.get_noise_index(qc, vectors, n_qubits=2)
            backend_tag = "simulator"
            metric_line = f"Concurrence = {c:.2f}   |   Noise index = {noise_pct:.1f}%"
            amp_line = "Joint state: " + edu_viz.format_statevector_line(statevec, n_qubits=2)
        else:
            # --- real IBM hardware: vectors + witness estimated from measurements ---
            witness = quantum_backend.get_entanglement_witness(qc)
            c = witness / 3.0   # rough 0..1 proxy so the trend graph stays comparable
            # How far did the real QPU's measured Bloch vectors stray from
            # what an ideal, noiseless simulator predicts for this same
            # circuit? No extra hardware calls needed -- reuses `vectors`
            # (already measured above) against a locally-computed ideal.
            noise_pct = quantum_backend.get_noise_index(qc, vectors, n_qubits=2)
            backend_tag = "real QPU"
            metric_line = (f"|<XX>|+|<YY>|+|<ZZ>| = {witness:.2f}  (witness)"
                            f"   |   Noise index = {noise_pct:.1f}% (vs ideal simulation)")
            amp_line = "Joint state amplitudes unavailable on real hardware (measurement statistics only)"

        self.concurrence_history.append(c)

        fig = plt.figure(figsize=(12, 5.5))
        for i, vec in enumerate(vectors):
            norm = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
            ax = fig.add_subplot(1, 3, i + 1, projection='3d')
            # |v| shrinks toward 0 as concurrence climbs toward 1 -- that
            # shrinking arrow *is* growing entanglement, not a glitch.
            plot_bloch_vector(vec, ax=ax, title=f"qubit {i}  |v| = {norm:.2f}",
                               font_size=13)
        ax_trend = fig.add_subplot(1, 3, 3)
        edu_viz.add_concurrence_trend(ax_trend, self.concurrence_history)

        edu_viz.add_boxed_title(
            fig, f"θ = {theta:.2f} rad   {formula}\n{metric_line}  [{backend_tag}]\n{amp_line}",
            fontsize=10.5, top=0.60, bottom=0.08, wspace=0.35)

        dlg = BlochDialog(fig, parent=self)
        dlg.exec()      # modal – player must close it before continuing

# -------------------------------------------------
# 7. Application entry point
# -------------------------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)

    # Optional – force an emoji‑capable font if the system provides one
    families = QtGui.QFontDatabase.families()
    for fam in ("Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"):
        if fam in families:
            app.setFont(QtGui.QFont(fam, 12))
            global font_emoji
            font_emoji = fam
            break

    win = MemoryGameWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()