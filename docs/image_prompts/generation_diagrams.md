# LaTeX / TikZ Code — Data Generation Diagrams

Each section below is a **complete, self-contained LaTeX document** that compiles
to the diagram referenced in `sonar_sim/generation/README.md`.

## How to compile

```bash
# Any diagram
pdflatex IMG-GEN-01.tex
# Convert PDF to high-res PNG for GitHub
pdftoppm -r 300 IMG-GEN-01.pdf IMG-GEN-01 -png
# Or with ImageMagick
convert -density 300 IMG-GEN-01.pdf -quality 95 IMG-GEN-01.png
```

Save the compiled PNG files in `docs/images/generation/` and replace the
`[IMG-GEN-XX]` placeholders in `sonar_sim/generation/README.md` with
`![description](../../docs/images/generation/filename.png)`.

**Required LaTeX packages** (all included in TeX Live full / MiKTeX):
`tikz`, `pgfplots`, `amsmath`, `amssymb`, `xcolor`, `geometry`, `fontenc`,
`inputenc`, `pgfarrows`, `tikz-3dplot`

---

## IMG-GEN-01 — Active vs Passive SONAR

**Target file:** `docs/images/generation/sonar_active_vs_passive.png`
**Aspect ratio:** 16:9 — compile with `\paperwidth=32cm, \paperheight=18cm`

```latex
\documentclass[tikz, border=8pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, shapes.geometric, positioning, decorations.pathmorphing,
                decorations.markings, backgrounds, fit}

% ── Colour palette ──────────────────────────────────────────────────────────
\definecolor{navybg}{HTML}{0d1b2a}
\definecolor{cyanEl}{HTML}{00d4ff}
\definecolor{amberTgt}{HTML}{ffb347}
\definecolor{greenPulse}{HTML}{39d353}
\definecolor{greyWave}{HTML}{8a9bb5}
\definecolor{panelBg}{HTML}{162032}

\begin{document}
\begin{tikzpicture}[
    font=\sffamily\small,
    background rectangle/.style={fill=navybg},
    show background rectangle,
    every node/.style={text=white}
]

%% ── DIVIDE LINE ─────────────────────────────────────────────────────────────
\draw[white, dashed, thick] (8,0) -- (8,12);

%% ══════════════════════════════════════════════════════════════════════════
%%  LEFT PANEL — ACTIVE SONAR
%% ══════════════════════════════════════════════════════════════════════════
\node[white, font=\sffamily\large\bfseries] at (4,11.3)
    {ACTIVE SONAR};

%% Source submarine (left side)
\node[amberTgt, font=\sffamily\footnotesize] at (1.5,7.5) {Source};
% Submarine body
\draw[amberTgt, thick, rounded corners=4pt]
    (0.5,6.8) rectangle (2.5,7.2);
\draw[amberTgt, thick] (2.5,7.0) -- (3.0,7.0);          % tail
\draw[amberTgt, thick] (1.2,7.2) -- (1.2,7.6) -- (1.6,7.6); % conning tower

%% Expanding pulse wavefronts (3 arcs, rightward)
\foreach \r/\op in {1.2/0.9, 2.2/0.6, 3.2/0.3}{
    \draw[greenPulse, thick, opacity=\op]
        (3.0,7.0) arc[start angle=20, end angle=-20, radius=\r*2.5];
}
\node[greenPulse, font=\sffamily\footnotesize] at (5.0,7.8)
    {Transmitted Pulse};

%% Target submarine (right side)
\draw[greyWave, thick, rounded corners=4pt]
    (5.8,6.8) rectangle (7.6,7.2);
\draw[greyWave, thick] (7.6,7.0) -- (8.0,7.0);
\draw[greyWave, thick] (6.4,7.2) -- (6.4,7.6) -- (6.8,7.6);
\node[greyWave, font=\sffamily\footnotesize] at (6.8,7.5) {Target};

%% Echo arc back (leftward, dashed)
\draw[greenPulse!60, thick, dashed, ->, >=Stealth]
    (5.8,7.0) .. controls (4.5,8.5) .. (3.0,7.2);
\node[greenPulse!80, font=\sffamily\footnotesize] at (4.4,8.8) {Echo};

%% Round-trip time annotation
\draw[white, <->, >=Stealth, thin]
    (1.5,5.8) -- (7.0,5.8);
\node[white, font=\sffamily\footnotesize] at (4.2,5.4)
    {Round-trip time $\Delta t = \frac{2R}{c}$ \quad $\Rightarrow$ Range $R$};

%% Emits signature warning
\node[red!70, font=\sffamily\footnotesize\itshape] at (4.0,4.6)
    {\textbf{$\times$} Emits detectable acoustic signature};
\node[greenPulse!80, font=\sffamily\footnotesize\itshape] at (4.0,4.0)
    {\textbf{\checkmark} Obtains range information};

%% ══════════════════════════════════════════════════════════════════════════
%%  RIGHT PANEL — PASSIVE SONAR
%% ══════════════════════════════════════════════════════════════════════════
\node[white, font=\sffamily\large\bfseries] at (12,11.3)
    {PASSIVE SONAR};

%% Towing ship (surface, top-right area)
\draw[white, thick, rounded corners=2pt]
    (9.2,9.2) rectangle (11.0,9.6);   % hull
\draw[white, thick] (9.8,9.6) -- (9.8,10.0) -- (10.4,10.0); % superstructure

%% Tow cable
\draw[white, thick] (10.0,9.2) -- (10.0,8.0)
    [postaction={decorate, decoration={markings,
        mark=at position 0.5 with {\node[white, right=2pt,
            font=\sffamily\tiny]{Tow cable};}}}];

%% ULA — 8 hydrophone elements on a horizontal line
\draw[white, thin] (9.0,7.5) -- (15.5,7.5);
\foreach \i in {0,1,...,7}{
    \draw[cyanEl, fill=cyanEl!30, thick]
        ({9.2 + \i*0.9}, 7.5) circle (0.18);
    \node[cyanEl, font=\sffamily\tiny] at ({9.2 + \i*0.9}, 7.15)
        {\i};
}
\node[cyanEl, font=\sffamily\footnotesize] at (12.3,6.7)
    {Towed ULA — 32 hydrophones};

%% Distant target submarine (upper left of right panel)
\draw[amberTgt, thick, rounded corners=3pt]
    (8.4,10.5) rectangle (9.8,10.9);
\draw[amberTgt, thick] (9.8,10.7) -- (10.2,10.7);
\node[amberTgt, font=\sffamily\footnotesize] at (9.1,11.1) {Target};

%% Wavefronts from target toward array (3 arc lines)
\foreach \r/\op in {1.0/0.9, 1.8/0.6, 2.6/0.3}{
    \draw[greyWave, thick, opacity=\op]
        (9.8,10.7)
        arc[start angle=210, end angle=270, radius=\r*1.8];
}
\node[greyWave, font=\sffamily\footnotesize] at (11.5,9.3)
    {Acoustic wavefronts};

%% Arrival time tick-marks on elements (progressive offset)
\foreach \i in {0,1,...,7}{
    \pgfmathsetmacro{\yoff}{-0.4 - \i*0.07}
    \draw[cyanEl!70, thin]
        ({9.2 + \i*0.9}, {7.5 + \yoff - 0.1})
        -- ({9.2 + \i*0.9}, {7.5 + \yoff + 0.1});
}
\node[white, font=\sffamily\tiny] at (12.3,6.3)
    {Progressive arrival times $\tau_n = n \cdot \frac{d\cos\theta}{c}$};

%% No-emission note
\node[greenPulse!80, font=\sffamily\footnotesize\itshape] at (12.3,5.0)
    {\textbf{\checkmark} Zero acoustic emission — undetectable};
\node[red!70, font=\sffamily\footnotesize\itshape] at (12.3,4.4)
    {\textbf{$\times$} No range — bearing angle $\theta$ only};

%% ── Bottom caption ───────────────────────────────────────────────────────
\node[white!70, font=\sffamily\footnotesize] at (8,2.8)
    {Sound speed in seawater: $c \approx 1500\,\text{m/s}$
     \quad (vs.\ $343\,\text{m/s}$ in air)
     \quad — acoustics is the only long-range underwater sensing modality};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-02 — Towed Array Wavefront Geometry

**Target file:** `docs/images/generation/towed_array_wavefront.png`
**Aspect ratio:** 3:2

```latex
\documentclass[tikz, border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, decorations.markings, angles, quotes, calc}

