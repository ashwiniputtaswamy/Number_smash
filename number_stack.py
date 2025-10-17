import pygame
import random
import sys
from collections import deque

# ----------------------------
# CONFIGURATION
# ----------------------------
ROWS, COLS = 10, 7
CELL_SIZE = 60
GRID_PADDING = 5
TOP_MARGIN = 120
FPS = 60

BG_COLOR = (25, 25, 30)
GRID_COLOR = (45, 45, 50)
CELL_COLOR = (60, 60, 65)
NUM_COLOR = (230, 230, 230)
SPECIAL_COLOR = (180, 220, 255)
TEXT_COLOR = (240, 240, 240)

FALL_INTERVAL = 800  # ms: time between new falling numbers
FALL_SPEED = 6        # pixels per frame (falling speed)

# ----------------------------
# GAME CLASS
# ----------------------------
class NumberStack:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Number Stack — Smash 0s & 1s")

        width = COLS * (CELL_SIZE + GRID_PADDING) + GRID_PADDING
        height = ROWS * (CELL_SIZE + GRID_PADDING) + GRID_PADDING + TOP_MARGIN
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 18)

        self.grid_x = GRID_PADDING
        self.grid_y = TOP_MARGIN
        self.running = True
        self.reset()

    def reset(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.falling_number = None
        self.fall_y = 0
        self.fall_col = random.randint(0, COLS - 1)
        self.fall_value = random.randint(0, 9)
        self.last_fall_time = pygame.time.get_ticks()
        self.paused = False
        self.score = 0
        self.game_over = False
        self.message = "Click groups of 2+ zeros or ones to smash!"

    # ------------- Grid helpers ----------------
    def grid_to_screen(self, r, c):
        x = self.grid_x + c * (CELL_SIZE + GRID_PADDING)
        y = self.grid_y + r * (CELL_SIZE + GRID_PADDING)
        return x, y

    def in_bounds(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

    # ------------- Falling logic ----------------
    def spawn_new_number(self):
        self.fall_col = random.randint(0, COLS - 1)
        self.fall_value = random.randint(0, 9)
        self.fall_y = 0
        self.falling_number = True

        # If top cell in that column is filled — Game Over
        if self.grid[0][self.fall_col] is not None:
            self.game_over = True
            self.falling_number = False
            self.message = "Game Over! Press R to restart."

    def drop_number(self):
        """Moves falling number down until it stacks"""
        if not self.falling_number or self.game_over:
            return

        # Find where it should land
        for row in range(ROWS):
            below_filled = (
                row == ROWS - 1 or self.grid[row + 1][self.fall_col] is not None
            )
            if below_filled:
                # If reached the bottom or above a filled cell
                if self.fall_y >= row * (CELL_SIZE + GRID_PADDING):
                    # Land it
                    self.grid[row][self.fall_col] = self.fall_value
                    self.falling_number = False
                    break

        self.fall_y += FALL_SPEED

    # ------------- Group detection ----------------
    def find_group(self, start_r, start_c):
        target = self.grid[start_r][start_c]
        if target not in (0, 1):
            return []
        visited = [[False]*COLS for _ in range(ROWS)]
        q = deque()
        q.append((start_r, start_c))
        visited[start_r][start_c] = True
        group = [(start_r, start_c)]
        while q:
            r, c = q.popleft()
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if self.in_bounds(nr, nc) and not visited[nr][nc]:
                    if self.grid[nr][nc] == target:
                        visited[nr][nc] = True
                        q.append((nr, nc))
                        group.append((nr, nc))
        return group

    def smash(self, r, c):
        if self.grid[r][c] not in (0, 1):
            self.message = "Only zeros or ones can be smashed!"
            return
        group = self.find_group(r, c)
        if len(group) < 2:
            self.message = f"Need at least 2 matching {self.grid[r][c]}s!"
            return

        # Smash them (remove)
        for gr, gc in group:
            self.grid[gr][gc] = None
        self.score += len(group) * 10
        self.message = f"Smashed {len(group)} tiles! +{len(group)*10} points."
        self.apply_gravity()

    def apply_gravity(self):
        """Make numbers fall down to fill empty spaces"""
        for c in range(COLS):
            stack = [self.grid[r][c] for r in range(ROWS) if self.grid[r][c] is not None]
            for r in range(ROWS - 1, -1, -1):
                if stack:
                    self.grid[r][c] = stack.pop()
                else:
                    self.grid[r][c] = None

    # ------------- Drawing ----------------
    def draw_grid(self):
        for r in range(ROWS):
            for c in range(COLS):
                x, y = self.grid_to_screen(r, c)
                pygame.draw.rect(self.screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE), border_radius=6)
                val = self.grid[r][c]
                if val is not None:
                    color = SPECIAL_COLOR if val in (0, 1) else NUM_COLOR
                    text = self.font_big.render(str(val), True, color)
                    self.screen.blit(
                        text, (x + CELL_SIZE//2 - text.get_width()//2, y + CELL_SIZE//2 - text.get_height()//2)
                    )

    def draw_falling(self):
        if not self.falling_number or self.game_over:
            return
        c = self.fall_col
        val = self.fall_value
        x = self.grid_x + c * (CELL_SIZE + GRID_PADDING)
        y = self.grid_y + self.fall_y
        pygame.draw.rect(self.screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE), border_radius=6)
        color = SPECIAL_COLOR if val in (0, 1) else NUM_COLOR
        text = self.font_big.render(str(val), True, color)
        self.screen.blit(text, (x + CELL_SIZE//2 - text.get_width()//2, y + CELL_SIZE//2 - text.get_height()//2))

    def draw_ui(self):
        title = self.font_big.render("Number Stack", True, TEXT_COLOR)
        self.screen.blit(title, (10, 15))
        score_text = self.font_small.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_text, (10, 60))
        msg = self.font_small.render(self.message, True, (180, 180, 180))
        self.screen.blit(msg, (10, 90))

    # ------------- Events ----------------
    def handle_click(self, pos):
        if self.game_over:
            return
        mx, my = pos
        for r in range(ROWS):
            for c in range(COLS):
                x, y = self.grid_to_screen(r, c)
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                if rect.collidepoint(mx, my) and self.grid[r][c] is not None:
                    self.smash(r, c)
                    return

    # ------------- Main loop ----------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.screen.fill(BG_COLOR)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.running = False
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused

            if not self.paused and not self.game_over:
                now = pygame.time.get_ticks()
                if not self.falling_number and now - self.last_fall_time > FALL_INTERVAL:
                    self.spawn_new_number()
                    self.last_fall_time = now

                if self.falling_number:
                    self.drop_number()

            # Draw everything
            pygame.draw.rect(
                self.screen, GRID_COLOR,
                (self.grid_x - GRID_PADDING//2, self.grid_y - GRID_PADDING//2,
                 COLS*(CELL_SIZE+GRID_PADDING)+GRID_PADDING, ROWS*(CELL_SIZE+GRID_PADDING)+GRID_PADDING),
                border_radius=10
            )
            self.draw_grid()
            self.draw_falling()
            self.draw_ui()
            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    NumberStack().run()
