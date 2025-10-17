# number_smash.py
import pygame
import random
import sys
import math
from collections import deque

# ----------------------------
# Configuration
# ----------------------------
GRID_ROWS = 8
GRID_COLS = 8
CELL_SIZE = 64
GRID_PADDING = 8
TOP_MARGIN = 120
WINDOW_BG = (30, 30, 40)
FPS = 60

# Animation & timing
NUMBER_CYCLE_INTERVAL = 700  # ms: how often each cell changes its number (gives "constantly moving numbers")
POP_ANIM_TIME = 200  # ms
SHAKE_ANIM_TIME = 220  # ms

# Colors for numbers 0-9 (vibrant palette)
NUM_COLORS = {
    0: (102, 197, 255),
    1: (255, 183, 197),
    2: (255, 223, 102),
    3: (188, 242, 129),
    4: (255, 159, 243),
    5: (255, 128, 128),
    6: (153, 204, 255),
    7: (179, 157, 219),
    8: (255, 205, 148),
    9: (200, 200, 200)
}
CELL_BG = (20, 24, 30)
GRID_BG = (45, 48, 55)
TEXT_COLOR = (240, 240, 240)
INSTR_COLOR = (200, 200, 200)
SCORE_COLOR = (255, 250, 200)

# ----------------------------
# Utilities
# ----------------------------
def clamp(n, a, b):
    return max(a, min(b, n))

