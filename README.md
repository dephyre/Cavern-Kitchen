# Cavern Kitchen

Descend into endless procedurally generated dungeons in this roguelike. Cook monster drops into meals to survive. Find weapons and armor that scale with depth. Hunt bounty bosses every 5 floors. Discover legendary gear with 5% drop rate. How deep can you go?

## Features

- **Endless Dungeon**: Procedurally generated floors that scale infinitely
- **Cook to Survive**: Turn monster drops into life-saving meals
- **Turn-Based Combat**: Attack enemies by walking into them
- **Equipment Scaling**: Weapons and armor grow stronger with depth
- **Legendary Loot**: 5% chance for powerful unique gear
- **Bounty Hunts**: Boss fights every 5 floors
- **Fog of War**: Limited visibility adds tension

## Requirements

- Python 3.7+
- pygame (for audio)

```bash
pip install pygame
```

## How to Play

Run the game:
```bash
python Cavern-Kitchen-v.01.py
```

Custom dungeon size:
```bash
python Cavern-Kitchen-v.01.py 50 25  # 50 wide, 25 tall
```

## Controls

| Key | Action |
|-----|--------|
| `w` | Move Up |
| `a` | Move Left |
| `s` | Move Down |
| `d` | Move Right |
| `c` | Cook |
| `q` | Quit |

## The Kitchen

What good is slaying monsters if you can't eat them? Combine ingredients to restore HP:

| Dish | Ingredients | HP |
|------|-------------|-----|
| Monster Meat Hand Pie | Monster Meat + Flour | 20 |
| Slime Onigiri | Slime Jelly + Cave Rice | 15 |
| Underworld Grits | Ground Cave Corn | 12 |
| Dungeon Apple Jam | Cave Apple | 10 |
| Suspicious Stew | Slime Jelly + any | 10 |
| Cave Skewer | Goblin Ear + Bat Wing | 8 |
| Cooked ingredient | Any single item | 2 |

## Enemies

| Enemy | Symbol | Base HP | Drop |
|-------|--------|---------|------|
| Goblin | `g` | 5 | Goblin Ear |
| Slime | `s` | 3 | Slime Jelly |
| Bat | `b` | 2 | Bat Wing |

Stats scale by 1.2x per floor. A Floor 15 Goblin has 77 HP!

## Equipment

### Weapons (magenta `W`)
| Name | Base ATK |
|------|----------|
| Rusted Sword | +2 |
| Iron Mace | +4 |
| Steel Blade | +6 |
| Battle Axe | +8 |

### Armor (blue `A`)
| Name | Base DEF |
|------|----------|
| Leather Tunic | +1 |
| Chainmail | +3 |
| Iron Plate | +5 |
| Dragon Scale | +7 |

### Legendary Items (5% chance)
5% of equipment is Legendary with 2x stats and unique names like:
- Heavy Cast-Iron Skillet
- Apothecary's Pestle
- Grandma's Rolling Pin of Justice
- The Thicc Sweater
- Armor of the Procrastinator

## Bounties

Every 5 floors, face a Bounty Target:
- 5x HP, 2x damage for that floor
- Reward: 500 × floor level in score
- Guaranteed item drop
- Message: *"Bounty collected. See you, space crawler..."*

## Other Items

| Symbol | Item |
|--------|------|
| `r` | Cave Rice |
| `a` | Cave Apple |
| `f` | Flour |
| `c` | Ground Cave Corn |
| `T` | Treasure (+100 score) |
| `^` | Trap (-2 HP) |
| `U` | Stairs Up (entrance) |
| `X` | Stairs Down (exit, +5 HP) |

## Building

### Linux
```bash
./build_linux.sh
```

### Windows
Run `build_windows.bat` on Windows to create `DungeonCrawler.exe`.

### Output
Executable and audio files are in `dist/windows/`.

## Audio Files (Optional)

Place these in the game directory:
- `bgm.mp3` - Background music
- `hit.wav` - Attack sound
- `pickup.wav` - Item pickup
- `cook.wav` - Cooking sound
- `exit.wav` - Level transition

Game runs without audio files.

## Tips

1. **Cook often** - Ingredients are plentiful, HP is precious
2. **Gear scales** - Upgrade when deeper floors give better stats
3. **Watch for Legendaries** - 2x stats are worth seeking
4. **Prep for Bounties** - Heal up before floors 5, 10, 15...
5. **Defense matters** - High DEF can block all damage

## File Structure

```
dungeon/
├── Cavern-Kitchen-v.01.py
├── dungeon_generator.py
├── build_linux.sh
├── build_windows.bat
├── bgm.mp3
├── hit.wav
├── pickup.wav
├── cook.wav
├── exit.wav
└── dist/windows/DungeonCrawler
```

## Credits

Built with Python, pygame for audio, and terminal interface using `termios` and `tty`.

---

**Descend. Cook. Survive.**

*How deep can you go?*
