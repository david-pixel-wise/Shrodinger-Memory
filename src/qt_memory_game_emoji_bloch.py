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
from qiskit.visualization import plot_bloch_multivector

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
        self.setWindowTitle("Bloch sphere of the signs")
        self.setMinimumSize(600, 300)

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
        self.sim = AerSimulator(method='statevector')
        self.sim.set_options(shots=1)        # one measurement per circuit call

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
            btn.setFont(QtGui.QFont(font_emoji, 32))
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
            result = self.sim.run(qc).result()
            bits = next(iter(result.get_counts(qc)))   # only one entry
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
        btn.setText(label)
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
                    QtWidgets.QMessageBox.information(
                        self, "Congratulations",
                        "All pairs have been found! Well done.")
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
        Build a 2‑qubit state that matches the signs of the two cards,
        obtain its statevector (new Aer 0.17.2 API), and display the Bloch picture.
        """
        # Map '+' → |0⟩ and '-' → |1⟩ (using the Unicode plus/minus you chose)
        sign_to_vec = {'➕': [1, 0], '➖': [0, 1]}

        qc = QuantumCircuit(2)
        qc.initialize(sign_to_vec[first_lbl[0]], 0)   # qubit 0 = sign of first card
        qc.initialize(sign_to_vec[second_lbl[0]], 1)  # qubit 1 = sign of second card
        qc.save_statevector()                         # safety for newer Aer

        sim = AerSimulator(method='statevector')
        result = sim.run(qc).result()

        try:
            statevec = result.get_statevector()
        except Exception:            # very old result objects
            statevec = result.data(0)['statevector']

        fig = plot_bloch_multivector(statevec)

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