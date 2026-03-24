"""Game constants and configuration."""

# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# World settings
TILE_SIZE = 32
WORLD_WIDTH = 400  # tiles wide (4x bigger)
WORLD_HEIGHT = 200  # tiles tall (4x bigger)

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

# Tool colors
SWORD_COLOR = (180, 180, 200)
PICKAXE_COLOR = (100, 100, 120)
AXE_COLOR = (139, 90, 43)
SHOVEL_COLOR = (150, 150, 160)

# Player settings (1.5 blocks wide, 3 blocks tall)
PLAYER_WIDTH = 48   # 1.5 blocks
PLAYER_HEIGHT = 96  # 3 blocks
PLAYER_COLOR = (0, 100, 200)
PLAYER_SPEED = 5
PLAYER_JUMP_VELOCITY = -14
GRAVITY = 0.6
MAX_FALL_SPEED = 15

# Thrown item settings
THROW_FORCE = 8.0  # Initial throw velocity
THROW_UPWARD_ANGLE = -0.3  # Slight upward angle

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
TREE_CHANCE = 0.03  # 3% chance per column to have a tree (reduced count)
MIN_TREE_SPACING = 10  # minimum tiles between trees (more spread out)

# Day/Night cycle
DAY_DURATION = 300.0  # 5 minutes in seconds
NIGHT_SKY_COLOR = (25, 25, 50)  # Dark blue for night
DAY_SKY_COLOR = (135, 206, 235)  # Sky blue for day

# Sword settings
SWORD_SWING_DURATION = 0.3  # seconds
SWORD_SWING_RANGE = 80  # pixels
SWORD_DAMAGE = 1  # damage per hit

# Zombie settings
ZOMBIE_WIDTH = 48
ZOMBIE_HEIGHT = 72
ZOMBIE_SPEED = 1.5
ZOMBIE_HEALTH = 3
ZOMBIE_DAMAGE = 1
ZOMBIE_SPAWN_INTERVAL = 5.0  # seconds between spawn attempts
ZOMBIE_MAX_COUNT = 10  # max zombies at once
ZOMBIE_SPAWN_DISTANCE_MIN = 300  # minimum distance from player
ZOMBIE_SPAWN_DISTANCE_MAX = 500  # maximum distance from player

# Flying Eye settings (night enemy)
EYE_WIDTH = 48
EYE_HEIGHT = 48
EYE_SPEED = 2.5
EYE_HEALTH = 2
EYE_DAMAGE = 1
EYE_KNOCKBACK_FORCE = 6.0  # Knockback speed for the eye
EYE_PLAYER_DRAG_DISTANCE = 64  # 2 blocks (32 * 2)
EYE_SPAWN_INTERVAL = 8.0  # seconds between spawn attempts
EYE_MAX_COUNT = 5  # max flying eyes at once

# Platform settings
PLATFORM_THICKNESS = 8  # pixels (thin platform, 1/4 of tile)

# Lighting settings
LIGHT_RADIUS_DAY = 8  # blocks - fully visible area around player (day)
LIGHT_RADIUS_NIGHT = 6  # blocks - fully visible area around player (night, reduced)
LIGHT_FADE_DISTANCE = 12  # blocks - distance to complete darkness
UNDERGROUND_LIGHT_LIMIT = 5  # blocks - visibility limit below ground during day