\definecolor{waveBlue}{HTML}{1a6eb5}
\definecolor{sensorBlue}{HTML}{2196f3}
\definecolor{pathRed}{HTML}{d32f2f}
\definecolor{annoOrange}{HTML}{e65100}

\begin{document}
\begin{tikzpicture}[
    font=\sffamily\small,
    >=Stealth
]

% ── Parameters (all in TikZ units = cm) ─────────────────────────────────
% 8 sensors, spacing d represented as 1.8 units
\def\d{1.8}       % element spacing in drawing units
\def\N{8}         % number of elements shown
\def\theta{35}    % bearing from broadside in degrees → wavefront angle from vertical

% ── Array baseline ───────────────────────────────────────────────────────
\foreach \i in {0,1,...,7}{
    \pgfmathsetmacro{\x}{\i * \d}
    \draw[sensorBlue, fill=sensorBlue!20, thick] (\x, 0) circle (0.2);
    \node[below=4pt, font=\sffamily\footnotesize] at (\x, 0)
        {$n{=}\i$};
}
% Array axis label
\node[below=18pt] at (3.5*\d, 0) {ULA axis};

% ── Element spacing annotation ───────────────────────────────────────────
\draw[<->, thin] (0, -0.7) -- (\d, -0.7)
    node[midway, below, font=\sffamily\footnotesize]
    {$d = 0.1875\,\text{m}$};

% ── Incoming wavefront (diagonal line) ──────────────────────────────────
% Wavefront arrives from upper-left; the wavefront is perpendicular to
% the direction of propagation. Direction of propagation makes angle
% (90° - theta) with the array axis.
% Wavefront line passes through element 0 at y=0.
% Wavefront direction vector: (sin(theta), -cos(theta)) normalised
% We draw the wavefront as a line with slope = -cot(theta) shifted right

\pgfmathsetmacro{\waveslope}{cos(\theta)/sin(\theta)}   % slope dy/dx of wavefront

% Wavefront line through element 0 (x=0, y=0)
\draw[waveBlue, very thick, ->, shorten >=2pt]
    (-1.0, \waveslope*(-1.0))
    -- ({7*\d + 0.5}, {\waveslope*(7*\d+0.5)})
    node[above right, waveBlue] {Wavefront};

% ── Propagation direction arrow ──────────────────────────────────────────
\pgfmathsetmacro{\px}{sin(\theta)}
\pgfmathsetmacro{\py}{-cos(\theta)}
\draw[waveBlue, ->, thick]
    (3.0, 4.5)
    -- ({3.0 + 2*\px}, {4.5 + 2*\py})
    node[right, waveBlue, font=\sffamily\footnotesize]
    {Propagation direction};

% ── Bearing angle arc ────────────────────────────────────────────────────
% θ measured from broadside (vertical)
\draw[annoOrange, thin]
    (3.0, 4.5) -- (3.0, 6.5);   % broadside reference (vertical)
\draw[annoOrange, ->, thin]
    (3.0, 5.8) arc[start angle=90, end angle={90-\theta}, radius=1.3];
\node[annoOrange] at (3.6, 5.6) {$\theta$};

% ── Path-length difference construction ─────────────────────────────────
% For element 1 at x=d, y=0:
% The extra path length relative to element 0 is d*cos(theta).
% Draw right-triangle from element 0 to element 1 footprint on wavefront.

\pgfmathsetmacro{\footx}{\d * sin(\theta) * sin(\theta)}
\pgfmathsetmacro{\footy}{\d * sin(\theta) * (-cos(\theta))}
% Foot of perpendicular from element 1 onto the wavefront line through elem 0
% Wavefront unit normal: (sin(theta), -cos(theta))
% Projection of element-1 position (\d, 0) onto wavefront normal:
% proj = d * sin(theta)
% Foot = elem1 - proj * normal = (\d - d*sin^2, d*sin*cos)

\pgfmathsetmacro{\ex}{\d - \d*sin(\theta)*sin(\theta)}
\pgfmathsetmacro{\ey}{\d * sin(\theta) * cos(\theta)}

% Draw dashed path-length line from elem 1 down to wavefront
\draw[pathRed, dashed, thick] (\d, 0) -- (\ex, \ey);

% Path-length label
\pgfmathsetmacro{\midpx}{(\d + \ex)/2 + 0.3}
\pgfmathsetmacro{\midpy}{(\ey)/2}
\node[pathRed, right, font=\sffamily\footnotesize] at (\midpx, \midpy)
    {$d\cos\theta$};

% Right-angle mark at foot
\pgfmathsetmacro{\marksize}{0.12}
\draw[pathRed, thin]
    (\ex, \ey)
    -- ({\ex + \marksize*cos(\theta)}, {\ey + \marksize*sin(\theta)})
    -- ({\ex + \marksize*cos(\theta) - \marksize*sin(\theta)},
        {\ey + \marksize*sin(\theta) + \marksize*cos(\theta)})
    -- ({\ex - \marksize*sin(\theta)}, {\ey + \marksize*cos(\theta)});

% ── Arrival time timeline (below each element) ──────────────────────────
\def\timelineY{-1.4}
\def\timelineLen{0.9}

% Timeline axis
\draw[black!40, thin, ->]
    (-0.3, \timelineY) -- ({7*\d + 1.0}, \timelineY)
    node[right, font=\sffamily\footnotesize] {$t$};
\node[left, font=\sffamily\footnotesize] at (-0.3, \timelineY) {$\tau$};

% Dots for each sensor arrival time
% tau_n proportional to n; max tau at n=7 mapped to 0.7 units offset
\pgfmathsetmacro{\tscale}{0.5}   % scale: 1 unit of n maps to this many x-units
\foreach \i in {0,1,...,7}{
    \pgfmathsetmacro{\arrivalx}{\i * \d + \i * \tscale * 0.12}
    % vertical dashed line from element to timeline
    \draw[black!25, dashed, thin]
        ({\i*\d}, -0.3) -- ({\i*\d}, {\timelineY + 0.1});
    % dot
    \filldraw[sensorBlue]
        ({\i*\d + \i*0.08}, \timelineY) circle (0.07);
}
\node[font=\sffamily\tiny, text=black!60] at (3.5*\d, \timelineY - 0.4)
    {Progressive arrival: $\tau_n = n \cdot \dfrac{d\cos\theta}{c}$};

% ── Legend box ──────────────────────────────────────────────────────────
\draw[black!40, rounded corners=4pt, thin]
    (10.5, 1.5) rectangle (15.5, 5.5);
\node[above, font=\sffamily\footnotesize\bfseries] at (13.0, 5.2)
    {Legend};
\node[anchor=west, font=\sffamily\footnotesize] at (10.8, 4.6)
    {$\theta$ — bearing from broadside};
\node[anchor=west, font=\sffamily\footnotesize] at (10.8, 4.0)
    {$d = 0.1875\,\text{m}$ — element spacing};
\node[anchor=west, font=\sffamily\footnotesize] at (10.8, 3.4)
    {$c = 1500\,\text{m/s}$ — sound speed};
