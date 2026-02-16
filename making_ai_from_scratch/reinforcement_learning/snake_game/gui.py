from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
import tkinter as tk
from tkinter import messagebox


# Boundaries for user-adjustable settings
MIN_GRID_SIZE = 8
MAX_GRID_SIZE = 60
MIN_CELL_SIZE = 12
MAX_CELL_SIZE = 48
MIN_SPEED_MS = 40
MAX_SPEED_MS = 500
MIN_APPLES = 1
MAX_APPLES = 100
MIN_INITIAL_LENGTH = 2


@dataclass
class SnakeConfig:
    grid_size: int = 20
    cell_size: int = 28
    speed_ms: int = 100
    apples: int = 3
    initial_length: int = 3
    wrap_walls: bool = False
    show_grid: bool = True


class SnakeGame:
    def __init__(self, config: SnakeConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        size = self.config.grid_size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
        self.snake: deque[tuple[int, int]] = deque()
        self.snake_set: set[tuple[int, int]] = set()
        self.apples: set[tuple[int, int]] = set()
        self.free_tiles = {(x, y) for x in range(size) for y in range(size)}
        self.direction = "right"
        self.pending_direction = "right"
        self.running = False
        self.alive = True
        self.score = 0

        self.spawn_snake(self.config.initial_length)
        self.replenish_apples()

    def spawn_snake(self, length: int) -> None:
        size = self.config.grid_size
        center_y = size // 2
        center_x = size // 2

        positions = [(center_x - i, center_y) for i in range(length)]
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)

        if min_x < 0 or max_x >= size:
            tail_x = (size - length) // 2
            head_x = tail_x + length - 1
            positions = [(head_x - i, center_y) for i in range(length)]

        for x, y in positions:
            self.snake.append((x, y))
            self.snake_set.add((x, y))
            self.free_tiles.discard((x, y))
            self.grid[y][x] = 1

    def _next_head(self, direction: str) -> tuple[int, int]:
        head_x, head_y = self.snake[0]
        if direction == "up":
            return head_x, head_y - 1
        if direction == "down":
            return head_x, head_y + 1
        if direction == "left":
            return head_x - 1, head_y
        return head_x + 1, head_y

    def _in_bounds(self, x: int, y: int) -> bool:
        size = self.config.grid_size
        return 0 <= x < size and 0 <= y < size

    def move(self) -> bool:
        if not self.alive:
            return False

        self.direction = self.pending_direction
        new_x, new_y = self._next_head(self.direction)

        if self.config.wrap_walls:
            size = self.config.grid_size
            new_x %= size
            new_y %= size
        elif not self._in_bounds(new_x, new_y):
            self.alive = False
            return False

        new_head = (new_x, new_y)
        growing = new_head in self.apples
        tail = self.snake[-1]

        if new_head in self.snake_set and not (not growing and new_head == tail):
            self.alive = False
            return False

        self.snake.appendleft(new_head)
        self.snake_set.add(new_head)
        self.free_tiles.discard(new_head)

        if growing:
            self.apples.discard(new_head)
            self.score += 1
        else:
            old_tail = self.snake.pop()
            self.snake_set.discard(old_tail)
            self.free_tiles.add(old_tail)

        self.replenish_apples()
        return True

    def replenish_apples(self) -> None:
        target = min(self.config.apples, len(self.free_tiles))
        while len(self.apples) < target and self.free_tiles:
            pos = random.choice(tuple(self.free_tiles))
            self.apples.add(pos)
            self.free_tiles.discard(pos)

    def queue_direction(self, new_direction: str) -> None:
        opposites = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }
        if new_direction not in opposites:
            return
        if len(self.snake) > 1 and opposites[new_direction] == self.direction:
            return
        self.pending_direction = new_direction


