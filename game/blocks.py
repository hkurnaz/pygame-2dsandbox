"""Block definitions and types for the game world."""

from game.constants import (
    GRASS_COLOR, DIRT_COLOR, WOOD_COLOR, LEAVES_COLOR, STONE_COLOR,
    BLACK
)


class BlockType:
    """Represents a type of block in the game."""
    AIR = 0
    GRASS = 1
    DIRT = 2
    WOOD = 3
    LEAVES = 4
    STONE = 5


# Block properties: (name, color, breakable, solid, break_time_seconds)
BLOCK_DATA = {
    BlockType.AIR: ("Air", BLACK, False, False, 0.0),
    BlockType.GRASS: ("Grass", GRASS_COLOR, True, True, 2.0),
    BlockType.DIRT: ("Dirt", DIRT_COLOR, True, True, 2.0),
    BlockType.WOOD: ("Wood", WOOD_COLOR, True, True, 3.0),
    BlockType.LEAVES: ("Leaves", LEAVES_COLOR, True, True, 1.0),
    BlockType.STONE: ("Stone", STONE_COLOR, True, True, 4.0),
}


def get_block_name(block_type):
    """Get the name of a block type."""
    return BLOCK_DATA.get(block_type, ("Unknown",))[0]


def get_block_color(block_type):
    """Get the color of a block type."""
    return BLOCK_DATA.get(block_type, ("", BLACK))[1]


def is_block_solid(block_type):
    """Check if a block is solid (can collide)."""
    return BLOCK_DATA.get(block_type, (None, None, None, True, 0))[3]


def is_block_breakable(block_type):
    """Check if a block can be broken."""
    return BLOCK_DATA.get(block_type, (None, None, True, None, 0))[2]


def is_block_air(block_type):
    """Check if block is air (empty)."""
    return block_type == BlockType.AIR


def get_break_time(block_type):
    """Get the time in seconds required to break a block with bare hands."""
    return BLOCK_DATA.get(block_type, (None, None, None, None, 1.0))[4]