\node[anchor=west, font=\sffamily\footnotesize] at (10.8, 2.8)
    {$\tau_n = n \cdot \dfrac{d\cos\theta}{c}$ — delay at sensor $n$};
\node[anchor=west, font=\sffamily\footnotesize] at (10.8, 2.0)
    {$\mathbf{Y} = [\mathbf{y}_0\;\mathbf{y}_1\;\cdots\;\mathbf{y}_{N-1}]
     \in\mathbb{R}^{T\times N}$};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-03 — Array Data Model: Y = S + Z

**Target file:** `docs/images/generation/array_data_model.png`
**Aspect ratio:** 4:3

```latex
\documentclass[tikz, border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, shapes.geometric, positioning, fit, backgrounds, calc}

\definecolor{blockBlue}{HTML}{1565c0}
\definecolor{delayOrange}{HTML}{e65100}
\definecolor{sumRed}{HTML}{c62828}
\definecolor{noiseGreen}{HTML}{2e7d32}
\definecolor{arrayGray}{HTML}{546e7a}

\tikzset{
  sigblock/.style={
    draw=blockBlue, fill=blockBlue!12, thick,
    rectangle, rounded corners=3pt,
    minimum width=1.6cm, minimum height=0.7cm,
    font=\sffamily\footnotesize, text=blockBlue
  },
  delayblock/.style={
    draw=delayOrange, fill=delayOrange!12, thick,
    rectangle,
    minimum width=1.2cm, minimum height=0.7cm,
    font=\sffamily\footnotesize, text=delayOrange
  },
  sumnode/.style={
    draw=sumRed, fill=sumRed!10, thick,
    circle, minimum size=0.7cm,
    font=\sffamily\bfseries, text=sumRed
  },
  sensor/.style={
    draw=arrayGray, fill=arrayGray!20, thick,
    circle, minimum size=0.55cm,
    font=\sffamily\footnotesize
  }
}

\begin{document}
\begin{tikzpicture}[>=Stealth, font=\sffamily\small]

%% ── ULA (top section) ───────────────────────────────────────────────────
\foreach \i/\lbl in {0/1, 1/2, 2/3, 3/{$\cdots$}, 4/N}{
    \node[sensor] (s\i) at ({2.5*\i}, 5.5) {\lbl};
}
% Array baseline
\draw[arrayGray, thick]
    (-0.5, 5.5) -- ({2.5*4 + 0.5}, 5.5);
\node[arrayGray, below=6pt] at (5.0, 5.5)
    {Uniform Linear Array (ULA) — $N$ hydrophones};

%% ── Source arrows from above ────────────────────────────────────────────
% Target 1 — from upper left
\draw[blockBlue, ->, thick]
    (-1.5, 9.5) -- (s0.north)
    node[midway, left=2pt, font=\sffamily\footnotesize, blockBlue]
    {Target$_1$\;($\theta_1$)};

% Target 2 — from upper centre
\draw[blockBlue!70, ->, thick]
    (3.5, 9.5) -- (s2.north)
    node[midway, right=2pt, font=\sffamily\footnotesize, blockBlue!70]
    {Target$_2$\;($\theta_2$)};

% Self-noise — from upper right, fixed 15°
\draw[delayOrange, ->, thick]
    (9.5, 9.5) -- (s4.north)
    node[midway, right=2pt, font=\sffamily\footnotesize, delayOrange]
    {Self-noise ($15°$)};

% Ambient noise — horizontal arrows from both sides
\draw[noiseGreen, ->, thick] (-2.0, 5.5) -- (s0.west)
    node[midway, above, font=\sffamily\footnotesize, noiseGreen]
    {$\eta_n(t)$};
\draw[noiseGreen, ->, thick] (12.5, 5.5) -- (s4.east);

%% ── Signal flow for sensor n (below the array) ──────────────────────────
\node[font=\sffamily\footnotesize\bfseries, arrayGray] at (5.0, 4.5)
    {Signal flow at sensor $n$:};

% Self-noise path
\node[sigblock]  (iblock)  at (0.0, 3.0) {$i(t)$};
\node[delayblock](itau)    at (2.2, 3.0) {$\tau_n$};
\draw[->] (iblock) -- (itau);

% Target s_1 path
\node[sigblock]  (s1block) at (0.0, 1.8) {$s_1(t)$};
\node[delayblock](s1tau)   at (2.2, 1.8) {$\tau_{n,1}$};
\draw[->] (s1block) -- (s1tau);

% Target s_2 path
\node[sigblock]  (s2block) at (0.0, 0.6) {$s_2(t)$};
\node[delayblock](s2tau)   at (2.2, 0.6) {$\tau_{n,2}$};
\draw[->] (s2block) -- (s2tau);

% Ellipsis
\node at (0.0, -0.4) {$\vdots$};
\node at (2.2, -0.4) {$\vdots$};

% Summing node
\node[sumnode] (sum) at (5.0, 1.8) {$+$};

% Connect delay outputs to sum
\draw[->] (itau.east)  -| (sum.north);
\draw[->] (s1tau.east) -- (sum.west);
\draw[->] (s2tau.east) -| (sum.south);

% Ambient noise enters sum from below
\node[noiseGreen, sigblock, draw=noiseGreen, fill=noiseGreen!10,
      text=noiseGreen] (nblock) at (5.0, -0.6)
    {$\eta_n(t)$};
\draw[->, noiseGreen] (nblock.north) -- (sum.south);

% Output
\draw[->] (sum.east) -- ++(2.0, 0)
    node[right, font=\sffamily\footnotesize]
    {$y_n(t)$};

%% ── Full equation ───────────────────────────────────────────────────────
\node[font=\sffamily\footnotesize, anchor=west] at (0.0, -1.6)
    {$y_n(t) = \displaystyle\sum_j s_j\!\left(t - \tau_{n,j}\right)
      \;+\; i\!\left(t - \tau_n\right) \;+\; \eta_n(t)$};

%% ── Matrix form ─────────────────────────────────────────────────────────
\node[draw=black!30, rounded corners=4pt, fill=black!4,
      font=\sffamily\footnotesize, inner sep=8pt]
      (matbox) at (5.0, -3.2) {%
    $\underbrace{\mathbf{Y}}_{\in\,\mathbb{R}^{T\times N}}
     \;=\;
     \underbrace{\mathbf{S}(\theta)}_{\text{target field}}
     \;+\;
     \underbrace{\mathbf{Z}}_{\text{self-noise + ambient}}$
};

% Brace labels
\node[blockBlue, font=\sffamily\tiny, below=2pt] at (matbox.south)
    {$\mathbf{Y},\mathbf{S},\mathbf{Z}\in\mathbb{R}^{T\times N}$
     \quad $T$ = time samples, $N$ = sensors};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-04 — BB0 Narrowband Source Waveform

**Target file:** `docs/images/generation/bb0_narrowband_waveform.png`
**Aspect ratio:** 3:2 — use `pgfplots`

```latex
\documentclass{standalone}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{amsmath}
\usepackage{xcolor}

\definecolor{toneBlue}{HTML}{1565c0}
\definecolor{selfOrange}{HTML}{e65100}

\begin{document}
\begin{tikzpicture}
\begin{axis}[
  %% ── layout ────────────────────────────────────────────────────────
  name=timeplot,
  width=12cm, height=5cm,
  xmin=0, xmax=3,
  ymin=-1.3, ymax=1.3,
  xlabel={Time (ms)},
  ylabel={Amplitude},
  title={\textbf{BB0 — Time Domain:}
         $s(t) = A\sin\!\left(2\pi \cdot 1300 \cdot t\right)$},
  xtick={0,0.5,1.0,1.5,2.0,2.5,3.0},
  ytick={-1,0,1},
  grid=both, grid style={black!8},
  axis lines=left,
  tick label style={font=\sffamily\footnotesize},
  label style={font=\sffamily\small},
  title style={font=\sffamily\small},
  clip=false
]
  %% 1300 Hz sine over 3 ms; t in ms → multiply by 1e-3 for seconds
  %% 1300 * 1e-3 = 1.3 cycles per ms
  \addplot[toneBlue, thick, smooth, samples=400, domain=0:3]
      {sin(deg(2*pi*1.3*x))};
  \node[toneBlue, font=\sffamily\footnotesize, anchor=west] at (axis cs:0.1,1.1)
      {$f_{\text{target}} = 1300\,\text{Hz}$};
