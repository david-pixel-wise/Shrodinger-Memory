#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Small, backend-agnostic plotting helpers shared by all four game experiments.

These only ever draw onto an Axes the caller already created (fig.add_subplot),
so every experiment keeps building a single matplotlib Figure that goes into the
one unchanged BlochDialog — no new windows, buttons, or panels are added
anywhere. This module exists purely so the educational panels (Bloch vectors,
probability bar chart, correlation heatmap, correlator bar chart, concurrence
trend) are written once instead of duplicated four times.

Font sizes here are deliberately larger than matplotlib's defaults -- the
popup is meant to be read at a glance during a game, not zoomed into.
"""

TITLE_FS = 13
LABEL_FS = 11
TICK_FS = 10
ANNOT_FS = 10


def add_boxed_title(fig, text, fontsize=11.5, y=0.95, top=0.62, bottom=0.08, wspace=0.35):
    """
    Draws the popup's multi-line title/metrics text inside a colored,
    rounded box at the top of the figure, instead of a plain
    fig.suptitle() call -- visually separates the text from the charts
    below it. Replaces the fig.suptitle(...) + fig.subplots_adjust(...)
    pair used at every call site before: this handles both in one call.

    top/bottom/wspace are passed straight to fig.subplots_adjust() so
    each experiment can keep its own panel spacing (a 2-panel layout needs
    different margins than a 3-panel one); only the title's own styling
    (fontsize, y, box appearance) is fixed here.
    """
    fig.text(0.5, y, text, ha='center', va='top', fontsize=fontsize,
              bbox=dict(boxstyle='round,pad=0.7', facecolor='#EAF0FA',
                        edgecolor='#4C72B0', linewidth=1.8))
    fig.subplots_adjust(top=top, bottom=bottom, wspace=wspace)


def format_statevector_line(statevec, n_qubits=2):
    """
    Format the joint statevector's complex amplitudes as a single text
    line, e.g. "|00>: +0.71+0.00i   |01>: +0.00+0.00i   ...". This is
    only meaningful in simulator mode -- an individual qubit inside an
    entangled pair does NOT have its own complex amplitude (that's
    exactly why its Bloch vector sits at the center: it's in a mixed
    state, not describable by a single ket). Only the *joint* two-qubit
    system has well-defined amplitudes, which is what this shows.
    Real hardware can't provide this at all (no exact statevector), so
    callers should only use this when statevec is not None.
    """
    from qiskit.quantum_info import Statevector

    sv = Statevector(statevec)
    parts = []
    for i, amp in enumerate(sv.data):
        label = format(i, f'0{n_qubits}b')
        parts.append(f"|{label}⟩: {amp.real:+.2f}{amp.imag:+.2f}i")
    return "   ".join(parts)


def add_probability_bar_chart(ax, probs, n_qubits=2,
                               title="Joint outcome probabilities"):
    """
    probs: dict {bitstring: probability}, as returned by
    quantum_backend.get_basis_probabilities(). Draws one bar per computational
    basis state (00, 01, 10, 11, ...). This is the same joint distribution
    whether it came from an exact statevector (simulator) or from measurement
    counts (real IBM hardware) -- it's what directly shows *why* a pair looks
    correlated: e.g. only "00" and "11" having weight is the visual signature
    of a Φ-type Bell state.
    """
    labels = [format(i, f'0{n_qubits}b') for i in range(2 ** n_qubits)]
    values = [probs.get(lbl, 0.0) for lbl in labels]

    ax.bar(labels, values, color="#4C72B0")
    ax.set_ylim(0, 1.10)
    ax.set_ylabel("Probability", fontsize=LABEL_FS)
    ax.set_title(title, fontsize=TITLE_FS)
    ax.tick_params(labelsize=TICK_FS)
    for i, v in enumerate(values):
        ax.text(i, v + 0.03, f"{v:.2f}", ha='center', fontsize=ANNOT_FS)


def add_per_qubit_probability_chart(ax, vectors, title="Per-qubit measurement probabilities"):
    """
    vectors: list of [x,y,z] Bloch vectors, one per qubit (already computed
    elsewhere via quantum_backend.get_bloch_vectors /
    marginal_bloch_vectors_from_statevector). Plots each qubit's OWN
    P(|0>) and P(|1>) as grouped bars, computed directly from that
    qubit's Bloch-vector Z-component: P(0) = (1+z)/2, P(1) = (1-z)/2.

    This is the more direct way to show "these two qubits are
    independent" than a joint-outcome bar chart: it shows each qubit
    genuinely HAS its own well-defined probability distribution on its
    own, unrelated to the other -- which is only true because there is
    no entanglement. For an entangled pair, plotting each qubit's own
    P(0)/P(1) this way would be misleading (a maximally mixed marginal
    always reads 50/50 regardless of how strongly correlated the pair
    actually is), which is exactly why the other experiments show a JOINT
    outcome chart instead -- the two panels are answering different
    questions, matched to whichever is meaningful for that experiment.
    """
    import numpy as np

    n = len(vectors)
    p0 = [(1 + v[2]) / 2 for v in vectors]
    p1 = [(1 - v[2]) / 2 for v in vectors]
    x = np.arange(n)
    width = 0.35

    ax.bar(x - width / 2, p0, width, label='P(|0⟩)', color="#4C72B0")
    ax.bar(x + width / 2, p1, width, label='P(|1⟩)', color="#DD8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"qubit {i}" for i in range(n)], fontsize=TICK_FS)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Probability", fontsize=LABEL_FS)
    ax.set_title(title, fontsize=TITLE_FS)
    # Placed below the axes (not 'upper center') -- inside the plot area
    # it collided with the tall bars and their value labels.
    ax.legend(fontsize=ANNOT_FS, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)
    for i in range(n):
        ax.text(x[i] - width / 2, p0[i] + 0.03, f"{p0[i]:.2f}", ha='center', fontsize=ANNOT_FS)
        ax.text(x[i] + width / 2, p1[i] + 0.03, f"{p1[i]:.2f}", ha='center', fontsize=ANNOT_FS)


def add_density_matrix_grid(ax, statevec, n_qubits=2, title="Density matrix — sign & magnitude"):
    """
    A colored grid of the 2-qubit density matrix rho_ij: each cell's
    SIZE is |rho_ij| (magnitude) and its COLOR is the sign of the real
    part (blue = positive, red = negative). All circuits in this game
    only ever produce real amplitudes (confirmed -- none of h/x/z/cx/cz/
    ry introduce a complex phase starting from |00>), so sign alone
    fully captures what a general phase-color plot would need a full
    hue wheel for; using two strong, distinct colors here reads far more
    clearly than a muted phase gradient would for a binary +/- case.

    This directly answers "how do the four Bell states differ?": they
    share the same diagonal (which basis states have any weight at all)
    but differ in which OFF-diagonal cells are blue vs red -- e.g. Φ+
    is all-blue, Φ- has its top-right block flip to red, Ψ- alternates
    diagonally. Position tells you WHICH pair of basis states are
    involved (Φ family: |00>,|11> corners; Ψ family: |01>,|10> center);
    color tells you the relative sign between them.
    """
    from qiskit.quantum_info import Statevector, DensityMatrix
    import matplotlib.pyplot as plt

    rho = DensityMatrix(Statevector(statevec)).data
    labels = [format(i, f'0{n_qubits}b') for i in range(2 ** n_qubits)]
    n = len(labels)

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(-0.5, n - 0.5)
    ax.invert_yaxis()
    ax.set_facecolor("#f5f5f5")

    for i in range(n):
        for j in range(n):
            val = rho[i, j].real
            mag = abs(val)
            if mag > 1e-3:
                color = "#4C72B0" if val > 0 else "#C44E52"
                size = min(mag / 0.5, 1.0) * 0.85
                rect = plt.Rectangle((j - size / 2, i - size / 2), size, size,
                                      facecolor=color, edgecolor='black', linewidth=0.6)
                ax.add_patch(rect)

    ax.set_xticks(range(n))
    ax.set_xticklabels([f"|{lbl}⟩" for lbl in labels], fontsize=TICK_FS)
    ax.set_yticks(range(n))
    ax.set_yticklabels([f"|{lbl}⟩" for lbl in labels], fontsize=TICK_FS)
    ax.set_aspect('equal')
    ax.grid(True, color='white', linewidth=1.5)
    ax.set_title(title, fontsize=TITLE_FS)

    from matplotlib.patches import Patch
    legend_elems = [Patch(facecolor="#4C72B0", label='positive'),
                    Patch(facecolor="#C44E52", label='negative')]
    ax.legend(handles=legend_elems, loc='upper center', bbox_to_anchor=(0.5, -0.12),
              ncol=2, fontsize=ANNOT_FS, frameon=False)


def add_probability_heatmap(ax, probs, title="Joint probability heatmap"):
    """
    2-qubit only: reshapes the same joint distribution used by the bar chart
    into a 2x2 grid (q1 rows x q0 columns) and colors it by probability.
    Same underlying data as the bar chart, different visual language --
    some players read a correlation grid more easily than a bar chart.

    NOTE: some entangled states have a perfectly flat probability grid
    (every cell 0.25) -- their correlation only shows up in a different
    measurement basis. add_correlator_bar_chart() below is the panel for
    that case; don't use this heatmap for such states, it won't show
    anything useful (see Experiment 5).
    """
    import numpy as np

    grid = np.zeros((2, 2))
    for bits, p in probs.items():
        b = bits.zfill(2)
        q1, q0 = int(b[-2]), int(b[-1])
        grid[q1][q0] = p

    im = ax.imshow(grid, cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["q0=0", "q0=1"], fontsize=TICK_FS)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["q1=0", "q1=1"], fontsize=TICK_FS)
    for i in range(2):
        for j in range(2):
            color = "white" if grid[i][j] < 0.5 else "black"
            ax.text(j, i, f"{grid[i][j]:.2f}", ha='center', va='center',
                     color=color, fontsize=ANNOT_FS + 1)
    ax.set_title(title, fontsize=TITLE_FS)
    return im


def add_correlator_bar_chart(ax, correlators,
                              title="Two-qubit correlators ⟨XX⟩ ⟨YY⟩ ⟨ZZ⟩"):
    """
    correlators: dict {'XX': v, 'YY': v, 'ZZ': v} as returned by
    quantum_backend.get_pauli_correlators(). Some entangled states (e.g.
    Experiment 5's H+H+CZ construction) have a perfectly flat computational-basis
    (Z-basis) probability distribution -- nothing to see in a bar chart
    or heatmap of outcomes. Their entanglement only becomes visible when
    you measure in a different basis: this panel shows exactly that,
    plotting all three two-qubit correlators from -1 (perfect anti-
    correlation) to +1 (perfect correlation), so a spike in X or Y even
    while Z sits near zero is the visible signature of "this pair is
    entangled, just not in the basis you were looking at."
    """
    labels = ["⟨XX⟩", "⟨YY⟩", "⟨ZZ⟩"]
    values = [correlators.get(k, 0.0) for k in ("XX", "YY", "ZZ")]
    colors = ["#55A868" if abs(v) > 0.5 else "#4C72B0" for v in values]

    ax.bar(labels, values, color=colors)
    ax.set_ylim(-1.25, 1.25)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Expectation value", fontsize=LABEL_FS)
    ax.set_title(title, fontsize=TITLE_FS)
    ax.tick_params(labelsize=TICK_FS)
    for i, v in enumerate(values):
        offset = 0.08 if v >= 0 else -0.14
        ax.text(i, v + offset, f"{v:.2f}", ha='center', fontsize=ANNOT_FS)


def add_concurrence_trend(ax, history, title="Concurrence across matches this game"):
    """
    history: list of concurrence values, one per match so far, in order.
    Only meaningful for a experiment where entanglement strength actually
    changes match to match (Experiment 4); shows the whole game's progression on
    every popup, not just the current pair's number.
    """
    xs = list(range(1, len(history) + 1))
    ax.plot(xs, history, marker='o', color="#C44E52")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Pair #", fontsize=LABEL_FS)
    ax.set_ylabel("Concurrence", fontsize=LABEL_FS)
    ax.set_title(title, fontsize=TITLE_FS)
    ax.tick_params(labelsize=TICK_FS)
    ax.set_xticks(xs)
