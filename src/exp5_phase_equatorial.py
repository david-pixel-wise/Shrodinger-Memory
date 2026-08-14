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
        self.setWindowTitle("Phase Entanglement — Correlator View")
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
        Build a phase-type entangled 2-qubit state (H+H+CZ). Backend
        (simulator or real IBM hardware) is selected entirely by
        config.BACKEND_MODE.

        Simulator mode shows a density-matrix color grid (reused from
        Experiment 3) next to the correlator bar chart, NOT Bloch spheres. Checked
        this directly: for this maximally-entangled state the marginal
        Bloch vectors are *exactly* zero on the simulator every single
        time (|v| = 0.00, no exceptions) -- so two empty spheres were
        never showing anything a player could learn from match to match.
        The density-matrix grid is genuinely informative instead: this
        state's matrix is fully populated (all 16 cells nonzero) versus
        Experiment 3's Bell states (only 4 cells nonzero), so the two experiments look
        visibly different in kind, not just in color pattern.

        Real-hardware mode keeps the Bloch spheres -- there they ARE
        meaningful: real QPU noise means the *measured* marginal vectors
        won't be exactly zero, so their (small) length is a genuine
        signal of how noisy that particular hardware run was, which the
        simulator can never show.

        NOTE on why qubit 1's flip comes from emoji parity, not sign: the
        game's own match rule (reveal_card requires opp_sign, i.e.
        first_lbl[0] != second_lbl[0]) means a match ALWAYS pairs a '+'
        card with a '-' card. Reading both signs therefore only ever
        reaches 2 of the 4 possible flip combinations -- verified this
        collapses <YY> to always read -1.00, the same chart every single
        match, regardless of which pair was found. Fixed the same way as
        Experiment 3: the second flip now comes from the matched emoji's index
        parity (independent of sign), which unlocks the other combination
        too -- verified <YY> now reaches both +1.00 and -1.00 depending
        on which emoji was matched and which card was clicked first.
        """
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        qc.cz(0, 1)                        # phase-type entangling gate
        if first_lbl[0] == '➖':
            qc.x(0)                        # encode sign of the first card
        emoji_idx = EMOJIS.index(first_lbl[1:])   # matched cards share the same emoji
        if emoji_idx % 2 == 1:
            qc.x(1)                        # odd emoji index -> bit flip on qubit 1

        # Exact state formula for each combination (verified against the
        # actual statevector amplitudes, see conversation). The minus
        # sign inherited from the CZ gate moves to a different basis state
        # depending on which x gates fired.
        x0 = first_lbl[0] == '➖'
        x1 = emoji_idx % 2 == 1
        formula = {
            (False, False): "(|00⟩+|01⟩+|10⟩-|11⟩)/2",
            (True,  False): "(|00⟩+|01⟩-|10⟩+|11⟩)/2",
            (False, True):  "(|00⟩-|01⟩+|10⟩+|11⟩)/2",
            (True,  True):  "(-|00⟩+|01⟩+|10⟩+|11⟩)/2",
        }[(x0, x1)]

        # qc has entangling gates only (no measure/save_statevector) -- the
        # backend abstraction appends whatever each backend needs.
        vectors, statevec = quantum_backend.get_bloch_vectors(qc, n_qubits=2)
        correlators = quantum_backend.get_pauli_correlators(qc)

        import matplotlib.pyplot as plt

        if statevec is not None:
            # --- simulator: density-matrix grid + correlator chart ---
            c = quantum_backend.safe_concurrence(statevec)
            # Same noise-index function used in real-hardware mode -- here
            # it compares the exact vectors against themselves, so it's
            # always exactly 0.0%, an explicit "this is the noiseless
            # baseline" anchor to compare real QPU runs against later.
            sim_vectors = quantum_backend.marginal_bloch_vectors_from_statevector(statevec, 2)
            noise_pct = quantum_backend.get_noise_index(qc, sim_vectors, n_qubits=2)
            backend_tag = "simulator"
            metric_line = f"Concurrence = {c:.2f}   |   Noise index = {noise_pct:.1f}%"
            amp_line = "Joint state: " + edu_viz.format_statevector_line(statevec, n_qubits=2)

            fig = plt.figure(figsize=(12, 5.5))
            ax_dm = fig.add_subplot(1, 2, 1)
            edu_viz.add_density_matrix_grid(ax_dm, statevec, n_qubits=2)
            ax_corr = fig.add_subplot(1, 2, 2)
            edu_viz.add_correlator_bar_chart(ax_corr, correlators)

            edu_viz.add_boxed_title(fig, f"{formula}\n{metric_line}  [{backend_tag}]\n{amp_line}",
                                     fontsize=11, top=0.65, bottom=0.14, wspace=0.4)
        else:
            # --- real IBM hardware: Bloch vectors (meaningful here -- see
            # docstring) + correlator chart estimated from measurements ---
            witness = sum(abs(v) for v in correlators.values())
            # How far did the real QPU's measured Bloch vectors stray from
            # what an ideal, noiseless simulator predicts for this same
            # circuit? No extra hardware calls needed -- reuses `vectors`
            # (already measured above) against a locally-computed ideal.
            noise_pct = quantum_backend.get_noise_index(qc, vectors, n_qubits=2)
            backend_tag = "real QPU"
            metric_line = (f"|<XX>|+|<YY>|+|<ZZ>| = {witness:.2f}  (witness)"
                            f"   |   Noise index = {noise_pct:.1f}% (vs ideal simulation)")
            amp_line = "Joint state amplitudes unavailable on real hardware (measurement statistics only)"

            fig = plt.figure(figsize=(12, 5.5))
            for i, vec in enumerate(vectors):
                norm = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
                ax = fig.add_subplot(1, 3, i + 1, projection='3d')
                plot_bloch_vector(vec, ax=ax, title=f"qubit {i}  |v| = {norm:.2f}",
                                   font_size=13)
            ax_corr = fig.add_subplot(1, 3, 3)
            edu_viz.add_correlator_bar_chart(ax_corr, correlators)

            edu_viz.add_boxed_title(fig, f"{formula}\n{metric_line}  [{backend_tag}]\n{amp_line}",
                                     fontsize=11, top=0.62, bottom=0.08, wspace=0.35)

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