\end{axis}

\begin{axis}[
  %% ── layout ────────────────────────────────────────────────────────
  name=psdplot,
  at={(timeplot.below south west)}, anchor=above north west,
  yshift=-0.8cm,
  width=12cm, height=5cm,
  xmin=0, xmax=2200,
  ymin=-5, ymax=45,
  xlabel={Frequency (Hz)},
  ylabel={PSD (dB)},
  title={\textbf{BB0 — Power Spectral Density}},
  xtick={0,200,400,600,800,1000,1200,1300,1400,1600,1800,2000},
  xticklabel style={rotate=45, anchor=east, font=\sffamily\tiny},
  ytick={-5,0,10,20,30,40},
  grid=both, grid style={black!8},
  axis lines=left,
  tick label style={font=\sffamily\footnotesize},
  label style={font=\sffamily\small},
  title style={font=\sffamily\small},
  clip=false
]
  %% Flat noise floor at 0 dB
  \addplot[black!25, thin, domain=0:2200] {0};

  %% Target tone spike at 1300 Hz (drawn as a thick vertical line + arrowhead)
  \addplot[toneBlue, very thick, ->]
      coordinates {(1300, 0) (1300, 40)};
  \node[toneBlue, anchor=west, font=\sffamily\footnotesize]
      at (axis cs:1310, 38) {Target tone: $1300\,\text{Hz}$};

  %% Self-noise reference dashed line at 1200 Hz
  \addplot[selfOrange, dashed, thick, ->]
      coordinates {(1200, 0) (1200, 35)};
  \node[selfOrange, anchor=east, font=\sffamily\footnotesize]
      at (axis cs:1190, 33) {Self-noise: $1200\,\text{Hz}$};

\end{axis}
\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-05 — BB1 Wideband Cavitation Source Waveform

**Target file:** `docs/images/generation/bb1_wideband_waveform.png`
**Aspect ratio:** 16:9

```latex
\documentclass{standalone}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{amsmath}
\usepackage{tikz}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, positioning}

\definecolor{noiseBlue}{HTML}{1565c0}
\definecolor{envOrange}{HTML}{e65100}
\definecolor{finalGreen}{HTML}{2e7d32}
\definecolor{toneBlue}{HTML}{1a6eb5}

\begin{document}
\begin{tikzpicture}[>=Stealth, font=\sffamily\small]

%% ── PANEL 1: Bandpass noise (time + PSD) ────────────────────────────────
\begin{axis}[
  name=p1time,
  at={(0,0)},
  width=8cm, height=4cm,
  xmin=0, xmax=100,
  ylabel={Amplitude}, xlabel={Time (ms)},
  title={\footnotesize\textbf{Panel 1:} Bandpass noise $S_B(t)$},
  yticklabels={}, grid=both, grid style={black!8},
  axis lines=left,
  tick label style={font=\sffamily\tiny},
  title style={font=\sffamily\footnotesize}
]
  %% Pseudo-noise: sum of many random sinusoids in 100-2000 Hz band
  \addplot[noiseBlue, thin, smooth, samples=500, domain=0:100]
      { 0.6*sin(deg(2*pi*0.13*x + 0.5))
       +0.5*sin(deg(2*pi*0.24*x + 1.2))
       +0.4*sin(deg(2*pi*0.41*x + 2.1))
       +0.7*sin(deg(2*pi*0.57*x + 0.8))
       +0.3*sin(deg(2*pi*0.78*x + 1.7))
       +0.5*sin(deg(2*pi*0.95*x + 0.3))
       +0.4*sin(deg(2*pi*1.13*x + 2.5))
       +0.3*sin(deg(2*pi*1.41*x + 1.1))};
\end{axis}

\begin{axis}[
  name=p1psd,
  at={(p1time.below south west)}, anchor=above north west, yshift=-0.5cm,
  width=8cm, height=3.2cm,
  xmin=0, xmax=2200, ymin=-3, ymax=18,
  ylabel={PSD (dB)}, xlabel={Freq (Hz)},
  grid=both, grid style={black!8}, axis lines=left,
  tick label style={font=\sffamily\tiny},
  xtick={0,500,1000,1500,2000},
]
  %% Bandpass rectangle 100-2000 Hz
  \addplot[noiseBlue, thick, fill=noiseBlue!15] coordinates
      {(0,0)(100,0)(100,12)(2000,12)(2000,0)(2100,0)};
  \node[noiseBlue, font=\sffamily\tiny] at (axis cs:1050, 14)
      {100–2000 Hz};
\end{axis}

%% ── PANEL 2: AM Envelope ────────────────────────────────────────────────
\begin{axis}[
  name=p2,
  at={(p1time.right of north east)}, anchor=left of north west,
  xshift=2.2cm,
  width=8cm, height=4cm,
  xmin=0, xmax=400,
  ymin=0, ymax=2.2,
  ylabel={Envelope}, xlabel={Time (ms)},
  title={\footnotesize\textbf{Panel 2:} AM Envelope},
  grid=both, grid style={black!8}, axis lines=left,
  tick label style={font=\sffamily\tiny},
  title style={font=\sffamily\footnotesize}
]
  %% envelope = 1 + 0.5*sin(2*pi*5e-3*t) + 0.5*sin(2*pi*10e-3*t)
  %% t in ms -> 5 Hz = 0.005 cycles/ms; 10 Hz = 0.01 cycles/ms
  \addplot[envOrange, thick, smooth, samples=400, domain=0:400]
      {1 + 0.5*sin(deg(2*pi*0.005*x)) + 0.5*sin(deg(2*pi*0.01*x))};
  \draw[envOrange!50, dashed, thin] (axis cs:0,1) -- (axis cs:400,1)
      node[right, font=\sffamily\tiny, envOrange]{baseline};
  \node[envOrange, anchor=west, font=\sffamily\tiny] at (axis cs:5, 2.05)
      {$1 + 0.5\sin(2\pi\cdot5t) + 0.5\sin(2\pi\cdot10t)$};
  \node[envOrange, anchor=west, font=\sffamily\tiny] at (axis cs:5, 1.88)
      {$f_{m_1}=5\,\text{Hz}$,\; $f_{m_2}=10\,\text{Hz}$ (blade-rate)};
\end{axis}

%% ── PANEL 3: Final BB1 waveform ─────────────────────────────────────────
\begin{axis}[
  name=p3time,
  at={(p2.right of north east)}, anchor=left of north west,
  xshift=2.2cm,
  width=8cm, height=4cm,
  xmin=0, xmax=100,
  ylabel={Amplitude}, xlabel={Time (ms)},
  title={\footnotesize\textbf{Panel 3:} Final BB1 = AM-noise + tone},
  yticklabels={}, grid=both, grid style={black!8},
  axis lines=left,
  tick label style={font=\sffamily\tiny},
  title style={font=\sffamily\footnotesize}
]
  %% AM-modulated noise approximation + tone at 1.3 cycles/ms
  \addplot[finalGreen, thin, smooth, samples=500, domain=0:100]
      { (1 + 0.5*sin(deg(2*pi*0.005*x)) + 0.5*sin(deg(2*pi*0.01*x))) *
        (0.4*sin(deg(2*pi*0.13*x))+0.5*sin(deg(2*pi*0.57*x))
        +0.4*sin(deg(2*pi*0.95*x))+0.3*sin(deg(2*pi*1.41*x)))
       + 0.5*sin(deg(2*pi*1.3*x)) };
\end{axis}

\begin{axis}[
  name=p3psd,
  at={(p3time.below south west)}, anchor=above north west, yshift=-0.5cm,
  width=8cm, height=3.2cm,
  xmin=0, xmax=2200, ymin=-3, ymax=18,
  ylabel={PSD (dB)}, xlabel={Freq (Hz)},
  grid=both, grid style={black!8}, axis lines=left,
  tick label style={font=\sffamily\tiny},
  xtick={0,500,1000,1300,1500,2000},
  xticklabel style={rotate=45, anchor=east, font=\sffamily\tiny},
]
  %% Broadband plateau
  \addplot[finalGreen, thick, fill=finalGreen!12] coordinates
      {(0,0)(100,0)(100,11)(2000,11)(2000,0)(2100,0)};
  %% Tone spike at 1300 Hz
  \addplot[toneBlue, very thick, ->]
      coordinates {(1300, 0) (1300, 16)};
  \node[toneBlue, font=\sffamily\tiny, anchor=west]
      at (axis cs:1310, 15) {$1300\,\text{Hz}$ tone};
\end{axis}

%% ── Operator arrows between panels ─────────────────────────────────────
% Arrow + × symbol between Panel 1 and Panel 2
\node[font=\Large] (times12) at
    ($(p1time.east)!0.5!(p2.west)$) {$\times$};
\draw[->, thick] (p1time.east) -- (times12.west);
\draw[->, thick] (times12.east) -- (p2.west);

% Arrow + = symbol between Panel 2 and Panel 3
\node[font=\Large] (eq23) at
    ($(p2.east)!0.5!(p3time.west)$) {$\Rightarrow$};
\draw[->, thick] (p2.east) -- (eq23.west);
\draw[->, thick] (eq23.east) -- (p3time.west);

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-06 — Fractional Delay LMMSE Interpolation

**Target file:** `docs/images/generation/fractional_delay_lmmse.png`
**Aspect ratio:** 4:3

```latex
\documentclass[tikz, border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, shapes.geometric, positioning, fit,
                decorations.pathmorphing, calc, matrix}

