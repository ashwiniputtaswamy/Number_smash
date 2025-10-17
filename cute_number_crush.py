"""
cute_number_crush.py
A Candy-Crush-like match-3 game using cute numbers, built with Pygame.

Controls:
 - Click one tile, then click an adjacent tile to swap.
 - R : Restart
 - SPACE : Pause / Resume
 - Q or window close : Quit
"""

import pygame
import random
import sys
from collections import deque

# ---------------- Configuration ----------------
ROWS = 8
COLS = 8
TILE_SIZE = 70
PADDING = 8
TOP_MARGIN = 120
FPS = 60

# Use 6 types (numbers 0..5) like candy crush variety
TILE_TYPES = list(range(6))  # numbers shown on tiles
ANIM_SPEED = 10  # pixels per frame for swap / fall animations
POP_ANIM_MS = 220
SWAP_ANIM_FRAMES = 12

# Colors (gentle pastel palette)
BG = (245, 248, 255)
BOARD_BG = (235, 240, 250)
TILE_BG = (250, 250, 255)
TEXT_COLOR = (28, 30, 33)
SCORE_COLOR = (60, 60, 90)
INSTR_COLOR = (80, 86, 110)

TYPE_COLORS = {
    0: (255, 179, 186),  # pink
    1: (255, 223, 186),  # peach
    2: (255, 255, 186),  # yellow
    3: (186, 255, 201),  # mint
    4: (186, 225, 255),  # baby blue
    5: (215, 186, 255),  # lavender
}

# Scoring
BASE_SCORE_PER_TILE = 10

# ---------------- Helper utilities ----------------
def clamp(x, a, b):
    return max(a, min(b, x))

# ---------------- Tile / Board ----------------
class Tile:
    def __init__(self, type_id):
        self.type = type_id  # integer type
        self.pop_timer = 0   # pop animation if removed
        self.falling = False # used if animating fall

class Board:
    def __init__(self, rows=ROWS, cols=COLS):
        self.rows = rows
        self.cols = cols
        self.grid = [[Tile(random.choice(TILE_TYPES)) for _ in range(cols)] for _ in range(rows)]
        # ensure no immediate matches on initial fill
        self._remove_initial_matches()

    def _remove_initial_matches(self):
        # Regenerate any tile that forms a match immediately
        for r in range(self.rows):
            for c in range(self.cols):
                while True:
                    if self._is_match_at(r, c):
                        self.grid[r][c] = Tile(random.choice(TILE_TYPES))
                    else:
                        break

    def _is_match_at(self, r, c):
        """Check if tile at r,c forms a 3+ match with neighbors (used only on init)."""
        t = self.grid[r][c].type
        # horizontal
        count = 1
        cc = c - 1
        while cc >= 0 and self.grid[r][cc].type == t:
            count += 1; cc -= 1
        cc = c + 1
        while cc < self.cols and self.grid[r][cc].type == t:
            count += 1; cc += 1
        if count >= 3:
            return True
        # vertical
        count = 1
        rr = r - 1
        while rr >= 0 and self.grid[rr][c].type == t:
            count += 1; rr -= 1
        rr = r + 1
        while rr < self.rows and self.grid[rr][c].type == t:
            count += 1; rr += 1
        return count >= 3

    def get(self, r, c):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return None

    def swap(self, r1, c1, r2, c2):
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]

    def find_matches(self):
        """Return set of coordinates that form matches (3+ in a row or column)."""
        to_remove = set()
        # horizontal
        for r in range(self.rows):
            c = 0
            while c < self.cols:
                start = c
                t = self.grid[r][c].type
                c += 1
                while c < self.cols and self.grid[r][c].type == t:
                    c += 1
                length = c - start
                if length >= 3:
                    for cc in range(start, c):
                        to_remove.add((r, cc))
        # vertical
        for c in range(self.cols):
            r = 0
            while r < self.rows:
                start = r
                t = self.grid[r][c].type
                r += 1
                while r < self.rows and self.grid[r][c].type == t:
                    r += 1
                length = r - start
                if length >= 3:
                    for rr in range(start, r):
                        to_remove.add((rr, c))
        return to_remove

    def remove_and_collapse(self, remove_coords):
        """Remove tiles at given coords, collapse columns, fill with new tiles, return total tiles removed."""
        # Mark removed positions with None
        removed = 0
        for (r, c) in remove_coords:
            if self.grid[r][c] is not None:
                self.grid[r][c] = None
                removed += 1

        # Collapse each column
        for c in range(self.cols):
            stack = []
            for r in range(self.rows - 1, -1, -1):
                if self.grid[r][c] is not None:
                    stack.append(self.grid[r][c])
            # fill from bottom
            for r in range(self.rows - 1, -1, -1):
                if stack:
                    self.grid[r][c] = stack.pop(0)  # pop from front since stack is bottom->top
                else:
                    self.grid[r][c] = Tile(random.choice(TILE_TYPES))
        return removed

