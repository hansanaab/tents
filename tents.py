#!/usr/bin/env python3
"""Tents — a tiny always-on-top puzzle window.

Left click:  empty -> tent -> grass -> empty
Right click: toggle grass (drag to paint grass)
N = new game, R = reset, 1/2/3 = easy/medium/hard, T = toggle always-on-top
"""
import random
import time
import tkinter as tk

CELL = 34
CLUE = 22
PAD = 2

COLORS = {
    "bg": "#f4efe1",
    "grid": "#c9bfa5",
    "grass": "#b9dd9a",
    "grass_dot": "#7fb25a",
    "tree": "#2f7d32",
    "trunk": "#7a4a22",
    "tent": "#e07b2a",
    "tent_err": "#d62828",
    "clue": "#333333",
    "clue_ok": "#9a9a9a",
    "clue_bad": "#d62828",
    "win": "#2f7d32",
}

DIFFICULTIES = ("Easy", "Medium", "Hard")
SIZES = (5, 6, 7, 8)


def orth(r, c, n):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < n:
            yield rr, cc


def touching(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1


def has_matching(tents, trees, n):
    """Can every tent be paired with its own orthogonally adjacent tree?"""
    if len(tents) != len(trees):
        return False
    match = {}

    def try_assign(t, seen):
        for tr in orth(*t, n):
            if tr in trees and tr not in seen:
                seen.add(tr)
                if tr not in match or try_assign(match[tr], seen):
                    match[tr] = t
                    return True
        return False

    return all(try_assign(t, set()) for t in tents)


def count_solutions(n, trees, rows, cols, limit=2):
    cands = sorted({p for t in trees for p in orth(*t, n) if p not in trees})
    # remaining candidates per column/row from index i onward
    col_left = [[0] * n for _ in range(len(cands) + 1)]
    row_left = [[0] * n for _ in range(len(cands) + 1)]
    for i in range(len(cands) - 1, -1, -1):
        col_left[i] = col_left[i + 1][:]
        row_left[i] = row_left[i + 1][:]
        col_left[i][cands[i][1]] += 1
        row_left[i][cands[i][0]] += 1
    for r in range(n):
        if row_left[0][r] < rows[r]:
            return 0
    for c in range(n):
        if col_left[0][c] < cols[c]:
            return 0

    rc, cc = [0] * n, [0] * n
    placed = []
    found = 0

    def rec(i):
        nonlocal found
        if found >= limit:
            return
        if i == len(cands):
            if rc == list(rows) and cc == list(cols) and has_matching(placed, trees, n):
                found += 1
            return
        r, c = cands[i]
        # option: place tent
        if rc[r] < rows[r] and cc[c] < cols[c] and not any(touching((r, c), p) for p in placed[-2 * n:]):
            rc[r] += 1
            cc[c] += 1
            placed.append((r, c))
            if feasible(i + 1):
                rec(i + 1)
            placed.pop()
            rc[r] -= 1
            cc[c] -= 1
        # option: leave empty
        if feasible(i + 1):
            rec(i + 1)

    def feasible(j):
        for k in range(n):
            if cc[k] + col_left[j][k] < cols[k]:
                return False
            if rc[k] + row_left[j][k] < rows[k]:
                return False
        return True

    rec(0)
    return found


def generate(n, difficulty):
    density = {"Easy": 0.17, "Medium": 0.19, "Hard": 0.22}[difficulty]
    target = max(3, round(n * n * density))
    for _ in range(2000):
        cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(cells)
        tents, trees = [], set()
        for p in cells:
            if len(tents) >= target:
                break
            if p in trees or any(touching(p, t) for t in tents):
                continue
            spots = [q for q in orth(*p, n) if q not in trees and q not in tents]
            if not spots:
                continue
            tents.append(p)
            trees.add(random.choice(spots))
        if len(tents) < target:
            continue
        rows = [sum(1 for t in tents if t[0] == r) for r in range(n)]
        cols = [sum(1 for t in tents if t[1] == c) for c in range(n)]
        if count_solutions(n, trees, rows, cols) == 1:
            return trees, set(tents), rows, cols
    raise RuntimeError("could not generate puzzle")


class Tents:
    def __init__(self, root):
        self.root = root
        self.n = 6
        self.difficulty = tk.StringVar(value="Medium")
        self.size_var = tk.IntVar(value=6)
        self.topmost = tk.BooleanVar(value=True)
        root.title("Tents")
        root.resizable(False, False)
        root.configure(bg=COLORS["bg"])
        root.attributes("-topmost", True)

        self.canvas = tk.Canvas(root, highlightthickness=0, bg=COLORS["bg"])
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_left)
        for ev in ("<Button-2>", "<Button-3>", "<Control-Button-1>"):
            self.canvas.bind(ev, self.on_right)
        for ev in ("<B2-Motion>", "<B3-Motion>", "<Control-B1-Motion>"):
            self.canvas.bind(ev, self.on_drag)

        self.build_menu()
        root.bind("n", lambda e: self.new_game())
        root.bind("r", lambda e: self.reset())
        root.bind("t", lambda e: self.topmost.set(not self.topmost.get()) or self.apply_topmost())
        for i, d in enumerate(DIFFICULTIES, 1):
            root.bind(str(i), lambda e, d=d: (self.difficulty.set(d), self.new_game()))

        self.new_game(first=True)
        self.tick()

    def build_menu(self):
        m = tk.Menu(self.root)
        game = tk.Menu(m, tearoff=0)
        game.add_command(label="New Game", accelerator="N", command=self.new_game)
        game.add_command(label="Reset", accelerator="R", command=self.reset)
        game.add_separator()
        game.add_checkbutton(label="Always on Top", accelerator="T",
                             variable=self.topmost, command=self.apply_topmost)
        m.add_cascade(label="Game", menu=game)
        diff = tk.Menu(m, tearoff=0)
        for i, d in enumerate(DIFFICULTIES, 1):
            diff.add_radiobutton(label=d, accelerator=str(i), variable=self.difficulty,
                                 value=d, command=self.new_game)
        m.add_cascade(label="Difficulty", menu=diff)
        size = tk.Menu(m, tearoff=0)
        for s in SIZES:
            size.add_radiobutton(label=f"{s}×{s}", variable=self.size_var, value=s,
                                 command=self.new_game)
        m.add_cascade(label="Size", menu=size)
        self.root.config(menu=m)

    def apply_topmost(self):
        self.root.attributes("-topmost", self.topmost.get())

    # ---------- game state ----------
    def new_game(self, first=False):
        self.n = self.size_var.get()
        d = self.difficulty.get()
        self.trees, self.solution, self.rows, self.cols = generate(self.n, d)
        self.state = {}      # (r,c) -> "tent" | "grass"
        self.locked = set()
        n = self.n
        if d in ("Easy", "Medium"):
            near = {p for t in self.trees for p in orth(*t, n)}
            for r in range(n):
                for c in range(n):
                    p = (r, c)
                    if p not in self.trees and p not in near:
                        self.state[p] = "grass"
                        self.locked.add(p)
        if d == "Easy":
            for p in random.sample(sorted(self.solution), max(1, len(self.solution) // 3)):
                self.state[p] = "tent"
                self.locked.add(p)
        self.initial = dict(self.state)
        self.start = time.time()
        self.won = False
        w = n * CELL + CLUE + PAD * 2
        self.canvas.config(width=w, height=w)
        self.root.update_idletasks()
        if first:
            x = self.root.winfo_screenwidth() - w - 20
            self.root.geometry(f"+{x}+40")
        self.draw()

    def reset(self):
        self.state = dict(self.initial)
        self.won = False
        self.start = time.time()
        self.draw()

    def cell_at(self, e):
        c = (e.x - PAD) // CELL
        r = (e.y - PAD) // CELL
        if 0 <= r < self.n and 0 <= c < self.n:
            return r, c
        return None

    def editable(self, p):
        return p and not self.won and p not in self.trees and p not in self.locked

    def on_left(self, e):
        if self.won:
            for (x0, y0, x1, y1), d in self.buttons:
                if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                    self.difficulty.set(d)
                    self.new_game()
            return
        p = self.cell_at(e)
        if not self.editable(p):
            return
        nxt = {None: "tent", "tent": "grass", "grass": None}[self.state.get(p)]
        self.set(p, nxt)

    def on_right(self, e):
        p = self.cell_at(e)
        if not self.editable(p):
            self.paint = None
            return
        self.paint = None if self.state.get(p) == "grass" else "grass"
        self.set(p, self.paint)

    def on_drag(self, e):
        p = self.cell_at(e)
        if not self.editable(p) or not hasattr(self, "paint"):
            return
        cur = self.state.get(p)
        if self.paint == "grass" and cur is None or self.paint is None and cur == "grass":
            self.set(p, self.paint)

    def set(self, p, val):
        if val is None:
            self.state.pop(p, None)
        else:
            self.state[p] = val
        self.check_win()
        self.draw()

    def tents(self):
        return [p for p, v in self.state.items() if v == "tent"]

    def check_win(self):
        t = self.tents()
        n = self.n
        ok = (all(sum(1 for p in t if p[0] == r) == self.rows[r] for r in range(n))
              and all(sum(1 for p in t if p[1] == c) == self.cols[c] for c in range(n))
              and not any(touching(a, b) for i, a in enumerate(t) for b in t[i + 1:])
              and has_matching(t, self.trees, n))
        if ok:
            self.won = True
            self.elapsed = int(time.time() - self.start)
            for r in range(n):
                for c in range(n):
                    if (r, c) not in self.trees and (r, c) not in self.state:
                        self.state[(r, c)] = "grass"

    def tick(self):
        secs = self.elapsed if self.won else int(time.time() - self.start)
        label = "Solved! " if self.won else ""
        self.root.title(f"Tents {label}{secs // 60}:{secs % 60:02d}")
        self.root.after(500, self.tick)

    # ---------- drawing ----------
    def draw(self):
        cv, n = self.canvas, self.n
        cv.delete("all")
        tents = self.tents()
        bad = {a for a in tents for b in tents if a != b and touching(a, b)}
        for r in range(n):
            for c in range(n):
                x0, y0 = PAD + c * CELL, PAD + r * CELL
                x1, y1 = x0 + CELL, y0 + CELL
                p = (r, c)
                v = self.state.get(p)
                fill = COLORS["grass"] if v == "grass" else COLORS["bg"]
                cv.create_rectangle(x0, y0, x1, y1, fill=fill, outline=COLORS["grid"])
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if p in self.trees:
                    cv.create_rectangle(cx - 2, cy + 4, cx + 2, cy + 12, fill=COLORS["trunk"], width=0)
                    cv.create_oval(cx - 10, cy - 12, cx + 10, cy + 7, fill=COLORS["tree"], width=0)
                elif v == "tent":
                    col = COLORS["tent_err"] if p in bad else COLORS["tent"]
                    cv.create_polygon(cx, cy - 11, cx - 12, cy + 10, cx + 12, cy + 10,
                                      fill=col, outline="")
                    cv.create_polygon(cx, cy - 1, cx - 4, cy + 10, cx + 4, cy + 10,
                                      fill="#5a3412", outline="")
                elif v == "grass" and not self.won:
                    cv.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=COLORS["grass_dot"], width=0)
        font = ("Helvetica", 13, "bold")
        for r in range(n):
            have = sum(1 for p in tents if p[0] == r)
            cv.create_text(PAD + n * CELL + CLUE / 2, PAD + r * CELL + CELL / 2,
                           text=str(self.rows[r]), font=font, fill=self.clue_color(have, self.rows[r]))
        for c in range(n):
            have = sum(1 for p in tents if p[1] == c)
            cv.create_text(PAD + c * CELL + CELL / 2, PAD + n * CELL + CLUE / 2,
                           text=str(self.cols[c]), font=font, fill=self.clue_color(have, self.cols[c]))
        if self.won:
            cv.create_text(PAD + n * CELL + CLUE / 2, PAD + n * CELL + CLUE / 2,
                           text="✓", font=font, fill=COLORS["win"])
            self.draw_win_panel()

    def draw_win_panel(self):
        """Overlay with 'Solved' and one New Game button per difficulty."""
        cv = self.canvas
        size = self.n * CELL
        mid = PAD + size / 2
        gap, bh = 5, 26
        bw = min(54, (size - 28 - 2 * gap) / 3)
        bfont = ("Helvetica", 11 if bw >= 54 else 10, "bold")
        top = mid - 44
        cv.create_rectangle(PAD + 8, top, PAD + size - 8, mid + 50,
                            fill="white", outline=COLORS["win"], width=2)
        secs = self.elapsed
        cv.create_text(mid, top + 16, text=f"Solved in {secs // 60}:{secs % 60:02d}",
                       font=("Helvetica", 13, "bold"), fill=COLORS["win"])
        cv.create_text(mid, top + 38, text="New game:", font=("Helvetica", 11),
                       fill=COLORS["clue"])
        self.buttons = []
        x = mid - (3 * bw + 2 * gap) / 2
        y = top + 54
        for d in DIFFICULTIES:
            box = (x, y, x + bw, y + bh)
            current = d == self.difficulty.get()
            cv.create_rectangle(*box, fill=COLORS["win"] if current else COLORS["grass"],
                                outline=COLORS["win"])
            cv.create_text(x + bw / 2, y + bh / 2, text=d, font=bfont,
                           fill="white" if current else COLORS["clue"])
            self.buttons.append((box, d))
            x += bw + gap

    def clue_color(self, have, want):
        if self.won:
            return COLORS["win"]
        if have > want:
            return COLORS["clue_bad"]
        return COLORS["clue_ok"] if have == want else COLORS["clue"]


if __name__ == "__main__":
    root = tk.Tk()
    Tents(root)
    root.mainloop()