# ----------------------------
# Cell class representing each square
# ----------------------------
class Cell:
    def __init__(self, row, col, size):
        self.row = row
        self.col = col
        self.size = size
        self.value = random.randint(0, 9)
        self.last_change = pygame.time.get_ticks() + random.randint(0, NUMBER_CYCLE_INTERVAL)
        self.pop_anim = 0  # 0 = none, else remaining ms
        self.shake_anim = 0
        self.falling = False  # falling animation flag

    def update_cycle(self, now):
        # Cycle numbers periodically for dynamic effect
        if now - self.last_change >= NUMBER_CYCLE_INTERVAL:
            self.value = random.randint(0, 9)
            self.last_change = now

    def start_pop(self):
        self.pop_anim = POP_ANIM_TIME

    def start_shake(self):
        self.shake_anim = SHAKE_ANIM_TIME

    def draw(self, surface, x, y, font):
        # Draw cell background
        rect = pygame.Rect(x, y, self.size, self.size)
        pygame.draw.rect(surface, CELL_BG, rect, border_radius=8)

        # If popping, slightly scale up
        scale = 1.0
        if self.pop_anim > 0:
            frac = self.pop_anim / POP_ANIM_TIME
            scale = 1.0 + 0.18 * frac  # pop bigger when just popped

        # Shake offset
        shake_x = 0
        if self.shake_anim > 0:
            shake_x = int(6 * math.sin((self.shake_anim / SHAKE_ANIM_TIME) * math.pi * 8))

        # Number surface
        num = str(self.value) if self.value is not None else ""
        if num != "":
            txt = font.render(num, True, TEXT_COLOR)
            tw, th = txt.get_size()
            # colored circle behind number
            color = NUM_COLORS.get(self.value, (180, 180, 180))
            # circle pos center
            cx = x + self.size // 2 + shake_x
            cy = y + self.size // 2
            radius = int(min(self.size // 2 - 8, (self.size // 2) * scale))
            pygame.draw.circle(surface, color, (cx, cy), radius)
            # draw number text centered
            surface.blit(txt, (cx - tw // 2, cy - th // 2))

    def tick(self, dt):
        if self.pop_anim > 0:
            self.pop_anim = max(0, self.pop_anim - dt)
        if self.shake_anim > 0:
            self.shake_anim = max(0, self.shake_anim - dt)


# ----------------------------
# Game class
# ----------------------------
class NumberSmashGame:
    def __init__(self, rows=GRID_ROWS, cols=GRID_COLS, cell_size=CELL_SIZE):
        pygame.init()
        pygame.display.set_caption("Number Smash — Smash 0s and 1s!")
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        width = cols * (cell_size + GRID_PADDING) + GRID_PADDING
        height = rows * (cell_size + GRID_PADDING) + GRID_PADDING + TOP_MARGIN
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 20)
        self.font_small = pygame.font.SysFont("Arial", 16)
        self.grid_x = GRID_PADDING
        self.grid_y = TOP_MARGIN
        self.running = True
        self.paused = False

        self.reset()

    def reset(self):
        self.grid = [[Cell(r, c, self.cell_size) for c in range(self.cols)] for r in range(self.rows)]
        self.score = 0
        self.message = "Click matching 0s or 1s (groups of 2+). Press R to restart. Q to quit."
        self.last_tick = pygame.time.get_ticks()
        self.show_instructions = True
        # ensure there's at least some possible match to start (optional)
        # skip guarantee to keep it simple/dynamic

    def draw_ui(self):
        # header / instructions
        title = self.font_big.render("Number Smash", True, SCORE_COLOR)
        self.screen.blit(title, (12, 12))
        sc = self.font_med.render(f"Score: {self.score}", True, SCORE_COLOR)
        self.screen.blit(sc, (12, 50))
        instr = self.font_small.render("Smash groups of 2+ zeros or ones. Click a cell to smash. R=Restart  Space=Pause", True, INSTR_COLOR)
        self.screen.blit(instr, (12, 82))

        # optional message at top-right
        msg = self.font_small.render(self.message, True, INSTR_COLOR)
        w = self.screen.get_width()
        self.screen.blit(msg, (w - msg.get_width() - 12, 50))

    def grid_to_screen(self, r, c):
        x = self.grid_x + c * (self.cell_size + GRID_PADDING)
        y = self.grid_y + r * (self.cell_size + GRID_PADDING)
        return x, y

    def screen_to_grid(self, mx, my):
        mx -= self.grid_x
        my -= self.grid_y
        if mx < 0 or my < 0:
            return None
        cell_w = self.cell_size + GRID_PADDING
        c = mx // cell_w
        r = my // cell_w
        if 0 <= r < self.rows and 0 <= c < self.cols:
            # ensure inside actual square area (not in padding)
            rx = mx % cell_w
            ry = my % cell_w
            if rx <= self.cell_size and ry <= self.cell_size:
                return int(r), int(c)
        return None

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def flood_group(self, start_r, start_c):
        # BFS for 4-way adjacent same value
        target = self.grid[start_r][start_c].value
        if target is None:
            return []
        visited = [[False]*self.cols for _ in range(self.rows)]
        q = deque()
        q.append((start_r, start_c))
        visited[start_r][start_c] = True
        group = [(start_r, start_c)]
        while q:
            r, c = q.popleft()
            for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc) and not visited[nr][nc]:
                    cell = self.grid[nr][nc]
                    if cell.value == target:
                        visited[nr][nc] = True
                        q.append((nr, nc))
                        group.append((nr, nc))
        return group

    def smash_at(self, r, c):
        # attempt to smash the group at r,c
        cell = self.grid[r][c]
        val = cell.value
        if val not in (0, 1):
            # cannot smash distractors
            cell.start_shake()
            self.message = "You can only smash groups of 0s or 1s!"
            return False
        group = self.flood_group(r, c)
        if len(group) < 2:
            cell.start_shake()
            self.message = f"Need group of 2+ {val}s to smash (found {len(group)})."
            return False
        # smash: clear those cells
        for (gr, gc) in group:
            self.grid[gr][gc].start_pop()
            # mark as cleared after short delay (we'll directly clear)
            self.grid[gr][gc].value = None
        self.apply_gravity()
        # scoring: reward group_size * (value + 1)
        gain = len(group) * (val + 1)
        self.score += gain
        self.message = f"Smashed {len(group)} of {val}! +{gain} points"
        return True

    def apply_gravity(self):
        # For each column, let numbers fall down to bottom, new random numbers spawn on top
        for c in range(self.cols):
            stack = []
            for r in range(self.rows):
                val = self.grid[r][c].value
                if val is not None:
                    stack.append(val)
            # fill bottom up
            rptr = self.rows - 1
            for val in reversed(stack):
                self.grid[rptr][c].value = val
                rptr -= 1
            # fill remaining top cells with new random numbers
            while rptr >= 0:
                self.grid[rptr][c].value = random.randint(0, 9)
                rptr -= 1
        # small chance to randomize some cells slightly to keep dynamic visuals
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c].last_change = pygame.time.get_ticks()

    def update(self, dt):
        now = pygame.time.get_ticks()
        if not self.paused:
            # update cycle for each cell (number change)
            for r in range(self.rows):
                for c in range(self.cols):
                    cell = self.grid[r][c]
                    cell.update_cycle(now)
                    cell.tick(dt)

    def draw(self):
        self.screen.fill(WINDOW_BG)
        # grid background area
        gw = self.cols * (self.cell_size + GRID_PADDING) + GRID_PADDING
        gh = self.rows * (self.cell_size + GRID_PADDING) + GRID_PADDING
        pygame.draw.rect(self.screen, GRID_BG, (self.grid_x - GRID_PADDING//2, self.grid_y - GRID_PADDING//2, gw, gh), border_radius=12)

        # draw grid cells
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.grid_to_screen(r, c)
                cell = self.grid[r][c]
                cell.draw(self.screen, x, y, self.font_big)

        # UI overlays
        self.draw_ui()

        # If paused or showing instructions overlay
        if self.paused:
            overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            overlay.fill((8, 8, 12, 160))
            self.screen.blit(overlay, (0,0))
            txt = self.font_big.render("PAUSED", True, (240,240,240))
            self.screen.blit(txt, ((self.screen.get_width()-txt.get_width())//2, 200))
            hint = self.font_med.render("Press SPACE to resume", True, INSTR_COLOR)
            self.screen.blit(hint, ((self.screen.get_width()-hint.get_width())//2, 250))

        if self.show_instructions:
            self.draw_instructions()

        pygame.display.flip()

    def draw_instructions(self):
        w = self.screen.get_width()
        h = self.screen.get_height()
        overlay = pygame.Surface((w-80, h-160), pygame.SRCALPHA)
        overlay.fill((12, 14, 18, 230))
        # centered
        ox = 40
        oy = 60
        self.screen.blit(overlay, (ox, oy))
        title = self.font_big.render("How to play — Number Smash", True, SCORE_COLOR)
        self.screen.blit(title, (ox+20, oy+18))
        lines = [
            "• The grid contains numbers 0–9 which constantly change every moment.",
            "• You may SMASH only groups of 2 or more same-number tiles when that number is 0 or 1.",
            "• Click a tile (left mouse). If it is 0 or 1 and part of a group (>=2), the whole group is removed.",
            "• Numbers above fall down and new numbers spawn at the top.",
            "• Distractors: numbers 2–9 cannot be smashed (but they'll block matches until they change).",
            "• Controls: Click = Smash | R = Restart | SPACE = Pause/Unpause | Q / Close = Quit",
            "• Score increases by group_size * (value + 1). Have fun!"
        ]
        y = oy + 68
        for line in lines:
            txt = self.font_small.render(line, True, INSTR_COLOR)
            self.screen.blit(txt, (ox + 20, y))
            y += 28

        note = self.font_med.render("Click anywhere on this box to continue...", True, (210,210,210))
        self.screen.blit(note, (ox + 20, y + 6))

    def handle_click(self, pos):
        # clicking while instructions visible dismisses them
        if self.show_instructions:
            # any click inside the instruction overlay dismisses
            w = self.screen.get_width()
            h = self.screen.get_height()
            rect = pygame.Rect(40, 60, w-80, h-160)
            if rect.collidepoint(pos):
                self.show_instructions = False
            return

        g = self.screen_to_grid(*pos)
        if g:
            r, c = g
            self.smash_at(r, c)

    def mainloop(self):
        while self.running:
            dt = self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.handle_click(ev.pos)
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_q:
                        self.running = False
                    elif ev.key == pygame.K_r:
                        self.reset()
                    elif ev.key == pygame.K_SPACE:
                        self.paused = not self.paused

            if not self.paused:
                self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = NumberSmashGame()
    game.mainloop()