class SnakeApp:
    BG = "#101418"
    BOARD_BG = "#1c2229"
    SIDEBAR_BG = "#0f1720"
    GRID_COLOR = "#293340"
    SNAKE_HEAD = "#45d483"
    SNAKE_BODY = "#1fb86b"
    APPLE_COLOR = "#ff5c74"
    TEXT_PRIMARY = "#e6eef7"
    TEXT_MUTED = "#95a4b8"
    ACCENT = "#42c4ff"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Snake Trainer")
        self.root.configure(bg=self.BG)
        self.root.minsize(980, 720)

        self.config = SnakeConfig()
        self.game = SnakeGame(self.config)
        self.after_id: str | None = None

        self._build_layout()
        self._bind_keys()
        self._apply_canvas_size()
        self.draw()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = tk.Frame(self.root, bg=self.BG)
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)
        container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            container,
            bg=self.BOARD_BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        self.sidebar = tk.Frame(container, bg=self.SIDEBAR_BG, width=300)
        self.sidebar.grid(row=0, column=1, sticky="ns")
        self.sidebar.grid_propagate(False)

        title = tk.Label(
            self.sidebar,
            text="Snake Controls",
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            font=("Helvetica", 18, "bold"),
        )
        title.pack(anchor="w", padx=16, pady=(16, 4))

        subtitle = tk.Label(
            self.sidebar,
            text="Tune settings, then press Start",
            fg=self.TEXT_MUTED,
            bg=self.SIDEBAR_BG,
            font=("Helvetica", 10),
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 12))

        self._build_status()
        self._build_controls()
        self._build_buttons()

    def _build_status(self) -> None:
        frame = tk.LabelFrame(
            self.sidebar,
            text="Status",
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            bd=1,
            font=("Helvetica", 10, "bold"),
            labelanchor="n",
        )
        frame.pack(fill="x", padx=16, pady=(0, 12))

        self.score_var = tk.StringVar(value="Score: 0")
        self.length_var = tk.StringVar(value=f"Length: {len(self.game.snake)}")
        self.state_var = tk.StringVar(value="State: Ready")

        for var in (self.score_var, self.length_var, self.state_var):
            tk.Label(
                frame,
                textvariable=var,
                fg=self.TEXT_PRIMARY,
                bg=self.SIDEBAR_BG,
                font=("Helvetica", 11),
                anchor="w",
            ).pack(fill="x", padx=10, pady=4)

    def _build_controls(self) -> None:
        frame = tk.LabelFrame(
            self.sidebar,
            text="Settings",
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            bd=1,
            font=("Helvetica", 10, "bold"),
            labelanchor="n",
        )
        frame.pack(fill="x", padx=16, pady=(0, 12))

        self.grid_size_var = tk.StringVar(value=str(self.config.grid_size))
        self.cell_size_var = tk.StringVar(value=str(self.config.cell_size))
        self.speed_var = tk.StringVar(value=str(self.config.speed_ms))
        self.apples_var = tk.StringVar(value=str(self.config.apples))
        self.length_setting_var = tk.StringVar(value=str(self.config.initial_length))
        self.wrap_var = tk.BooleanVar(value=self.config.wrap_walls)
        self.show_grid_var = tk.BooleanVar(value=self.config.show_grid)

        self._add_labeled_spinbox(frame, "Grid Size", self.grid_size_var)
        self._add_labeled_spinbox(frame, "Cell Size", self.cell_size_var)
        self._add_labeled_spinbox(frame, "Speed (ms)", self.speed_var)
        self._add_labeled_spinbox(frame, "Apples", self.apples_var)
        self._add_labeled_spinbox(frame, "Initial Length", self.length_setting_var)

        tk.Checkbutton(
            frame,
            text="Wrap through walls",
            variable=self.wrap_var,
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            selectcolor=self.SIDEBAR_BG,
            activebackground=self.SIDEBAR_BG,
            activeforeground=self.TEXT_PRIMARY,
            font=("Helvetica", 10),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        tk.Checkbutton(
            frame,
            text="Show grid lines",
            variable=self.show_grid_var,
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            selectcolor=self.SIDEBAR_BG,
            activebackground=self.SIDEBAR_BG,
            activeforeground=self.TEXT_PRIMARY,
            font=("Helvetica", 10),
        ).pack(anchor="w", padx=10, pady=(2, 10))

        hint = tk.Label(
            frame,
            text=(
                f"Ranges: grid {MIN_GRID_SIZE}-{MAX_GRID_SIZE}, cell {MIN_CELL_SIZE}-{MAX_CELL_SIZE}, "
                f"speed {MIN_SPEED_MS}-{MAX_SPEED_MS}, apples {MIN_APPLES}-{MAX_APPLES}"
            ),
            fg=self.TEXT_MUTED,
            bg=self.SIDEBAR_BG,
            justify="left",
            wraplength=260,
            font=("Helvetica", 9),
        )
        hint.pack(anchor="w", padx=10, pady=(0, 10))

    def _add_labeled_spinbox(self, parent: tk.Widget, label: str, var: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=self.SIDEBAR_BG)
        row.pack(fill="x", padx=10, pady=4)

        tk.Label(
            row,
            text=label,
            fg=self.TEXT_PRIMARY,
            bg=self.SIDEBAR_BG,
            font=("Helvetica", 10),
        ).pack(side="left")

        spin = tk.Spinbox(
            row,
            from_=0,
            to=999,
            textvariable=var,
            width=8,
            justify="center",
            bd=0,
            relief="flat",
            bg="#e8eef5",
            fg="#1a2734",
            font=("Helvetica", 10),
        )
        spin.pack(side="right")

    def _build_buttons(self) -> None:
        frame = tk.Frame(self.sidebar, bg=self.SIDEBAR_BG)
        frame.pack(fill="x", padx=16, pady=(0, 10))

        self.start_btn = self._button(frame, "Start", self.start_game)
        self.start_btn.pack(fill="x", pady=4)

        self.pause_btn = self._button(frame, "Pause", self.toggle_pause)
        self.pause_btn.pack(fill="x", pady=4)

        self.reset_btn = self._button(frame, "Reset", self.reset_game)
        self.reset_btn.pack(fill="x", pady=4)

        self.apply_btn = self._button(frame, "Apply Settings", self.apply_settings)
        self.apply_btn.pack(fill="x", pady=4)

        footer = tk.Label(
            self.sidebar,
            text="Move: Arrow keys / WASD",
            fg=self.TEXT_MUTED,
            bg=self.SIDEBAR_BG,
            font=("Helvetica", 10),
        )
        footer.pack(anchor="w", padx=16, pady=(4, 10))

    def _button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            fg="#09141f",
            bg=self.ACCENT,
            activebackground="#74d8ff",
            activeforeground="#09141f",
            bd=0,
            relief="flat",
            font=("Helvetica", 11, "bold"),
            padx=10,
            pady=8,
            cursor="hand2",
        )

    def _bind_keys(self) -> None:
        self.root.bind("<Up>", lambda _e: self.game.queue_direction("up"))
        self.root.bind("<Down>", lambda _e: self.game.queue_direction("down"))
        self.root.bind("<Left>", lambda _e: self.game.queue_direction("left"))
        self.root.bind("<Right>", lambda _e: self.game.queue_direction("right"))
        self.root.bind("w", lambda _e: self.game.queue_direction("up"))
        self.root.bind("s", lambda _e: self.game.queue_direction("down"))
        self.root.bind("a", lambda _e: self.game.queue_direction("left"))
        self.root.bind("d", lambda _e: self.game.queue_direction("right"))
        self.root.bind("<space>", lambda _e: self.toggle_pause())

    def _parse_int(self, raw: str, low: int, high: int, label: str) -> int:
        try:
            value = int(raw)
        except ValueError:
            raise ValueError(f"{label} must be an integer.")
        if not (low <= value <= high):
            raise ValueError(f"{label} must be between {low} and {high}.")
        return value

    def apply_settings(self) -> None:
        try:
            grid_size = self._parse_int(self.grid_size_var.get(), MIN_GRID_SIZE, MAX_GRID_SIZE, "Grid size")
            cell_size = self._parse_int(self.cell_size_var.get(), MIN_CELL_SIZE, MAX_CELL_SIZE, "Cell size")
            speed_ms = self._parse_int(self.speed_var.get(), MIN_SPEED_MS, MAX_SPEED_MS, "Speed")
            apples = self._parse_int(self.apples_var.get(), MIN_APPLES, MAX_APPLES, "Apples")
            initial_length = self._parse_int(
                self.length_setting_var.get(),
                MIN_INITIAL_LENGTH,
                grid_size,
                "Initial length",
            )
        except ValueError as exc:
            messagebox.showerror("Invalid Setting", str(exc))
            return

        max_apples_by_tiles = max(1, grid_size * grid_size - initial_length)
        if apples > max_apples_by_tiles:
            messagebox.showerror(
                "Invalid Setting",
                (
                    f"Apples is too high for the selected grid and snake length. "
                    f"Maximum allowed is {max_apples_by_tiles}."
                ),
            )
            return

        self.config = SnakeConfig(
            grid_size=grid_size,
            cell_size=cell_size,
            speed_ms=speed_ms,
            apples=apples,
            initial_length=initial_length,
            wrap_walls=self.wrap_var.get(),
            show_grid=self.show_grid_var.get(),
        )
        self.game = SnakeGame(self.config)
        self._cancel_loop()
        self._apply_canvas_size()
        self.state_var.set("State: Ready")
        self.draw()

    def _apply_canvas_size(self) -> None:
        side_pixels = self.config.grid_size * self.config.cell_size
        self.canvas.configure(width=side_pixels, height=side_pixels)

    def _cancel_loop(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def start_game(self) -> None:
        if not self.game.alive:
            self.game.reset()
        self.game.running = True
        self.state_var.set("State: Running")
        self.tick()

    def toggle_pause(self) -> None:
        if not self.game.alive:
            return
        self.game.running = not self.game.running
        if self.game.running:
            self.state_var.set("State: Running")
            self.tick()
        else:
            self.state_var.set("State: Paused")
            self._cancel_loop()

    def reset_game(self) -> None:
        self._cancel_loop()
        self.game = SnakeGame(self.config)
        self.state_var.set("State: Ready")
        self.draw()

    def tick(self) -> None:
        self._cancel_loop()
        if not self.game.running:
            return

        if not self.game.move():
            self.game.running = False
            self.state_var.set("State: Game Over")
            self.draw()
            return

        self.draw()
        self.after_id = self.root.after(self.config.speed_ms, self.tick)

    def draw(self) -> None:
        self.canvas.delete("all")
        size = self.config.grid_size
        cell = self.config.cell_size

        if self.config.show_grid:
            for i in range(size + 1):
                pos = i * cell
                self.canvas.create_line(0, pos, size * cell, pos, fill=self.GRID_COLOR)
                self.canvas.create_line(pos, 0, pos, size * cell, fill=self.GRID_COLOR)

        for x, y in self.game.apples:
            x1, y1 = x * cell + 4, y * cell + 4
            x2, y2 = (x + 1) * cell - 4, (y + 1) * cell - 4
            self.canvas.create_oval(x1, y1, x2, y2, fill=self.APPLE_COLOR, outline="")

        for idx, (x, y) in enumerate(self.game.snake):
            color = self.SNAKE_HEAD if idx == 0 else self.SNAKE_BODY
            x1, y1 = x * cell + 2, y * cell + 2
            x2, y2 = (x + 1) * cell - 2, (y + 1) * cell - 2
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        self.score_var.set(f"Score: {self.game.score}")
        self.length_var.set(f"Length: {len(self.game.snake)}")

        if not self.game.alive:
            side = size * cell
            self.canvas.create_rectangle(0, 0, side, side, fill="#000000", stipple="gray50", outline="")
            self.canvas.create_text(
                side // 2,
                side // 2 - 12,
                text="Game Over",
                fill=self.TEXT_PRIMARY,
                font=("Helvetica", 22, "bold"),
            )
            self.canvas.create_text(
                side // 2,
                side // 2 + 20,
                text="Press Reset or Start",
                fill=self.TEXT_MUTED,
                font=("Helvetica", 12),
            )


def main() -> None:
    root = tk.Tk()
    app = SnakeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
