#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quantum enhanced memory matching game (Qt 6 + Qiskit 2.2.3 + Aer 0.17.2).

EXPERIMENT 1 -- NO ENTANGLEMENT. This is the deliberate "before" picture
for the other four experiments: each matched pair is shown as two
completely INDEPENDENT qubits (no cx/cz, no correlation of any kind),
one with a fixed quantum-random pure state and the other set to its
exact antipode on the Bloch sphere -- always pointing in exactly
opposite directions, purely as a visual choice, not a physical
correlation. Compare this popup with Experiments 2-5's: here both Bloch
arrows are always full length and point opposite each other; there,
entanglement makes at least one of them shrink or ties their measurement
outcomes together. Concurrence is always exactly 0.00 here.

* UI is built completely in Python (no .ui file).
* Deck (sign + emoji) is generated once by a quantum circuit.
* Hidden cards are black with a white “❓”.
* Revealed cards are white with black text.
* After a correct match a modal popup shows the two INDEPENDENT random
  qubits associated with that emoji (not entangled -- see Experiments 2-5 for that).
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
        self.setWindowTitle("Two Independent Qubits — No Entanglement")
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
        self.setWindowTitle("Schrödinger Memory (Experiment 1 — no entanglement)")
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
        # 6.2b Give each emoji pair two OPPOSITE random qubit states
        # -------------------------------------------------
        # Each of the 8 emojis gets ONE quantum-random angle thetaA,
        # drawn once here; thetaB is set to its exact antipode
        # (thetaA + pi). Since ry(theta) places the Bloch vector at
        # (sin theta, 0, cos theta), adding pi negates both components,
        # so qubit B's arrow always points exactly opposite qubit A's --
        # geometric opposites through the sphere's center. This is
        # STILL not entanglement: qubit A and qubit B are prepared by
        # two completely separate ry gates with no interaction between
        # them (no cx/cz anywhere in this experiment), so their measurement
        # outcomes remain fully independent and concurrence stays
        # exactly 0.00 -- "opposite" here is a deliberate choice of
        # which two independent pure states to prepare, not a physical
        # correlation between them.
        import math
        self.pair_angles = {}
        for emoji in EMOJIS:
            theta_a = quantum_backend.generate_random_angle(0, math.pi)
            theta_b = (theta_a + math.pi) % (2 * math.pi)   # antipodal vector
            self.pair_angles[emoji] = (theta_a, theta_b)

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

                # Show the two independent random qubits for this emoji
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
    # 6.9 Bloch‑sphere popup for the two independent qubits of a match
    # -----------------------------------------------------------------
    def show_bloch_pair(self, first_lbl: str, second_lbl: str):
        """
        Build TWO COMPLETELY INDEPENDENT single-qubit states -- no
        entangling gate at all. Each emoji has one quantum-random angle
        thetaA (self.pair_angles, set in __init__); qubit B's angle is
        thetaA's exact antipode, so the two Bloch arrows always point in
        exactly opposite directions through the sphere's center. Card
        sign plays no role here (there's nothing to encode into a
        correlation, since there is no correlation). Backend (simulator
        or real IBM hardware) is selected entirely by config.BACKEND_MODE.

        This is the deliberate contrast to Experiments 2-5: since there's no
        entanglement, each qubit has a perfectly well-defined pure state
        of its own, so BOTH Bloch arrows are always full length
        (|v| = 1.00) -- compare with Experiments 2-5, where entanglement makes the
        marginal arrows shrink (down to exactly 0 for maximal
        entanglement). Concurrence here is always 0.00 -- the two arrows
        being antipodal is a deliberate visual choice, not a physical
        correlation between the qubits. The third panel shows each
        qubit's OWN P(|0>)/P(|1>) instead of a joint-outcome chart: a
        joint chart here would still be a valid probability distribution,
        but its shape (forced by the antipodal angles) can visually
        resemble a correlated pattern even though there's none -- showing
        each qubit's independent probability directly avoids that
        confusion.
        """
        emoji = first_lbl[1:]                     # matched cards share the same emoji
        theta_a, theta_b = self.pair_angles[emoji]  # fixed for this emoji, drawn once in __init__

        qc = QuantumCircuit(2)
        qc.ry(theta_a, 0)                  # qubit A: its own independent random state
        qc.ry(theta_b, 1)                  # qubit B: exact antipode of qubit A's state
        # NOTE: no cx/cz here -- that absence is the entire point of this
        # experiment. Card sign is intentionally unused: with no entangling
        # gate there is no correlation for a sign to encode.

        formula = (f"qubit A: cos({theta_a/2:.2f})|0⟩+sin({theta_a/2:.2f})|1⟩   "
                   f"qubit B: cos({theta_b/2:.2f})|0⟩+sin({theta_b/2:.2f})|1⟩  (B = antipode of A)")

        # qc has state-prep gates only (no measure/save_statevector) -- the
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
            metric_line = (f"Concurrence = {c:.2f}  (NOT entangled -- opposite arrows, independent qubits)"
                            f"   |   Noise index = {noise_pct:.1f}%")
            # Even a product state has a well-defined joint statevector --
            # it's just the two qubits' amplitudes multiplied together,
            # with no cross-correlation. Contrast with Experiments 2-5's amplitude
            # readout, which only has weight on 2 of the 4 basis states.
            amp_line = "Joint state: " + edu_viz.format_statevector_line(statevec, n_qubits=2)
        else:
            # --- real IBM hardware: vectors estimated from measurements ---
            witness = quantum_backend.get_entanglement_witness(qc)
            # How far did the real QPU's measured Bloch vectors stray from
            # what an ideal, noiseless simulator predicts for this same
            # circuit? No extra hardware calls needed -- reuses `vectors`
            # (already measured above) against a locally-computed ideal.
            noise_pct = quantum_backend.get_noise_index(qc, vectors, n_qubits=2)
            backend_tag = "real QPU"
            metric_line = (f"|<XX>|+|<YY>|+|<ZZ>| = {witness:.2f}  (should read ~0, no entanglement)"
                            f"   |   Noise index = {noise_pct:.1f}% (vs ideal simulation)")
            amp_line = "Joint state amplitudes unavailable on real hardware (measurement statistics only)"

        fig = plt.figure(figsize=(12, 5.5))
        for i, vec in enumerate(vectors):
            norm = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
            ax = fig.add_subplot(1, 3, i + 1, projection='3d')
            # |v| = 1.00 here -- always, for every pair -- because these
            # are genuine pure states with no entanglement to mix them.
            # qubit 1's arrow always points exactly opposite qubit 0's.
            plot_bloch_vector(vec, ax=ax, title=f"qubit {i}  |v| = {norm:.2f}",
                               font_size=13)
        ax_bar = fig.add_subplot(1, 3, 3)
        # Per-qubit P(0)/P(1), NOT a joint outcome chart: each qubit's own
        # probability is well-defined on its own, unrelated to the other --
        # that's the actual, direct signature of "not entangled" (a joint
        # chart alone can visually resemble a correlated pattern here,
        # purely because of the antipodal angle choice -- see conversation).
        edu_viz.add_per_qubit_probability_chart(ax_bar, vectors)

        edu_viz.add_boxed_title(fig, f"{formula}\n{metric_line}  [{backend_tag}]\n{amp_line}",
                                 fontsize=11, top=0.62, bottom=0.16, wspace=0.35)

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