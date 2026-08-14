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
        self.setWindowTitle("Bell State Explorer — Phi+/Phi-/Psi+/Psi-")
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
        Build one of the four Bell basis states (Φ+, Φ-, Ψ+, Ψ-). Backend
        (simulator or real IBM hardware) is selected entirely by
        config.BACKEND_MODE. Since Bloch spheres can't tell the four Bell
        states apart (their single-qubit marginals are identical), the
        simulator-mode popup shows a density-matrix color grid instead --
        see edu_viz.add_density_matrix_grid().

        NOTE on why this uses emoji identity, not just card sign: the
        game's own match rule (reveal_card requires opp_sign, i.e.
        first_lbl[0] != second_lbl[0]) means a match ALWAYS pairs a '+'
        card with a '-' card -- so a scheme that reads both signs only
        ever sees 2 of the 4 possible combinations, and only 2 of the 4
        Bell states are ever reachable (verified: only Φ- and Ψ+ turn up,
        Φ+ and Ψ- never do). To actually show all four, the second bit
        here comes from the matched emoji's index parity instead -- a
        property of *which pair* was matched, independent of sign, and
        it varies across the 8 emojis in the deck.
        """
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)                        # start from |Φ+> = (|00>+|11>)/√2
        if first_lbl[0] == '➖':
            qc.z(0)                        # ➖ on first card -> phase flip (Φ -> Φ-/Ψ-)
        emoji_idx = EMOJIS.index(first_lbl[1:])   # matched cards share the same emoji
        if emoji_idx % 2 == 1:
            qc.x(1)                        # odd emoji index -> bit flip  (-> Ψ family)

        z_flip = first_lbl[0] == '➖'
        x_flip = emoji_idx % 2 == 1
        bell_name = {
            (False, False): "Φ⁺ = (|00⟩+|11⟩)/√2",
            (True,  False): "Φ⁻ = (|00⟩-|11⟩)/√2",
            (False, True):  "Ψ⁺ = (|01⟩+|10⟩)/√2",
            (True,  True):  "Ψ⁻ = (|01⟩-|10⟩)/√2",
        }[(z_flip, x_flip)]

        # qc has entangling gates only (no measure/save_statevector) -- the
        # backend abstraction appends whatever each backend needs.
        vectors, statevec = quantum_backend.get_bloch_vectors(qc, n_qubits=2)
        probs = quantum_backend.get_basis_probabilities(qc, n_qubits=2)

        import matplotlib.pyplot as plt

        if statevec is not None:
            # --- simulator: exact statevector + exact concurrence ---
            # Bloch spheres can't tell the four Bell states apart (their
            # single-qubit marginals are identical). Uses a density-matrix
            # color grid instead: cell SIZE = |amplitude|, cell COLOR =
            # sign (blue/red) -- all four Bell states become visually
            # distinct via a combination of which cells are populated
            # (position) and which are blue vs red (sign). A probability
            # bar chart sits alongside it: same joint probabilities in
            # both Φ and Ψ cases, so the grid's sign-coloring is what
            # actually distinguishes + from - here.
            c = quantum_backend.safe_concurrence(statevec)
            # Same noise-index function used in real-hardware mode -- here
            # it compares the exact vectors against themselves, so it's
            # always exactly 0.0%, an explicit "this is the noiseless
            # baseline" anchor to compare real QPU runs against later.
            sim_vectors = quantum_backend.marginal_bloch_vectors_from_statevector(statevec, 2)
            noise_pct = quantum_backend.get_noise_index(qc, sim_vectors, n_qubits=2)
            # The joint 2-qubit system's complex amplitudes -- an individual
            # qubit in an entangled pair does NOT have its own amplitude
            # (that's why its Bloch vector would sit at the center); only
            # the pair together has a well-defined statevector, shown here.
            amp_line = "Joint state: " + edu_viz.format_statevector_line(statevec, n_qubits=2)

            fig = plt.figure(figsize=(12, 5.5))
            ax_dm = fig.add_subplot(1, 2, 1)
            edu_viz.add_density_matrix_grid(ax_dm, statevec, n_qubits=2)
            ax_bar = fig.add_subplot(1, 2, 2)
            edu_viz.add_probability_bar_chart(ax_bar, probs, n_qubits=2)

            edu_viz.add_boxed_title(
                fig,
                f"{bell_name}\nConcurrence = {c:.2f}  (entangled pair)  [simulator]"
                f"   |   Noise index = {noise_pct:.1f}%\n{amp_line}",
                fontsize=11, top=0.65, bottom=0.14, wspace=0.4,
            )
        else:
            # --- real IBM hardware: Bloch vectors + witness estimated from measurements ---
            from qiskit.visualization import plot_bloch_vector
            witness = quantum_backend.get_entanglement_witness(qc)
            # How far did the real QPU's measured Bloch vectors stray from
            # what an ideal, noiseless simulator predicts for this same
            # circuit? No extra hardware calls needed -- reuses `vectors`
            # (already measured above) against a locally-computed ideal.
            noise_pct = quantum_backend.get_noise_index(qc, vectors, n_qubits=2)
            amp_line = "Joint state amplitudes unavailable on real hardware (measurement statistics only)"
            fig = plt.figure(figsize=(12, 5.5))
            for i, vec in enumerate(vectors):
                ax = fig.add_subplot(1, 3, i + 1, projection='3d')
                plot_bloch_vector(vec, ax=ax, title=f"qubit {i}", font_size=13)
            ax_bar = fig.add_subplot(1, 3, 3)
            edu_viz.add_probability_bar_chart(ax_bar, probs, n_qubits=2)
            edu_viz.add_boxed_title(
                fig,
                f"{bell_name}\n"
                f"|<XX>|+|<YY>|+|<ZZ>| = {witness:.2f}  (entanglement witness, real QPU)"
                f"   |   Noise index = {noise_pct:.1f}% (vs ideal simulation)\n{amp_line}",
                fontsize=11, top=0.62, bottom=0.06, wspace=0.35,
            )

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