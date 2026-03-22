"""Game constants and configuration."""

# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# World settings
TILE_SIZE = 32
WORLD_WIDTH = 100  # tiles wide
WORLD_HEIGHT = 50  # tiles tall

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GREEN = (144, 238, 144)
DARK_GREEN = (0, 100, 0)
YELLOW = (255, 255, 0)
SKY_BLUE = (135, 206, 235)

# Block colors
GRASS_COLOR = (76, 153, 76)
DIRT_COLOR = (139, 69, 19)
WOOD_COLOR = (101, 67, 33)
LEAVES_COLOR = (34, 139, 34)
STONE_COLOR = (128, 128, 128)

# Player settings (2 blocks wide, 3 blocks tall)
PLAYER_WIDTH = 64   # 2 blocks
PLAYER_HEIGHT = 96  # 3 blocks
PLAYER_COLOR = (0, 100, 200)
PLAYER_SPEED = 5
PLAYER_JUMP_VELOCITY = -14
GRAVITY = 0.6
MAX_FALL_SPEED = 15

# Breaking settings
BREAK_RANGE = 5  # blocks

# Drop item settings
DROP_SIZE = 16  # smaller than full block (32)
DROP_COLLECT_RANGE = 50  # pixels
DROP_BOB_SPEED = 3  # bobbing animation speed
DROP_BOB_AMOUNT = 3  # pixels

# Inventory settings
INVENTORY_SLOTS = 9  # Hotbar slots
INVENTORY_COLS = 9   # Columns in big inventory
INVENTORY_ROWS = 3   # Rows in big inventory
INVENTORY_SLOT_SIZE = 40
INVENTORY_PADDING = 5

# Camera zoom (higher = more zoomed out)
CAMERA_ZOOM = 0.6  # 60% zoom makes everything smaller

# Camera
CAMERA_SMOOTH = 0.1

# World generation
GRASS_LAYER_DEPTH = 1
DIRT_LAYER_DEPTH = 8
TREE_CHANCE = 0.08  # 8% chance per column to have a tree
MIN_TREE_SPACING = 4  # minimum tiles between trees