\definecolor{sampleBlue}{HTML}{1565c0}
\definecolor{errorRed}{HTML}{c62828}
\definecolor{correctOrange}{HTML}{e65100}
\definecolor{blockGray}{HTML}{546e7a}
\definecolor{mathBg}{HTML}{f5f5f5}

\tikzset{
  fblock/.style={
    draw=blockGray, fill=blockGray!10, thick,
    rectangle, rounded corners=4pt,
    minimum width=3.2cm, minimum height=1.0cm,
    font=\sffamily\footnotesize, text=blockGray, align=center
  }
}

\begin{document}
\begin{tikzpicture}[>=Stealth, font=\sffamily\small]

%% ════════════════════════════════════════════════════════════════════
%%  ROW 1 — Problem statement
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\small\bfseries] at (6, 11.5)
    {The Sub-Sample Delay Problem};

% Sample index axis
\draw[->, thin] (-0.3, 10.0) -- (10.5, 10.0)
    node[right, font=\sffamily\footnotesize] {Sample index};

% Integer sample ticks + dots
\foreach \i in {0,1,...,10}{
    \draw[thin] (\i, 9.9) -- (\i, 10.1);
    \filldraw[sampleBlue] (\i, 10.0) circle (0.09);
    \node[below=3pt, font=\sffamily\tiny] at (\i, 9.9) {\i};
}

% Sinusoidal curve through the samples (cosmetic)
\draw[sampleBlue!40, thin, smooth, domain=0:10, samples=200]
    plot (\x, {10.0 + 0.7*sin(deg(2*pi*\x/6.5))});

% Desired fractional position τ = 5.79
\filldraw[errorRed] (5.79, 10.0) circle (0.12);
\draw[errorRed, ->, thin] (5.79, 10.5) -- (5.79, 10.12);
\node[errorRed, above, font=\sffamily\footnotesize]
    at (5.79, 10.55) {$\tau = 5.79$ samples\;(desired)};

% Integer rounded position at 6
\filldraw[correctOrange] (6.0, 10.0) circle (0.09);
\draw[correctOrange, ->, thin] (6.0, 9.4) -- (6.0, 9.88);
\node[correctOrange, below, font=\sffamily\footnotesize]
    at (6.0, 9.35) {$\lfloor\tau\rceil = 6$\;(integer rounding)};

% Error arrow
\draw[errorRed, <->, thick]
    (5.79, 9.65) -- (6.0, 9.65)
    node[midway, below=2pt, font=\sffamily\tiny, errorRed]
    {$\epsilon = 0.21$ samples\;$\Rightarrow$\;phase error};

%% ════════════════════════════════════════════════════════════════════
%%  ROW 2 — Decomposition
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\small\bfseries] at (6, 8.8)
    {Decomposition: $\tau = D_{\text{int}} + D_{\text{frac}}$};

\node[draw=sampleBlue!40, fill=sampleBlue!5, rounded corners=4pt,
      inner sep=6pt, font=\sffamily\footnotesize, align=center]
      (intbox) at (2.8, 7.8) {
    $D_{\text{int}} = \lfloor 5.79 \rfloor = 5$\\[3pt]
    Integer shift\\
    via zero-padded FIR impulse
};
\node[draw=correctOrange!60, fill=correctOrange!5, rounded corners=4pt,
      inner sep=6pt, font=\sffamily\footnotesize, align=center]
      (fracbox) at (9.2, 7.8) {
    $D_{\text{frac}} = 5.79 - 5 = 0.79$\\[3pt]
    Fractional delay\\
    via 2-tap LMMSE filter $[h_0,\,h_1]$
};

% Decomposition equation
\node[font=\sffamily\normalsize] at (6.0, 7.8)
    {$\boldsymbol{+}$};
\draw[<-, thin] (intbox.north) -- ++(0, 0.5)
    node[above, font=\sffamily\tiny] {easy};
\draw[<-, thin] (fracbox.north) -- ++(0, 0.5)
    node[above, font=\sffamily\tiny] {LMMSE};

%% ════════════════════════════════════════════════════════════════════
%%  ROW 3 — LMMSE equations
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\small\bfseries] at (6, 6.4)
    {2-tap LMMSE Gram System};

\node[draw=black!20, fill=mathBg, rounded corners=4pt,
      inner sep=10pt, align=left, font=\sffamily\footnotesize]
      (grambox) at (6.0, 5.0) {
    $\omega_c = \dfrac{\pi(f_H + f_L)}{f_s}$,\quad
    $\omega_B = \dfrac{\pi(f_H - f_L)}{f_s}$ \\[6pt]
    $\mathbf{G} =
     \begin{bmatrix} 1 & g \\ g & 1 \end{bmatrix}$,\quad
    $g = \dfrac{\cos(\omega_c)\,\sin(\omega_B)}{\omega_B}$ \\[6pt]
    $\mathbf{r} =
     \begin{bmatrix}
       \cos(\omega_c D_f)\,\operatorname{sinc}(\omega_B D_f) \\
       \cos\!\left(\omega_c(1-D_f)\right)\operatorname{sinc}\!\left(\omega_B(1-D_f)\right)
     \end{bmatrix}$ \\[6pt]
    $\begin{bmatrix}h_0\\h_1\end{bmatrix}
     = \mathbf{G}^{-1}\mathbf{r}$
};

