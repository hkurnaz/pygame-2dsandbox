"""Main entry point for MyArea game.

Run with: python3 -m game.main
"""

import pygame
import sys
import math
from game.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, SKY_BLUE, WHITE, YELLOW,
    TILE_SIZE, BREAK_RANGE
)
from game.player import Player
from game.world import World
from game.camera import Camera
from game.drops import DropManager
from game.inventory import Inventory
from game.blocks import get_break_time, get_block_name, is_block_breakable, BlockType


class Game:
    """Main game class."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MyArea")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Game objects
        self.world = World()
        self.world.generate()
        self.player = Player(0, 0)
        spawn_x, spawn_y = self.world.get_player_spawn()
        self.player.x = float(spawn_x)
        self.player.y = float(spawn_y)
        self.camera = Camera()

        # New systems
        self.drop_manager = DropManager()
        self.inventory = Inventory()

        # Breaking state
        self.breaking_tile = None  # (tile_x, tile_y)
        self.break_progress = 0.0  # 0.0 to 1.0
        self.break_time_required = 0.0  # seconds
        self.mouse_held = False

    def handle_events(self):
        """Handle pygame events."""
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Close inventory if open, otherwise quit
                    if self.inventory.is_open:
                        self.inventory.is_open = False
                        self.inventory.cancel_drag()
                    else:
                        self.running = False
                elif event.key == pygame.K_TAB:
                    # Toggle inventory
                    self.inventory.is_open = not self.inventory.is_open
                    self.inventory.cancel_drag()
                # Number keys 1-9 for inventory selection
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    self.inventory.select_slot(event.key - pygame.K_1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_held = True
                    # If inventory is open, handle inventory click
                    if self.inventory.is_open:
                        self.inventory.handle_click(*mouse_pos, 1)
                    else:
                        # Check hotbar click
                        hotbar_slot = self.inventory.check_hotbar_hover(*mouse_pos)
                        if hotbar_slot >= 0:
                            self.inventory.handle_click(*mouse_pos, 1)
                        else:
                            self._start_breaking(mouse_pos)
                elif event.button == 3:  # Right click - place block
                    if not self.inventory.is_open:
                        self._try_place_block(mouse_pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_held = False
                    # Only stop breaking if not in inventory
                    if not self.inventory.is_open:
                        self._stop_breaking()
            elif event.type == pygame.MOUSEWHEEL:
                # Mouse wheel for inventory selection
                # event.y is 1 for scroll up, -1 for scroll down
                self.inventory.scroll_selection(-event.y)

        # Update hover states for drops (world coordinates)
        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        self.drop_manager.check_hover(world_x, world_y)

    def _get_tile_at_mouse(self, mouse_pos):
        """Convert mouse position to tile coordinates (accounting for zoom)."""
        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)
        return tile_x, tile_y

    def _is_in_break_range(self, tile_x, tile_y):
        """Check if the tile is within break range of the player."""
        # Get player center in tile coordinates
        player_center_x = (self.player.x + self.player.width / 2) / TILE_SIZE
        player_center_y = (self.player.y + self.player.height / 2) / TILE_SIZE

        # Calculate distance
        dx = tile_x - player_center_x
        dy = tile_y - player_center_y
        distance = math.sqrt(dx * dx + dy * dy)

        return distance <= BREAK_RANGE

    def _start_breaking(self, mouse_pos):
        """Start breaking a block at mouse position."""
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Check if in range and breakable
        if not self._is_in_break_range(tile_x, tile_y):
            return

        block_type = self.world.get_block(tile_x, tile_y)
        if not is_block_breakable(block_type):
            return

        # Start breaking
        self.breaking_tile = (tile_x, tile_y)
        self.break_progress = 0.0
        self.break_time_required = get_break_time(block_type)

    def _stop_breaking(self):
        """Stop breaking (mouse released)."""
        self.breaking_tile = None
        self.break_progress = 0.0

    def _try_place_block(self, mouse_pos):
        """Try to place a block from inventory."""
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Check if in range
        if not self._is_in_break_range(tile_x, tile_y):
            return

        # Check if tile is empty
        if self.world.get_block(tile_x, tile_y) != 0:  # Not air
            return

        # Check if we have an item selected
        selected = self.inventory.get_selected_item()
        if selected is None:
            return

        block_type, count = selected

        # Check if block would intersect player
        block_rect = pygame.Rect(
            tile_x * TILE_SIZE,
            tile_y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        if block_rect.colliderect(self.player.rect):
            return

        # Place the block
        self.world.set_block(tile_x, tile_y, block_type)
        self.inventory.remove_item(self.inventory.selected_slot, 1)

    def update(self):
        """Update game state."""
        dt = 1.0 / FPS  # Time delta in seconds

        # Don't update player if inventory is open
        if not self.inventory.is_open:
            # Player movement
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys)
            self.player.update(self.world)
            self.camera.follow(self.player.rect)
            self.camera.update()

            # Handle breaking progress
            if self.mouse_held and self.breaking_tile is not None:
                tile_x, tile_y = self.breaking_tile

                # Check if still in range and still valid
                if self._is_in_break_range(tile_x, tile_y):
                    block_type = self.world.get_block(tile_x, tile_y)
                    if is_block_breakable(block_type):
                        # Progress breaking
                        self.break_progress += dt / self.break_time_required

                        if self.break_progress >= 1.0:
                            # Block broken!
                            self._break_block(tile_x, tile_y, block_type)
                            self.breaking_tile = None
                            self.break_progress = 0.0
                    else:
                        self._stop_breaking()
                else:
                    self._stop_breaking()

        # Update drops and check for collection
        collected_drops = self.drop_manager.update(dt, self.player.rect)
        for drop in collected_drops:
            if self.inventory.add_item(drop.block_type):
                self.drop_manager.remove_drop(drop)

    def _break_block(self, tile_x, tile_y, block_type):
        """Break a block and spawn a drop."""
        # Remove the block
        self.world.break_block(tile_x, tile_y)

        # Grass drops dirt instead of grass
        drop_type = block_type
        if block_type == BlockType.GRASS:
            drop_type = BlockType.DIRT

        # Spawn a drop
        self.drop_manager.spawn_drop(tile_x, tile_y, drop_type)

    def draw(self):
        """Draw everything."""
        # Clear screen with sky color
        self.screen.fill(SKY_BLUE)

        # Draw world
        self.world.draw(self.screen, self.camera)

        # Draw dropped items
        self.drop_manager.draw(self.screen, self.camera)

        # Draw player
        self.player.draw(self.screen, self.camera)

        # Draw breaking progress
        self._draw_breaking_progress()

        # Draw range indicator (only if inventory not open)
        if not self.inventory.is_open:
            self._draw_range_indicator()

        # Draw inventory
        self.inventory.draw(self.screen)

        # Draw inventory tooltip
        mouse_pos = pygame.mouse.get_pos()
        self.inventory.draw_tooltip(self.screen, *mouse_pos)

        # Draw dragged item
        self.inventory.draw_drag_item(self.screen, *mouse_pos)

        # Draw HUD / instructions
        self._draw_hud()

        pygame.display.flip()

    def _draw_breaking_progress(self):
        """Draw breaking progress bar on the block being broken."""
        if self.breaking_tile is None or self.break_progress <= 0:
            return

        tile_x, tile_y = self.breaking_tile

        # Calculate screen position with zoom
        world_x = tile_x * TILE_SIZE
        world_y = tile_y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        scaled_tile = TILE_SIZE * self.camera.zoom

        # Draw progress bar background
        bar_width = scaled_tile
        bar_height = 6
        bar_y = screen_y - bar_height - 2

        pygame.draw.rect(
            self.screen,
            (50, 50, 50),
            (int(screen_x), int(bar_y), int(bar_width), bar_height)
        )

        # Draw progress bar fill
        progress_width = int(bar_width * self.break_progress)
        pygame.draw.rect(
            self.screen,
            (0, 200, 0),
            (int(screen_x), int(bar_y), progress_width, bar_height)
        )

        # Draw border
        pygame.draw.rect(
            self.screen,
            WHITE,
            (int(screen_x), int(bar_y), int(bar_width), bar_height),
            1
        )

    def _draw_range_indicator(self):
        """Draw a subtle indicator showing break range."""
        mouse_pos = pygame.mouse.get_pos()
        tile_x, tile_y = self._get_tile_at_mouse(mouse_pos)

        # Draw highlight on hovered block if in range
        if self._is_in_break_range(tile_x, tile_y):
            block_type = self.world.get_block(tile_x, tile_y)
            if is_block_breakable(block_type):
                # Calculate screen position with zoom
                world_x = tile_x * TILE_SIZE
                world_y = tile_y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                scaled_tile = TILE_SIZE * self.camera.zoom

                # Draw yellow border to indicate breakable
                rect = pygame.Rect(int(screen_x), int(screen_y), int(scaled_tile), int(scaled_tile))
                pygame.draw.rect(self.screen, YELLOW, rect, 2)

                # Show break time
                break_time = get_break_time(block_type)
                font = pygame.font.SysFont(None, 18)
                text = font.render(f"{break_time:.1f}s", True, WHITE)
                self.screen.blit(text, (int(screen_x) + 2, int(screen_y) + 2))

    def _draw_hud(self):
        """Draw HUD elements (text, instructions)."""
        font = pygame.font.SysFont(None, 20)

        # Show title
        title = pygame.font.SysFont(None, 32).render("MyArea", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH - 100, 10))

        # Instructions at bottom
        if self.inventory.is_open:
            text = font.render("Tab: Close Inventory | Drag items to rearrange", True, WHITE)
        else:
            text = font.render(
                "WASD: Move | Space: Jump | L-Click: Break | R-Click: Place | Tab: Inventory | Scroll: Select",
                True, WHITE
            )
        self.screen.blit(text, (10, SCREEN_HEIGHT - 25))

        # Show current breaking info if breaking
        if self.breaking_tile is not None:
            tile_x, tile_y = self.breaking_tile
            block_type = self.world.get_block(tile_x, tile_y)
            name = get_block_name(block_type)
            info = font.render(f"Breaking: {name} ({self.break_progress * 100:.0f}%)", True, WHITE)
            self.screen.blit(info, (10, 60))

    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    """Entry point for python3 -m game.main."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