# ---------------- Game ----------------
class CandyLikeGame:
    def __init__(self):
        pygame.init()
        # runtime scale: used to increase sizes for touch-friendly displays
        self.scale = 1.0
        # derived sizes (will be updated by apply_scale)
        self.tile_size = TILE_SIZE
        self.padding = PADDING
        self.top_margin = TOP_MARGIN
        self.apply_scale()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Cute Number Crush")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("Poppins", 26, bold=True)
        self.font_tile = pygame.font.SysFont("Poppins", 28, bold=True)
        self.font_small = pygame.font.SysFont("Poppins", 16)
        self.board = Board()
        self.selected = None  # (r,c) first click
        self.animating = False
        self.swap_animation = None  # dict holding swap animation info
        self.score = 0
        self.combo = 0
        self.paused = False
        self.show_instructions = True

        # Pre-calc board rect (use scaled values)
        self.board_x = self.padding
        self.board_y = self.top_margin
        self.board_w = COLS * (self.tile_size + self.padding) + self.padding
        self.board_h = ROWS * (self.tile_size + self.padding) + self.padding

        # Initial check: clear any immediate matches (should already be done)
        self.resolve_all_matches_initial()

    # ---------- helpers ----------
    def tile_to_pixel(self, r, c):
        x = self.board_x + self.padding + c * (self.tile_size + self.padding)
        y = self.board_y + self.padding + r * (self.tile_size + self.padding)
        return x, y

    def pixel_to_tile(self, mx, my):
        mx -= self.board_x + self.padding
        my -= self.board_y + self.padding
        if mx < 0 or my < 0:
            return None
        cell_w = self.tile_size + self.padding
        c = int(mx // cell_w)
        r = int(my // cell_w)
        if 0 <= r < ROWS and 0 <= c < COLS:
            # ensure inside tile area (not padding)
            rx = mx % cell_w
            ry = my % cell_w
            if rx <= self.tile_size and ry <= self.tile_size:
                return (r, c)
        return None

    def draw_board(self):
        # background
        pygame.draw.rect(self.screen, BOARD_BG, (self.board_x, self.board_y, self.board_w, self.board_h), border_radius=14)
        # draw tiles
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                tile = self.board.get(r, c)
                if tile is None:
                    continue
                # if swapping animation affects these tiles, let animation handle draw
                if self.swap_animation and ((r, c) == self.swap_animation.get('a') or (r, c) == self.swap_animation.get('b')):
                    continue
                x, y = self.tile_to_pixel(r, c)
                self.draw_tile(tile, x, y)

        # draw swap anim overlays if any
        if self.swap_animation:
            self.draw_swap_anim()

    def draw_tile(self, tile, x, y, alpha=255, scale=1.0):
        rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
        # tile background (rounded)
        color = TYPE_COLORS.get(tile.type, (200,200,200))
        # soften color for background and a small white highlight
        base = color
        pygame.draw.rect(self.screen, base, rect, border_radius=10)
        # small inner box for aesthetic
        # inner padding scales with tile size
        inner_pad = max(6, int(self.tile_size * 0.14))
        inner = rect.inflate(-inner_pad * 2, -inner_pad * 2)
        pygame.draw.rect(self.screen, TILE_BG, inner, border_radius=8)
        # number text
        num_surf = self.font_tile.render(str(tile.type), True, TEXT_COLOR)
        # adjust for scale if any
        if scale != 1.0:
            num_surf = pygame.transform.rotozoom(num_surf, 0, scale)
        tw, th = num_surf.get_size()
        tx = x + (self.tile_size - tw) // 2
        ty = y + (self.tile_size - th) // 2
        # apply alpha
        if alpha < 255:
            num_surf.set_alpha(alpha)
        self.screen.blit(num_surf, (tx, ty))

    def draw_swap_anim(self):
        sa = self.swap_animation
        # positions for a and b interpolated
        a_pos = sa['a']
        b_pos = sa['b']
        progress = sa['progress']  # 0..1
        ax, ay = self.tile_to_pixel(*a_pos)
        bx, by = self.tile_to_pixel(*b_pos)
        # interpolate
        axn = ax + (bx - ax) * progress
        ayn = ay + (by - ay) * progress
        bxn = bx + (ax - bx) * progress
        byn = by + (ay - by) * progress
        # draw the two tiles moving
        tile_a = sa['tile_a']
        tile_b = sa['tile_b']
        self.draw_tile(tile_a, axn, ayn)
        self.draw_tile(tile_b, bxn, byn)

    # ---------- matching & resolving ----------
    def resolve_all_matches_initial(self):
        # run a loop to remove matches (rare) until none remain
        while True:
            matches = self.board.find_matches()
            if not matches:
                break
            self.board.remove_and_collapse(matches)

    def find_and_resolve_matches(self):
        """Find matches, remove them, apply gravity, refill, return total removed and whether any removed."""
        total_removed = 0
        chain = 0
        while True:
            matches = self.board.find_matches()
            if not matches:
                break
            chain += 1
            removed = self.board.remove_and_collapse(matches)
            total_removed += removed
            # increase score with chain multiplier
            self.score += removed * BASE_SCORE_PER_TILE * chain
        return total_removed

    # ---------- swap logic ----------
    def try_swap(self, a, b):
        """Try to swap two tiles. Perform animated swap and keep if creates match, otherwise revert."""
        if self.animating:
            return
        (r1, c1) = a
        (r2, c2) = b
        # must be adjacent
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            return
        # set up animation objects
        tile_a = self.board.get(r1, c1)
        tile_b = self.board.get(r2, c2)
        if tile_a is None or tile_b is None:
            return
        # start swap animation
        self.swap_animation = {
            'a': (r1, c1),
            'b': (r2, c2),
            'tile_a': tile_a,
            'tile_b': tile_b,
            'frames': SWAP_ANIM_FRAMES,
            'frame': 0,
            'progress': 0.0,
            'reverting': False,
            'keep': False
        }
        # actually swap in model for match detection after anim completes
        self.animating = True

    def update_swap_anim(self):
        if not self.swap_animation:
            return
        sa = self.swap_animation
        sa['frame'] += 1
        sa['progress'] = sa['frame'] / sa['frames']
        if sa['frame'] >= sa['frames']:
            # complete swap in model
            a = sa['a']; b = sa['b']
            self.board.swap(*a, *b)
            # check for matches
            matches = self.board.find_matches()
            if matches:
                # keep swap; resolve matches
                self.animating = False
                self.swap_animation = None
                removed = self.find_and_resolve_matches()
                if removed:
                    self.combo += 1
                else:
                    self.combo = 0
            else:
                # revert swap with animation reversed
                if not sa['reverting']:
                    sa['reverting'] = True
                    sa['frame'] = 0
                else:
                    # second time means revert completed: perform revert in model
                    self.board.swap(*a, *b)  # swap back
                    self.animating = False
                    self.swap_animation = None

    # ---------- events ----------
    def handle_click(self, pos):
        if self.show_instructions:
            self.show_instructions = False
            return
        if self.animating or self.paused:
            return
        clicked = self.pixel_to_tile(*pos)
        if not clicked:
            return
        if self.selected is None:
            self.selected = clicked
        else:
            if clicked == self.selected:
                self.selected = None
                return
            # attempt swap
            self.try_swap(self.selected, clicked)
            self.selected = None

    def apply_scale(self):
        """Apply current self.scale to derived layout sizes."""
        self.tile_size = max(24, int(TILE_SIZE * self.scale))
        self.padding = max(4, int(PADDING * self.scale))
        self.top_margin = max(60, int(TOP_MARGIN * self.scale))
        self.width = COLS * (self.tile_size + self.padding) + self.padding
        self.height = ROWS * (self.tile_size + self.padding) + self.padding + self.top_margin

    def toggle_touch_mode(self, enable=None):
        """Toggle touch-friendly (larger UI) mode. If enable is None, toggle current state."""
        if enable is None:
            if self.scale == 1.0:
                self.scale = 1.6
            else:
                self.scale = 1.0
        else:
            self.scale = 1.6 if enable else 1.0
        self.apply_scale()
        # recreate display surface at new size
        try:
            self.screen = pygame.display.set_mode((self.width, self.height))
        except Exception:
            pass

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        is_fs = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        if not is_fs:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode((self.width, self.height))

    # ---------- draw UI ----------
    def draw_ui(self):
        # title
        title = self.font_big.render("Cute Number Crush", True, SCORE_COLOR)
        self.screen.blit(title, (12, 14))
        # score box
        sc = self.font_small.render(f"Score: {self.score}", True, INSTR_COLOR)
        self.screen.blit(sc, (12, 52))
        instr = self.font_small.render("Click two adjacent tiles to swap. Match 3+ to clear. R=Restart, SPACE=Pause", True, INSTR_COLOR)
        self.screen.blit(instr, (12, 72))
        if self.paused:
            p = self.font_big.render("PAUSED", True, (90, 90, 120))
            self.screen.blit(p, ((self.width - p.get_width()) // 2, 40))
        if self.show_instructions:
            self.draw_instructions_overlay()

    def draw_instructions_overlay(self):
        w = self.width - 120
        h = 220
        ox = 60
        oy = (self.height - h) // 2
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((255, 255, 255, 230))
        pygame.draw.rect(s, (245,245,250), (0,0,w,h), border_radius=12)
        self.screen.blit(s, (ox, oy))
        t1 = self.font_big.render("How to play", True, (60,60,80))
        self.screen.blit(t1, (ox + 20, oy + 16))
        lines = [
            "Swap adjacent numbers to make a row or column of 3+ identical numbers.",
            "When matched, tiles disappear, tiles above fall down, and new tiles spawn.",
            "Chain reactions give more points. Try to clear as many as possible!",
            "",
            "Controls: Click tiles to swap | SPACE = Pause | R = Restart | Q = Quit"
        ]
        y = oy + 60
        for ln in lines:
            txt = self.font_small.render(ln, True, (80,90,110))
            self.screen.blit(txt, (ox + 20, y))
            y += 26

    # ---------- main loop ----------
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                # Mouse click (mouse emulates touch on many smartboards)
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx, my = ev.pos
                    # ensure click inside board area
                    if (self.board_x <= mx <= self.board_x + self.board_w and
                        self.board_y <= my <= self.board_y + self.board_h):
                        self.handle_click(ev.pos)
                # Touch events: map FINGERDOWN to mouse click position scaled to window
                if ev.type == pygame.FINGERDOWN:
                    # Touch positions are in normalized (0..1) window coords
                    w, h = pygame.display.get_surface().get_size()
                    tx = int(ev.x * w)
                    ty = int(ev.y * h)
                    if (self.board_x <= tx <= self.board_x + self.board_w and
                        self.board_y <= ty <= self.board_y + self.board_h):
                        self.handle_click((tx, ty))
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_r:
                        self.__init__()  # full reset
                    if ev.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    if ev.key == pygame.K_t:
                        # toggle touch-friendly mode (larger UI)
                        self.toggle_touch_mode()
                        # regenerate fonts scaled to tile size
                        base = max(14, int(26 * self.scale))
                        self.font_big = pygame.font.SysFont("Poppins", base, bold=True)
                        self.font_tile = pygame.font.SysFont("Poppins", max(14, int(28 * self.scale)), bold=True)
                        self.font_small = pygame.font.SysFont("Poppins", max(10, int(16 * self.scale)))
                    if ev.key == pygame.K_f:
                        self.toggle_fullscreen()
                    if ev.key == pygame.K_q:
                        pygame.quit(); sys.exit()

            if not self.paused:
                # update animations
                if self.swap_animation:
                    self.update_swap_anim()

                # after resolving matches, always check for any leftover matches (cascades)
                if not self.animating and not self.swap_animation:
                    matches = self.board.find_matches()
                    if matches:
                        removed = self.board.remove_and_collapse(matches)
                        # reward points, chain multiplier
                        if removed:
                            self.combo += 1
                            self.score += removed * BASE_SCORE_PER_TILE * max(1, self.combo)
                        else:
                            self.combo = 0

            # drawing
            self.screen.fill(BG)
            self.draw_board()
            # highlight selected tile
            if self.selected:
                rx, ry = self.tile_to_pixel(*self.selected)
                pygame.draw.rect(self.screen, (255, 200, 200), (rx-4, ry-4, self.tile_size+8, self.tile_size+8), width=4, border_radius=12)
            self.draw_ui()
            pygame.display.flip()

# ---------------- Run game ----------------
if __name__ == "__main__":
    game = CandyLikeGame()
    game.run()