% Parameter values annotation
\node[font=\sffamily\tiny, text=blockGray, anchor=west] at (0.3, 3.6)
    {$f_L = 100\,\text{Hz}$,\;
     $f_H = 2000\,\text{Hz}$,\;
     $f_s = 4096\,\text{Hz}$,\;
     $D_f = D_{\text{frac}} = 0.79$};

%% ════════════════════════════════════════════════════════════════════
%%  ROW 4 — Filter block diagram
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\small\bfseries] at (6, 3.0)
    {Composite FIR Implementation};

\node[fblock] (input) at (0.5, 2.0) {Input\\$s(t)$};

\node[fblock, draw=sampleBlue, fill=sampleBlue!8, text=sampleBlue]
     (intfir) at (4.2, 2.0)
     {Integer delay\\$D_{\text{int}}$ samples\\(zero-padded FIR)};

\node[fblock, draw=correctOrange, fill=correctOrange!8, text=correctOrange]
     (lmmse) at (8.3, 2.0)
     {2-tap LMMSE\\filter $[h_0,\,h_1]$};

\node[fblock] (output) at (11.8, 2.0) {Output\\$s(t-\tau)$};

\draw[->, thick] (input)  -- (intfir);
\draw[->, thick] (intfir) -- (lmmse);
\draw[->, thick] (lmmse)  -- (output);

% Code snippet below
\node[draw=black!15, fill=black!3, rounded corners=3pt,
      inner sep=6pt, font=\ttfamily\tiny, align=left] at (6.0, 0.6) {
    impulse = np.zeros(D\_int + 2)\\
    impulse[D\_int : D\_int + 2] = [h0, h1]\\
    output  = lfilter(impulse, 1.0, signal)
};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-07 — End-to-End Data Generation Pipeline

**Target file:** `docs/images/generation/pipeline_high_level.png`
**Aspect ratio:** 21:9

```latex
\documentclass[tikz, border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, shapes.geometric, positioning, fit,
                backgrounds, calc, decorations.pathreplacing}

\definecolor{navybg}{HTML}{0d1b2a}
\definecolor{stageA}{HTML}{00bcd4}   % Source Synthesis
\definecolor{stageB}{HTML}{26a69a}   % Spatialization
\definecolor{stageC}{HTML}{66bb6a}   % Fractional Delay
\definecolor{stageD}{HTML}{ffa726}   % Noise Mixing
\definecolor{stageE}{HTML}{ef5350}   % Dataset Assembly
\definecolor{outputCol}{HTML}{b0bec5}

\tikzset{
  stagenode/.style 2 args={
    draw=#1, fill=#1!18, very thick,
    rectangle, rounded corners=6pt,
    minimum width=3.6cm, minimum height=2.8cm,
    text=#1, font=\sffamily\footnotesize, align=center
  },
  shapearrow/.style={->, very thick, #1}
}

\begin{document}
\begin{tikzpicture}[
    font=\sffamily\small,
    background rectangle/.style={fill=navybg},
    show background rectangle,
    every node/.style={text=white}
]

%% ── Stage boxes ──────────────────────────────────────────────────────────
\node[stagenode={stageA}{}, text=stageA] (st1) at (0, 0) {
    \textbf{① Source}\\
    \textbf{Synthesis}\\[4pt]
    BB0: tone $f_1$\\
    BB1: AM-cavity\\
    $+$ tone\\[4pt]
    \texttt{\scriptsize sources.py}\\
    \texttt{\scriptsize source\_waveform()}
};

\node[stagenode={stageB}{}, text=stageB, right=1.2cm of st1] (st2) {
    \textbf{② Wave}\\
    \textbf{Propagation}\\[4pt]
    $\tau_m = \dfrac{m \cdot d\cos\theta}{c}$\\[4pt]
    per sensor\\[4pt]
    \texttt{\scriptsize array.py}\\
    \texttt{\scriptsize simulate\_ula()}
};

\node[stagenode={stageC}{}, text=stageC, right=1.2cm of st2] (st3) {
    \textbf{③ Fractional}\\
    \textbf{Delay}\\[4pt]
    $\tau = D_{\text{int}} + D_{\text{frac}}$\\
    2-tap LMMSE\\[4pt]
    \texttt{\scriptsize fractional\_delay.py}\\
    \texttt{\scriptsize delay\_signal()}
};

\node[stagenode={stageD}{}, text=stageD, right=1.2cm of st3] (st4) {
    \textbf{④ Noise}\\
    \textbf{Mixing}\\[4pt]
    $\mathbf{Y} = \mathbf{S}(\theta) + \mathbf{Z}$\\
    SINR control\\[4pt]
    \texttt{\scriptsize scenario.py}\\
    \texttt{\scriptsize generate\_snapshot()}
};

\node[stagenode={stageE}{}, text=stageE, right=1.2cm of st4] (st5) {
    \textbf{⑤ Dataset}\\
    \textbf{Assembly}\\[4pt]
    Sweep $\theta\!\in\![0°,180°]$\\
    Stack $(N,4096,32)$\\[4pt]
    \texttt{\scriptsize dataset.py}\\
    \texttt{\scriptsize generate\_dataset()}
};

%% ── Connecting arrows ────────────────────────────────────────────────────
\foreach \from/\to in {st1/st2, st2/st3, st3/st4, st4/st5}{
    \draw[shapearrow={white}, line width=1.5pt]
        (\from.east) -- (\to.west);
}

%% ── Data shape transformation row (below stages) ─────────────────────────
\node[white!70, font=\sffamily\footnotesize, below=1.0cm of st1]
    (sh1) {scalar\\$[T]$};
\node[white!70, font=\sffamily\footnotesize, below=1.0cm of st3]
    (sh2) {per-sensor matrix\\$[T \times M]$};
\node[white!70, font=\sffamily\footnotesize, below=1.0cm of st5]
    (sh3) {labelled dataset\\$[N \times T \times M]$};

\draw[->, white!50, thin] (sh1.east) -- (sh2.west);
\draw[->, white!50, thin] (sh2.east) -- (sh3.west);

\node[white!40, font=\sffamily\tiny, below=0.3cm of sh1]
    {$T = 4096$\;\;$M = 32$};
\node[white!40, font=\sffamily\tiny, below=0.3cm of sh3]
    {$N = $ bearings $\times$ repeats};

%% ── Output files (right of stage 5) ─────────────────────────────────────
\node[draw=outputCol!60, fill=outputCol!10, rounded corners=4pt,
      text=outputCol, font=\sffamily\footnotesize, align=left,
      inner sep=8pt, right=1.4cm of st5] (outbox) {
    \textbf{Output files}\\[4pt]
    \texttt{noisy.npy}\\
    \quad$(N, 4096, 32)$ float32\\[3pt]
    \texttt{labels.npy}\\
    \quad$(N,)$ int16\\[3pt]
    \texttt{generation\_metadata.json}\\
    \quad full provenance record
};
\draw[->, white!70, thick] (st5.east) -- (outbox.west);

%% ── Top label ────────────────────────────────────────────────────────────
\node[white, font=\sffamily\large\bfseries]
    at ($(st1.north)!0.5!(st5.north) + (0, 1.0)$)
    {Passive SONAR Data Generation Pipeline};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-08 — BB0 vs BB1 Spectral Comparison

**Target file:** `docs/images/generation/bb0_vs_bb1_comparison.png`
**Aspect ratio:** 16:9

```latex
\documentclass{standalone}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{positioning, calc}

\definecolor{bb0Blue}{HTML}{1565c0}
\definecolor{bb1Green}{HTML}{2e7d32}
\definecolor{selfOrange}{HTML}{e65100}

\begin{document}
\begin{tikzpicture}[font=\sffamily\small]

%% ── BB0 Time domain ──────────────────────────────────────────────────────
\begin{axis}[
  name=bb0time,
  width=8cm, height=4.5cm,
  xmin=0, xmax=3, ymin=-1.3, ymax=1.3,
  title={\textbf{BB0 — Narrowband (Time)}},
  xlabel={Time (ms)}, ylabel={Amplitude},
  grid=both, grid style={black!8}, axis lines=left,
  title style={font=\sffamily\small, color=bb0Blue},
  tick label style={font=\sffamily\tiny}
]
  \addplot[bb0Blue, thick, smooth, samples=300, domain=0:3]
      {sin(deg(2*pi*1.3*x))};
  \node[bb0Blue, font=\sffamily\tiny, anchor=west] at (axis cs:0.1,1.1)
      {$s(t) = A\sin(2\pi\cdot1300\cdot t)$};
\end{axis}

%% ── BB0 PSD ──────────────────────────────────────────────────────────────
\begin{axis}[
  name=bb0psd,
  at={(bb0time.below south west)}, anchor=above north west, yshift=-0.6cm,
  width=8cm, height=4.5cm,
  xmin=0, xmax=2200, ymin=-5, ymax=48,
  title={\textbf{BB0 — PSD}},
  xlabel={Frequency (Hz)}, ylabel={PSD (dB)},
  grid=both, grid style={black!8}, axis lines=left,
  title style={font=\sffamily\small, color=bb0Blue},
  xtick={0,500,1000,1200,1300,1500,2000},
  xticklabel style={rotate=45, anchor=east, font=\sffamily\tiny},
  tick label style={font=\sffamily\tiny}
]
  \addplot[black!20, thin, domain=0:2200] {0};
  \addplot[bb0Blue, very thick, ->] coordinates {(1300,0)(1300,42)};
  \node[bb0Blue, anchor=west, font=\sffamily\tiny]
      at (axis cs:1315,40) {Target $1300\,\text{Hz}$};
  \addplot[selfOrange, dashed, thick, ->] coordinates {(1200,0)(1200,36)};
  \node[selfOrange, anchor=east, font=\sffamily\tiny]
      at (axis cs:1185,34) {Self-noise $1200\,\text{Hz}$};
\end{axis}

%% ── BB0 physics label ────────────────────────────────────────────────────
\node[bb0Blue, font=\sffamily\footnotesize\itshape,
      below=0.4cm of bb0psd.south, text width=7cm, align=center]
    {Rotating machinery\\propeller shaft, turbine harmonics};

%% ── BB1 Time domain ──────────────────────────────────────────────────────
\begin{axis}[
  name=bb1time,
  at={(bb0time.right of north east)}, anchor=left of north west, xshift=3.0cm,
  width=8cm, height=4.5cm,
  xmin=0, xmax=100, ymin=-3, ymax=3,
  title={\textbf{BB1 — Wideband (Time)}},
  xlabel={Time (ms)}, ylabel={Amplitude},
  grid=both, grid style={black!8}, axis lines=left,
  title style={font=\sffamily\small, color=bb1Green},
  tick label style={font=\sffamily\tiny}
]
  %% AM-modulated noise approximation
  \addplot[bb1Green, thin, smooth, samples=500, domain=0:100]
      {(1+0.5*sin(deg(2*pi*0.005*x))+0.5*sin(deg(2*pi*0.01*x)))*
       (0.9*sin(deg(2*pi*0.13*x))+0.7*sin(deg(2*pi*0.41*x))
       +0.8*sin(deg(2*pi*0.78*x))+0.6*sin(deg(2*pi*1.41*x)))
       +0.5*sin(deg(2*pi*1.3*x))};
  \node[bb1Green, font=\sffamily\tiny, anchor=west] at (axis cs:2,2.7)
      {AM-cavitation + tone};
\end{axis}

%% ── BB1 PSD ──────────────────────────────────────────────────────────────
\begin{axis}[
  name=bb1psd,
  at={(bb1time.below south west)}, anchor=above north west, yshift=-0.6cm,
  width=8cm, height=4.5cm,
  xmin=0, xmax=2200, ymin=-3, ymax=20,
  title={\textbf{BB1 — PSD}},
  xlabel={Frequency (Hz)}, ylabel={PSD (dB)},
  grid=both, grid style={black!8}, axis lines=left,
  title style={font=\sffamily\small, color=bb1Green},
  xtick={0,500,1000,1300,1500,2000},
  xticklabel style={rotate=45, anchor=east, font=\sffamily\tiny},
  tick label style={font=\sffamily\tiny}
]
  %% Broadband plateau 100-2000 Hz
  \addplot[bb1Green, thick, fill=bb1Green!15] coordinates
      {(0,0)(100,0)(100,12)(2000,12)(2000,0)(2100,0)};
  %% Tone spike
  \addplot[bb0Blue, very thick, ->] coordinates {(1300,0)(1300,18)};
  \node[bb0Blue, anchor=west, font=\sffamily\tiny]
      at (axis cs:1315,17) {$1300\,\text{Hz}$ tone};
  \node[bb1Green, font=\sffamily\tiny] at (axis cs:1050,13.5)
      {100–2000 Hz broadband};
\end{axis}

%% ── BB1 physics label ────────────────────────────────────────────────────
\node[bb1Green, font=\sffamily\footnotesize\itshape,
      below=0.4cm of bb1psd.south, text width=7cm, align=center]
    {Propeller cavitation\\vapour bubble implosion, AM at 5 \& 10 Hz};

%% ── Centre comparison table ─────────────────────────────────────────────
\node[draw=black!30, fill=black!4, rounded corners=4pt,
      font=\sffamily\tiny, inner sep=7pt, align=left]
      (tbl) at ($(bb0time.east)!0.5!(bb1time.west) + (0,-2.0)$) {
  \begin{tabular}{l c c}
    \hline
    \textbf{Property} & \textbf{BB0} & \textbf{BB1} \\\hline
    Spectral shape  & Tonal        & Broadband \\
    Modulation      & None         & AM 5\,\&\,10\,Hz \\
    Physics         & Machinery    & Cavitation \\
    Self-noise freq & 1200\,Hz     & 1200\,Hz + BB \\
    CLI flag        & \texttt{-{}-bb 0} & \texttt{-{}-bb 1} \\
    Difficulty      & Moderate     & Higher \\\hline
  \end{tabular}
};

\end{tikzpicture}
\end{document}
```

---

## IMG-GEN-09 — Endfire vs Broadside Geometry

**Target file:** `docs/images/generation/endfire_vs_broadside.png`
**Aspect ratio:** 3:2

```latex
\documentclass[tikz, border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, positioning, calc, decorations.markings}

\definecolor{sensorBlue}{HTML}{1565c0}
\definecolor{waveOrange}{HTML}{e65100}
\definecolor{dotRed}{HTML}{c62828}
\definecolor{panelBg}{HTML}{fafafa}

\begin{document}
\begin{tikzpicture}[>=Stealth, font=\sffamily\small]

%% ── DIVIDER ──────────────────────────────────────────────────────────────
\draw[black!20, dashed, thick] (8.0, -5.0) -- (8.0, 6.5);

%% ════════════════════════════════════════════════════════════════════
%%  LEFT PANEL — BROADSIDE (θ = 90°)
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\normalsize\bfseries, sensorBlue] at (3.5, 6.0)
    {Broadside — $\theta = 90°$};

% ULA
\draw[black!30] (-0.5, 3.0) -- (7.5, 3.0);
\foreach \i in {0,...,7}{
    \draw[sensorBlue, fill=sensorBlue!20, thick]
        ({0.9*\i}, 3.0) circle (0.20);
    \node[below=4pt, font=\sffamily\tiny] at ({0.9*\i}, 3.0)
        {\i};
}

% Wavefront arrives from directly above (perpendicular to array)
% → horizontal line above the array
\draw[waveOrange, very thick, ->]
    (3.5, 5.5) -- (3.5, 4.3)
    node[midway, right=4pt, waveOrange, font=\sffamily\footnotesize]
    {Propagation};
\draw[waveOrange, very thick]
    (-0.5, 4.5) -- (7.5, 4.5);
\node[waveOrange, right, font=\sffamily\footnotesize] at (7.6, 4.5)
    {Wavefront};

% All arrivals simultaneous — timeline with all dots at same position
\node[font=\sffamily\footnotesize, black!60] at (3.5, 1.8)
    {Arrival timeline:};
\draw[->, thin, black!40] (-0.3, 1.3) -- (7.3, 1.3)
    node[right, font=\sffamily\tiny]{$t$};
\foreach \i in {0,...,7}{
    % All dots at the same x position → simultaneous arrival
    \filldraw[dotRed] (3.5, 1.3) circle (0.09);
    \draw[black!20, dashed, thin]
        ({0.9*\i}, 2.7) -- ({0.9*\i}, 1.4);
}
\node[font=\sffamily\tiny, dotRed] at (3.5, 0.9)
    {All sensors: same $\tau$ (simultaneous)};

% Annotation box
\node[draw=black!20, fill=panelBg, rounded corners=3pt,
      inner sep=6pt, font=\sffamily\footnotesize, align=center]
      at (3.5, -0.3) {
    $\tau_n = n\cdot\dfrac{d\cos(90°)}{c} = 0$\\[4pt]
    $\cos(90°) = 0$\\
    \textbf{Zero delay — no spatial information}
};

%% ════════════════════════════════════════════════════════════════════
%%  RIGHT PANEL — ENDFIRE (θ = 0°)
%% ════════════════════════════════════════════════════════════════════
\node[font=\sffamily\normalsize\bfseries, waveOrange] at (12.5, 6.0)
    {Endfire — $\theta = 0°$};

% ULA
\draw[black!30] (8.5, 3.0) -- (16.5, 3.0);
\foreach \i in {0,...,7}{
    \draw[sensorBlue, fill=sensorBlue!20, thick]
        ({9.0 + 0.9*\i}, 3.0) circle (0.20);
    \node[below=4pt, font=\sffamily\tiny] at ({9.0 + 0.9*\i}, 3.0)
        {\i};
}

% Wavefront arrives from the left (parallel to array axis)
% → vertical line to the left of element 0
\draw[waveOrange, very thick, ->]
    (7.5, 3.0) -- (8.7, 3.0)
    node[midway, above=4pt, waveOrange, font=\sffamily\footnotesize]
    {Propagation};
\draw[waveOrange, very thick]
    (8.0, 2.2) -- (8.0, 3.8);
\node[waveOrange, left, font=\sffamily\footnotesize] at (7.9, 3.8)
    {Wavefront};

% Progressive arrivals — dots shift to the right
\node[font=\sffamily\footnotesize, black!60] at (12.5, 1.8)
    {Arrival timeline:};
\draw[->, thin, black!40] (8.7, 1.3) -- (16.5, 1.3)
    node[right, font=\sffamily\tiny]{$t$};
\pgfmathsetmacro{\tscale}{0.82}
\foreach \i in {0,...,7}{
    \pgfmathsetmacro{\arrx}{9.0 + \i*\tscale}
    \filldraw[dotRed] (\arrx, 1.3) circle (0.09);
    \draw[black!20, dashed, thin]
        ({9.0 + 0.9*\i}, 2.7) -- (\arrx, 1.4);
}
\node[font=\sffamily\tiny, dotRed] at (12.5, 0.9)
    {Progressive: $\tau_n = n\cdot d/c = n \times 0.125\,\text{ms}$};

% Annotation box
\node[draw=black!20, fill=panelBg, rounded corners=3pt,
      inner sep=6pt, font=\sffamily\footnotesize, align=center]
      at (12.5, -0.3) {
    $\tau_n = n\cdot\dfrac{d\cos(0°)}{c}
             = n\cdot\dfrac{0.1875}{1500}$\\[4pt]
    $\tau_{\max} = 7\cdot0.125\,\text{ms} = 0.875\,\text{ms}$\;(8 elem)\\
    Full 32-element: $\Delta\tau_{\max} = 4\,\text{ms}$\\[4pt]
    \textbf{Max delay — but cosine gradient}\\
    \textbf{is flat near 0° → ambiguity zone}
};

%% ── Cosine function sketch (bottom, full width) ──────────────────────────
\begin{scope}[yshift=-7.2cm]
\draw[->, thin, black!50] (-0.3, 0) -- (16.5, 0)
    node[right, font=\sffamily\tiny]{$\theta$ (degrees)};
\draw[->, thin, black!50] (0.0, -0.3) -- (0.0, 1.4)
    node[above, font=\sffamily\tiny]{$\cos\theta$};
\draw[sensorBlue, thick, smooth, domain=0:180, samples=200]
    plot ({0.088*\x}, {cos(deg(\x*1))});   % 0.088 maps 180deg to 15.8 units
\draw[black!20, dashed] (0, 1.0) -- (16.5, 1.0);
\node[right, font=\sffamily\tiny, black!50] at (16.5, 1.0) {$1$};
\draw[black!20, dashed] (0, 0.0) -- (16.5, 0.0);
% Endfire zones highlighted
\fill[waveOrange!15]
    (0, -0.15) rectangle ({0.088*30}, 1.3);
\fill[waveOrange!15]
    ({0.088*150}, -0.15) rectangle ({0.088*180}, 1.3);
\node[waveOrange, font=\sffamily\tiny, rotate=90]
    at ({0.088*15}, 0.65) {endfire zone};
\node[waveOrange, font=\sffamily\tiny, rotate=90]
    at ({0.088*165}, 0.65) {endfire zone};
% x-axis ticks
\foreach \deg/\lbl in {0/$0°$, 30/$30°$, 90/$90°$, 150/$150°$, 180/$180°$}{
    \draw[thin, black!40] ({0.088*\deg}, -0.07) -- ({0.088*\deg}, 0.07);
    \node[below, font=\sffamily\tiny] at ({0.088*\deg}, -0.07) {\lbl};
}
\node[font=\sffamily\footnotesize, black!70]
    at (8.0, -0.7)
    {$\Delta\tau_{\text{step}} = \tfrac{d}{c}\cos\theta \cdot f_s$
     \;—\;flat near endfire $\Rightarrow$ 4× oversampling in training};
\end{scope}

\end{tikzpicture}
\end{document}
```

---

## Compilation Notes

| Diagram | Required TikZ libraries |
|---|---|
| IMG-GEN-01 | `arrows.meta`, `shapes.geometric`, `positioning`, `backgrounds`, `fit`, `decorations.pathmorphing`, `decorations.markings` |
| IMG-GEN-02 | `arrows.meta`, `decorations.markings`, `angles`, `quotes`, `calc` |
| IMG-GEN-03 | `arrows.meta`, `shapes.geometric`, `positioning`, `fit`, `backgrounds`, `calc` |
| IMG-GEN-04 | `pgfplots` |
| IMG-GEN-05 | `pgfplots`, `arrows.meta`, `positioning` |
| IMG-GEN-06 | `arrows.meta`, `shapes.geometric`, `positioning`, `fit`, `calc`, `matrix` |
| IMG-GEN-07 | `arrows.meta`, `shapes.geometric`, `positioning`, `fit`, `backgrounds`, `calc`, `decorations.pathreplacing` |
| IMG-GEN-08 | `pgfplots`, `positioning`, `calc` |
| IMG-GEN-09 | `arrows.meta`, `positioning`, `calc`, `decorations.markings` |

All compile with `pdflatex`. For best results use **TeX Live 2022+** or **MiKTeX 22+**.
If a package is missing, install via `tlmgr install <package>`.
