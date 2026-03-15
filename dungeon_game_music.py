#!/usr/bin/env python3
"""
Cavern Kitchen - A procedurally generated roguelike dungeon crawler
with cooking, equipment, bounty hunting, and procedural music.

Controls:
    w - Move Up
    a - Move Left
    s - Move Down
    d - Move Right
    c - Cook
    q - Quit

Usage:
    python dungeon_game_music.py [width] [height]

Defaults to 30x15 if no arguments provided.
"""

import os
import random
import sys
import termios
import threading
import time
import tty

import numpy as np
import pygame

from dungeon_generator import Dungeon

# ============================================================================
# PROCEDURAL MUSIC GENERATOR
# ============================================================================


class ProceduralMusicGenerator:
    """Generates procedural ambient music for dungeon exploration."""

    # Musical scales (frequencies in Hz)
    SCALES = {
        "minor": [261.63, 293.66, 311.13, 349.23, 392.00, 415.30, 466.16, 523.25],
        "dorian": [261.63, 293.66, 311.13, 349.23, 392.00, 440.00, 466.16, 523.25],
        "phrygian": [261.63, 277.18, 311.13, 349.23, 392.00, 440.00, 466.16, 523.25],
        "locrian": [261.63, 277.18, 293.66, 311.13, 392.00, 440.00, 415.30, 466.16],
    }

    # Base frequencies for drone
    DRONE_FREQUENCIES = {"low": 55.0, "mid": 110.0, "high": 220.0}

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.current_scale = "minor"
        self.intensity = 0.5
        self.is_combat = False
        self.is_boss = False
        self.playing = False

    def generate_drone(
        self, frequency, duration, volume=0.3, lfo_rate=0.5, lfo_depth=0.1
    ):
        """Generate an ambient drone with subtle LFO modulation."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        lfo = np.sin(2 * np.pi * lfo_rate * t) * lfo_depth
        drone = np.sin(2 * np.pi * frequency * t + lfo)
        drone += 0.5 * np.sin(2 * np.pi * frequency * 2 * t + lfo * 0.5)
        drone += 0.25 * np.sin(2 * np.pi * frequency * 3 * t + lfo * 0.25)
        drone = drone / np.max(np.abs(drone)) * volume
        return drone

    def generate_pad(self, base_freq, duration, volume=0.2):
        """Generate a warm pad sound with multiple detuned oscillators."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        pad = np.zeros_like(t)
        detune_amount = 0.01
        for detune in [-detune_amount, 0, detune_amount]:
            freq = base_freq * (1 + detune)
            pad += np.sin(2 * np.pi * freq * t)
            pad += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
            pad += 0.25 * np.sin(2 * np.pi * freq * 3 * t)
        fade_samples = int(self.sample_rate * 0.5)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        pad[:fade_samples] *= fade_in
        pad[-fade_samples:] *= fade_out
        return pad / np.max(np.abs(pad)) * volume

    def generate_melody_note(
        self, note_freq, duration, volume=0.15, attack=0.1, release=0.3
    ):
        """Generate a single melody note with envelope."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        vibrato = np.sin(2 * np.pi * 5 * t) * 0.01
        note = np.sin(2 * np.pi * note_freq * t + vibrato)
        note += 0.3 * np.sin(2 * np.pi * note_freq * 2 * t)
        attack_samples = int(self.sample_rate * attack)
        release_samples = int(self.sample_rate * release)
        sustain_samples = len(note) - attack_samples - release_samples
        if sustain_samples > 0:
            envelope = np.concatenate(
                [
                    np.linspace(0, 1, attack_samples),
                    np.ones(sustain_samples) * 0.7,
                    np.linspace(0.7, 0, release_samples),
                ]
            )
        else:
            envelope = np.linspace(1, 0, len(note))
        if len(envelope) < len(note):
            envelope = np.concatenate([envelope, np.zeros(len(note) - len(envelope))])
        elif len(envelope) > len(note):
            envelope = envelope[: len(note)]
        return note * envelope * volume

    def generate_percussion(self, duration=0.1, volume=0.3):
        """Generate a short percussion hit."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        noise = np.random.uniform(-1, 1, len(t))
        decay = np.exp(-t * 30)
        perc = noise * decay
        perc = np.convolve(perc, np.ones(10) / 10, mode="same")
        return perc * volume

    def create_ambient_loop(self, duration=10.0):
        """Create a complete ambient music loop."""
        samples = int(self.sample_rate * duration)
        ambient = np.zeros(samples)
        drone_low = self.generate_drone(
            self.DRONE_FREQUENCIES["low"], duration, volume=0.15, lfo_rate=0.1
        )
        ambient += drone_low
        pad = self.generate_pad(self.DRONE_FREQUENCIES["mid"] * 2, duration, volume=0.1)
        ambient += pad
        if self.intensity > 0.3:
            high_drone = self.generate_drone(
                self.DRONE_FREQUENCIES["high"], duration, volume=0.05, lfo_rate=0.2
            )
            ambient += high_drone
        return ambient

    def add_melody_layer(self, ambient_buffer, duration=10.0):
        """Add random melody notes to the ambient buffer."""
        scale = self.SCALES[self.current_scale]
        notes_per_loop = int(3 + self.intensity * 5)
        for _ in range(notes_per_loop):
            note_idx = random.randint(0, len(scale) - 1)
            note_freq = scale[note_idx]
            octave = random.choice([0.5, 0.5, 1.0, 1.0, 1.0])
            note_freq *= octave
            start_time = random.uniform(0, duration - 2)
            note_duration = random.uniform(0.5, 1.5)
            note = self.generate_melody_note(
                note_freq, note_duration, volume=0.08 + self.intensity * 0.05
            )
            start_sample = int(start_time * self.sample_rate)
            end_sample = min(start_sample + len(note), len(ambient_buffer))
            actual_length = end_sample - start_sample
            if actual_length > 0:
                ambient_buffer[start_sample:end_sample] += note[:actual_length]

    def add_percussion_layer(self, ambient_buffer, duration=10.0):
        """Add subtle percussion based on intensity."""
        if self.intensity < 0.4:
            return
        hits_per_loop = int(self.intensity * 8)
        for _ in range(hits_per_loop):
            start_time = random.uniform(0, duration - 0.2)
            perc = self.generate_percussion(
                duration=0.1, volume=0.1 + self.intensity * 0.1
            )
            start_sample = int(start_time * self.sample_rate)
            end_sample = min(start_sample + len(perc), len(ambient_buffer))
            actual_length = end_sample - start_sample
            if actual_length > 0:
                ambient_buffer[start_sample:end_sample] += perc[:actual_length]

    def generate_music_segment(self, duration=10.0):
        """Generate a complete music segment."""
        segment = self.create_ambient_loop(duration)
        self.add_melody_layer(segment, duration)
        self.add_percussion_layer(segment, duration)
        max_val = np.max(np.abs(segment))
        if max_val > 0:
            segment = segment / max_val * 0.8
        return segment

    def numpy_to_pygame_sound(self, audio_data):
        """Convert numpy array to pygame Sound object."""
        audio_16bit = np.int16(audio_data * 32767)
        audio_stereo = np.column_stack((audio_16bit, audio_16bit))
        sound = pygame.sndarray.make_sound(audio_stereo)
        return sound

    def play_ambient_loop(self):
        """Generate and play ambient music in a loop."""
        while self.playing:
            segment = self.generate_music_segment(duration=10.0)
            sound = self.numpy_to_pygame_sound(segment)
            channel = pygame.mixer.Channel(0)
            channel.play(sound)
            time.sleep(9.5)

    def start(self):
        """Start the procedural music."""
        if not self.playing:
            # Randomly select a scale at start
            scales = list(self.SCALES.keys())
            self.current_scale = random.choice(scales)
            self.intensity = 0.3  # Start calm
            self.playing = True
            self.music_thread = threading.Thread(
                target=self.play_ambient_loop, daemon=True
            )
            self.music_thread.start()

    def stop(self):
        """Stop the procedural music."""
        self.playing = False
        pygame.mixer.stop()

    def set_intensity(self, intensity):
        """Set music intensity (0.0 = calm, 1.0 = intense)."""
        self.intensity = max(0.0, min(1.0, intensity))

    def set_combat_mode(self, is_combat):
        """Enable or disable combat music mode."""
        self.is_combat = is_combat
        if is_combat:
            self.intensity = min(1.0, self.intensity + 0.3)
        else:
            self.intensity = max(0.0, self.intensity - 0.3)

    def set_boss_mode(self, is_boss):
        """Enable or disable boss fight music mode."""
        self.is_boss = is_boss
        if is_boss:
            self.intensity = 1.0
            self.current_scale = "locrian"
        else:
            self.current_scale = "minor"

    def change_scale(self, scale_name):
        """Change the musical scale being used."""
        if scale_name in self.SCALES:
            self.current_scale = scale_name


class SoundEffectGenerator:
    """Generate procedural sound effects."""

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def generate_hit_sound(self):
        """Generate a hit/attack sound."""
        duration = 0.15
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        hit = np.sin(2 * np.pi * 150 * t)
        hit += np.sin(2 * np.pi * 200 * t)
        hit += np.random.uniform(-0.5, 0.5, len(t))
        decay = np.exp(-t * 20)
        hit *= decay * 0.4
        return hit

    def generate_pickup_sound(self):
        """Generate a pickup/item collection sound."""
        duration = 0.3
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        freq1, freq2, freq3 = 440, 554, 659
        pickup = np.zeros_like(t)
        pickup += np.sin(2 * np.pi * freq1 * t) * (t < 0.1)
        pickup += np.sin(2 * np.pi * freq2 * t) * ((t >= 0.1) & (t < 0.2)) * 0.8
        pickup += np.sin(2 * np.pi * freq3 * t) * ((t >= 0.2) & (t < 0.3)) * 0.6
        decay = np.exp(-t * 5)
        pickup *= decay * 0.3
        return pickup

    def generate_cook_sound(self):
        """Generate a cooking sound (sizzle)."""
        duration = 0.5
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sizzle = np.random.uniform(-1, 1, len(t))
        sizzle = np.convolve(sizzle, np.sin(2 * np.pi * 1000 * t[:100]), mode="same")
        decay = np.exp(-t * 4)
        sizzle *= decay * 0.08  # Lowered from 0.2 to 0.08
        return sizzle

    def generate_exit_sound(self):
        """Generate a level exit/transition sound."""
        duration = 1.0
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        freq_start, freq_end = 200, 800
        freq = freq_start + (freq_end - freq_start) * t
        exit_sound = np.sin(2 * np.pi * freq * t)
        exit_sound += 0.5 * np.sin(2 * np.pi * freq * 0.5 * t)
        exit_sound += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        envelope = np.sin(np.pi * t / duration)
        exit_sound *= envelope * 0.3
        return exit_sound

    def generate_hurt_sound(self):
        """Generate a sound for when player takes damage."""
        duration = 0.3
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)

        # Low thud + harsh noise
        hurt = np.sin(2 * np.pi * 80 * t)  # Low bass thud
        hurt += 0.5 * np.sin(2 * np.pi * 150 * t)  # Mid punch
        hurt += 0.3 * np.random.uniform(-1, 1, len(t))  # Harsh noise

        # Quick attack and decay
        envelope = np.exp(-t * 15)
        hurt *= envelope * 0.35

        return hurt

    def generate_footstep_sound(self):
        """Generate a subtle footstep sound."""
        duration = 0.08
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)

        # Soft thud
        footstep = np.sin(2 * np.pi * 100 * t)
        footstep += 0.5 * np.sin(2 * np.pi * 200 * t)

        # Quick decay
        decay = np.exp(-t * 40)
        footstep *= decay * 0.15

        return footstep

    def get_sound(self, sound_type):
        """Get a generated sound by type."""
        if sound_type == "hit":
            return self.generate_hit_sound()
        elif sound_type == "pickup":
            return self.generate_pickup_sound()
        elif sound_type == "cook":
            return self.generate_cook_sound()
        elif sound_type == "exit":
            return self.generate_exit_sound()
        elif sound_type == "hurt":
            return self.generate_hurt_sound()
        elif sound_type == "footstep":
            return self.generate_footstep_sound()
        return None


# ============================================================================
# GAME CLASSES
# ============================================================================


class Player:
    """Represents the player character in the game."""

    MAX_HP = 50  # Health cap to prevent infinite scaling

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.health = 10
        self.max_health = 10
        self.score = 0
        self.inventory = []
        # Equipment stats
        self.base_attack = 1
        self.base_defense = 0
        self.weapon_attack = 0
        self.armor_defense = 0
        self.weapon_name = "None"
        self.armor_name = "None"
        # Status effects
        self.poison_turns = 0
        self.slow_turns = 0
        self.stun_turns = 0
        self.crit_chance = 0.05  # 5% base crit chance
        self.dodge_chance = 0.0  # Base dodge chance (from armor)

    def add_health(self, amount: int):
        """Add health with cap."""
        self.health = min(self.health + amount, self.MAX_HP)

    def apply_status(self, effect: str, duration: int):
        """Apply a status effect."""
        if effect == "poison":
            self.poison_turns = max(self.poison_turns, duration)
        elif effect == "slow":
            self.slow_turns = max(self.slow_turns, duration)
        elif effect == "stun":
            self.stun_turns = max(self.stun_turns, duration)

    def tick_status_effects(self):
        """Process status effects at end of turn. Returns damage taken."""
        damage = 0
        if self.poison_turns > 0:
            damage += 1
            self.poison_turns -= 1
        if self.slow_turns > 0:
            self.slow_turns -= 1
        if self.stun_turns > 0:
            self.stun_turns -= 1
        return damage

    def is_slowed(self):
        return self.slow_turns > 0

    def is_stunned(self):
        return self.stun_turns > 0

    def move(self, dx: int, dy: int, dungeon: Dungeon) -> bool:
        new_x = self.x + dx
        new_y = self.y + dy
        if dungeon.is_walkable(new_x, new_y):
            self.x = new_x
            self.y = new_y
            return True
        return False


class Enemy:
    """Represents an enemy in the game with behavior patterns."""

    def __init__(self, x: int, y: int, enemy_type: dict, is_bounty: bool = False):
        self.x = x
        self.y = y
        self.name = enemy_type["name"]
        self.symbol = enemy_type["symbol"]
        self.max_hp = enemy_type["hp"]
        self.hp = enemy_type["hp"]
        self.damage = enemy_type["damage"]
        self.drop_item = enemy_type["drop"]
        self.is_bounty = is_bounty
        self.pattern = enemy_type.get("pattern", "normal")
        self.attack_cooldown = 0  # For attack patterns
        self.stun_turns = 0  # Stun effect duration

    def can_attack(self):
        """Check if enemy can attack this turn based on pattern."""
        if self.stun_turns > 0:
            self.stun_turns -= 1
            return False

        if self.pattern == "slow":
            # Slow enemies attack every other turn
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
                return False
            self.attack_cooldown = 1
            return True
        elif self.pattern == "erratic":
            # Erratic enemies have 50% chance to attack
            import random

            return random.random() < 0.5
        elif self.pattern == "heavy":
            # Heavy enemies attack every 2 turns
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
                return False
            self.attack_cooldown = 2
            return True
        elif self.pattern == "elite":
            # Elite enemies always attack with bonus damage
            return True
        else:
            # Normal pattern - always attack
            return True

    def get_damage(self):
        """Get damage based on pattern."""
        base_damage = self.damage
        if self.pattern == "elite":
            # Elite enemies deal bonus damage
            return base_damage + 2
        return base_damage

    def move_towards_player(self, player, dungeon, enemies):
        """Move one tile closer to the player if within range."""
        import random

        # Different movement behaviors based on enemy type
        if self.pattern == "erratic":
            # Erratic - random movement
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
        elif self.pattern == "slow":
            # Slow - move every other turn
            if random.random() < 0.5:
                return False
            dx = 0
            dy = 0
            if player.x > self.x:
                dx = 1
            elif player.x < self.x:
                dx = -1
            if player.y > self.y:
                dy = 1
            elif player.y < self.y:
                dy = -1
        elif self.pattern == "ranged":
            # Ranged - keep distance from player
            dist = abs(player.x - self.x) + abs(player.y - self.y)
            if dist < 3:
                # Move away from player
                dx = -1 if player.x > self.x else (1 if player.x < self.x else 0)
                dy = -1 if player.y > self.y else (1 if player.y < self.y else 0)
            else:
                dx = 0
                dy = 0
        elif self.pattern == "spellcaster":
            # Spellcaster - stay still and cast
            dx = 0
            dy = 0
        elif self.pattern == "heavy":
            # Heavy - slow but direct
            dx = 0
            dy = 0
            if player.x > self.x:
                dx = 1
            elif player.x < self.x:
                dx = -1
            if player.y > self.y:
                dy = 1
            elif player.y < self.y:
                dy = -1
        else:
            # Normal - direct pursuit
            dx = 0
            dy = 0
            if player.x > self.x:
                dx = 1
            elif player.x < self.x:
                dx = -1
            if player.y > self.y:
                dy = 1
            elif player.y < self.y:
                dy = -1

        new_x = self.x + dx
        new_y = self.y + dy

        if dungeon.is_walkable(new_x, new_y):
            for enemy in enemies:
                if enemy is not self and enemy.x == new_x and enemy.y == new_y:
                    return False
            self.x = new_x
            self.y = new_y
            return True
        return False


# Enemy type definitions - Basic enemies
ENEMY_TYPES = [
    {
        "name": "Goblin",
        "symbol": "g",
        "hp": 5,
        "damage": 1,
        "drop": "Goblin Ear",
        "pattern": "normal",
    },
    {
        "name": "Slime",
        "symbol": "s",
        "hp": 3,
        "damage": 1,
        "drop": "Slime Jelly",
        "pattern": "slow",
    },
    {
        "name": "Bat",
        "symbol": "b",
        "hp": 2,
        "damage": 1,
        "drop": "Bat Wing",
        "pattern": "erratic",
    },
]

# Advanced enemy types - appear after floor 5
ADVANCED_ENEMY_TYPES = [
    {
        "name": "Archer",
        "symbol": "A",
        "hp": 4,
        "damage": 3,
        "drop": "Arrow",
        "pattern": "ranged",
    },
    {
        "name": "Mage",
        "symbol": "M",
        "hp": 3,
        "damage": 4,
        "drop": "Spell Scroll",
        "pattern": "spellcaster",
    },
    {
        "name": "Brute",
        "symbol": "B",
        "hp": 12,
        "damage": 3,
        "drop": "Brute Hide",
        "pattern": "heavy",
    },
    {
        "name": "Swarm",
        "symbol": "S",
        "hp": 2,
        "damage": 1,
        "drop": "Swarm Goo",
        "pattern": "swarm",
    },
]

# Elite enemy types - appear after floor 10
ELITE_ENEMY_TYPES = [
    {
        "name": "Elite Goblin",
        "symbol": "G",
        "hp": 15,
        "damage": 3,
        "drop": "Goblin King Crown",
        "pattern": "elite",
    },
    {
        "name": "Elite Slime",
        "symbol": "S",
        "hp": 10,
        "damage": 3,
        "drop": "Slime Core",
        "pattern": "elite",
    },
    {
        "name": "Elite Bat",
        "symbol": "B",
        "hp": 8,
        "damage": 2,
        "drop": "Bat Fang",
        "pattern": "elite",
    },
]

# Floor item definitions
FLOOR_ITEMS = [
    {"name": "Cave Rice", "symbol": "r"},
    {"name": "Cave Apple", "symbol": "a"},
    {"name": "Flour", "symbol": "f"},
    {"name": "Ground Cave Corn", "symbol": "c"},
]

# Health potion - rare healing item
HEALTH_POTION = {"name": "Health Potion", "symbol": "H", "heal": 20}

# Curse items - negative effects
CURSE_ITEMS = [
    {"name": "Poison Vial", "symbol": "P", "effect": "poison", "duration": 5},
    {"name": "Weakness Curse", "symbol": "W", "effect": "weakness", "duration": 10},
    {"name": "Slow Trap", "symbol": "S", "effect": "slow", "duration": 8},
]

# Curse definitions - negative effects
CURSES = [
    {"name": "Poison", "symbol": "P", "effect": "poison", "duration": 5},
    {"name": "Weakness", "symbol": "W", "effect": "weakness", "duration": 10},
    {"name": "Slow", "symbol": "S", "effect": "slow", "duration": 8},
]

# Weapon definitions - diminishing returns after floor 10
WEAPONS = [
    {"name": "Rusted Sword", "attack": 2},
    {"name": "Iron Mace", "attack": 4},
    {"name": "Steel Blade", "attack": 6},
    {"name": "Battle Axe", "attack": 8},
    {"name": "Warhammer", "attack": 10},
    {"name": "Greatsword", "attack": 12},
]

# Armor definitions - diminishing returns after floor 10
ARMOR = [
    {"name": "Leather Tunic", "defense": 1},
    {"name": "Chainmail", "defense": 3},
    {"name": "Iron Plate", "defense": 5},
    {"name": "Dragon Scale", "defense": 7},
    {"name": "Titan Mail", "defense": 9},
    {"name": "Void Armor", "defense": 11},
]

# Legendary weapon definitions - with special effects
LEGENDARY_WEAPONS = [
    {"name": "Heavy Cast-Iron Skillet", "attack": 2, "effect": "cooking_bonus"},
    {"name": "Apothecary's Pestle", "attack": 2, "effect": "poison"},
    {"name": "Vorpal Spatula of Doom", "attack": 2, "effect": "critical"},
    {"name": "The Annoyingly Sharp Spoon", "attack": 2, "effect": "none"},
    {"name": "Grandma's Rolling Pin of Justice", "attack": 2, "effect": "stun"},
    {"name": "Slightly Cursed Fork", "attack": 2, "effect": "lifesteal"},
    {"name": "Blade of the Late Breakfast", "attack": 2, "effect": "none"},
    {"name": "Excalibur's Lesser Cousin", "attack": 2, "effect": "none"},
]

# Legendary armor definitions - with special effects
LEGENDARY_ARMOR = [
    {"name": "Reinforced Turntable", "defense": 2, "effect": "dodge"},
    {"name": "Cloak of Inconvenience", "defense": 2, "effect": "none"},
    {"name": "The Indestructible Poncho", "defense": 2, "effect": "none"},
    {"name": "Vest of the Eternal Monday", "defense": 2, "effect": "none"},
    {"name": "Plate of Leftovers", "defense": 2, "effect": "none"},
    {"name": "The Thicc Sweater", "defense": 2, "effect": "warmth"},
    {"name": "Robes of Mild Discomfort", "defense": 2, "effect": "none"},
    {"name": "Armor of the Procrastinator", "defense": 2, "effect": "none"},
]

# Bounty target names
BOUNTY_NAMES = [
    "The Infamous Slime Syndicate",
    "Vicious Cave Bat",
    "Grumbles the Grouchy Goblin",
    "Sir Squeaks-a-Lot",
    "The Dread Pirate Roberts",
    "Baron Von Bites-a-Lot",
    "The Crimson Creep",
    "Whispers the Wicked",
    "Gnarls the Gnasty",
    "The Shadow That Stole Lunch",
    "Barnaby the Brutal",
    "The Gelatinous Menace",
    "Crusher the Cookie Thief",
    "The Phantom Menace Jr.",
    "Scales of Doom",
    "The Underground Overlord",
    "Fangs McGee",
    "The Boulder That Broke Your Heart",
    "Captain Crumble",
    "The Eternal Echo",
]


class Game:
    """Main game class handling the game loop and rendering."""

    PLAYER = "@"

    def __init__(self, width: int = 30, height: int = 15):
        self.width = width
        self.height = height
        self.dungeon = None
        self.player = None
        self.enemies = []
        self.floor_items = []
        self.weapons = []
        self.armors = []
        self.running = True
        self.visited = set()
        self.visibility_radius = 5
        self.messages = []
        self.dungeon_level = 1
        self.is_bounty_level = False
        self._flash_message = None

        # Procedural audio
        self.music_gen = None
        self.sfx_gen = None
        self.audio_initialized = False

    # Health bar colors
    HP_FULL = "\033[92m"  # Green
    HP_HIGH = "\033[93m"  # Yellow
    HP_LOW = "\033[91m"  # Red
    HP_CRITICAL = "\033[95m"  # Magenta

    def init_audio(self):
        """Initialize procedural audio system."""
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.music_gen = ProceduralMusicGenerator(sample_rate=44100)
            self.sfx_gen = SoundEffectGenerator(sample_rate=44100)
            self.audio_initialized = True
            self.music_gen.start()
        except Exception as e:
            print(f"Warning: Could not initialize audio: {e}")
            self.audio_initialized = False

    def play_sfx(self, sound_type: str):
        """Play a procedural sound effect."""
        if not self.audio_initialized or not self.sfx_gen:
            return
        try:
            audio = self.sfx_gen.get_sound(sound_type)
            if audio is not None:
                sound = self.music_gen.numpy_to_pygame_sound(audio)
                pygame.mixer.Channel(1).play(sound)
        except Exception:
            pass

    def _ensure_enemy_exists(self):
        """Ensure at least one enemy exists in the dungeon."""
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.grid[y][x] == Dungeon.ENEMY:
                    return
        floor_tiles = []
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.grid[y][x] == Dungeon.FLOOR:
                    if not (self.player and x == self.player.x and y == self.player.y):
                        floor_tiles.append((x, y))
        if floor_tiles:
            x, y = random.choice(floor_tiles)
            self.dungeon.grid[y][x] = Dungeon.ENEMY

    def generate_new_dungeon(self):
        """Generate a new dungeon and spawn the player."""
        old_score = self.player.score if self.player else 0
        old_health = self.player.health if self.player else 10
        old_inventory = self.player.inventory.copy() if self.player else []
        old_level = self.dungeon_level if self.player else 1
        old_weapon_attack = self.player.weapon_attack if self.player else 0
        old_weapon_name = self.player.weapon_name if self.player else "None"
        old_armor_defense = self.player.armor_defense if self.player else 0
        old_armor_name = self.player.armor_name if self.player else "None"

        self.dungeon = Dungeon(self.width, self.height)
        self.dungeon.generate()

        if self.dungeon.entrance_pos:
            self.player = Player(
                self.dungeon.entrance_pos[0], self.dungeon.entrance_pos[1]
            )
        else:
            if self.dungeon.rooms:
                room = self.dungeon.rooms[0]
                self.player = Player(
                    room.x + room.width // 2, room.y + room.height // 2
                )
            else:
                self.player = Player(self.width // 2, self.height // 2)

        self.player.score = old_score
        self.player.health = old_health
        self.player.inventory = old_inventory
        self.dungeon_level = old_level
        self.player.weapon_attack = old_weapon_attack
        self.player.weapon_name = old_weapon_name
        self.player.armor_defense = old_armor_defense
        self.player.armor_name = old_armor_name

        self._ensure_enemy_exists()
        self.visited = set()
        self._init_enemies()
        self._spawn_floor_items()
        self._spawn_health_potions()
        self._spawn_curses()
        self._spawn_equipment()
        self._update_visited()

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def _init_enemies(self):
        """Initialize enemy objects from dungeon grid."""
        self.enemies = []
        scale = 1.2 ** (self.dungeon_level - 1)
        self.is_bounty_level = self.dungeon_level % 5 == 0

        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.grid[y][x] == Dungeon.ENEMY:
                    if self.is_bounty_level:
                        bounty_name = random.choice(BOUNTY_NAMES)
                        base_hp = max(1, int(5 * scale))
                        base_damage = max(1, int(2 * scale))
                        self.enemies.append(
                            Enemy(
                                x,
                                y,
                                {
                                    "name": bounty_name,
                                    "symbol": "B",
                                    "hp": base_hp,
                                    "damage": base_damage,
                                    "drop": "Bounty Reward",
                                    "pattern": "elite",
                                },
                                is_bounty=True,
                            )
                        )
                    else:
                        # Choose enemy pool based on floor
                        if self.dungeon_level < 5:
                            enemy_pool = ENEMY_TYPES
                        elif self.dungeon_level < 10:
                            # Mix of basic and advanced
                            enemy_pool = ENEMY_TYPES + ADVANCED_ENEMY_TYPES
                        else:
                            # Mix of all types including elites
                            enemy_pool = (
                                ENEMY_TYPES + ADVANCED_ENEMY_TYPES + ELITE_ENEMY_TYPES
                            )

                        enemy_type = random.choice(enemy_pool)
                        scaled_hp = max(1, int(enemy_type["hp"] * scale))
                        scaled_damage = max(1, int(enemy_type["damage"] * scale))
                        self.enemies.append(
                            Enemy(
                                x,
                                y,
                                {
                                    "name": enemy_type["name"],
                                    "symbol": enemy_type["symbol"],
                                    "hp": scaled_hp,
                                    "damage": scaled_damage,
                                    "drop": enemy_type["drop"],
                                    "pattern": enemy_type.get("pattern", "normal"),
                                },
                            )
                        )
                    self.dungeon.grid[y][x] = Dungeon.FLOOR

    def _spawn_floor_items(self):
        """Spawn random floor items on the dungeon."""
        self.floor_items = []
        num_items = random.randint(2, 4)
        available_tiles = []
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.grid[y][x] == Dungeon.FLOOR:
                    if self.player and x == self.player.x and y == self.player.y:
                        continue
                    if any(e.x == x and e.y == y for e in self.enemies):
                        continue
                    available_tiles.append((x, y))
        for _ in range(min(num_items, len(available_tiles))):
            x, y = random.choice(available_tiles)
            available_tiles.remove((x, y))
            item = random.choice(FLOOR_ITEMS)
            self.floor_items.append((x, y, item["name"], item["symbol"]))

    def _spawn_health_potions(self):
        """Spawn health potions (rare)."""
        import random

        # 5% chance per floor
        if random.random() < 0.05:
            available_tiles = []
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    if self.dungeon.grid[y][x] == Dungeon.FLOOR:
                        if self.player and x == self.player.x and y == self.player.y:
                            continue
                        if any(e.x == x and e.y == y for e in self.enemies):
                            continue
                        if any(fi[0] == x and fi[1] == y for fi in self.floor_items):
                            continue
                        available_tiles.append((x, y))

            if available_tiles:
                x, y = random.choice(available_tiles)
                self.floor_items.append(
                    (x, y, HEALTH_POTION["name"], HEALTH_POTION["symbol"])
                )

    def _spawn_curses(self):
        """Spawn curse items on higher floors."""
        import random

        # 2% chance on floor 5-9, 5% on floor 10+
        curse_chance = 0.02 if self.dungeon_level < 10 else 0.05
        if random.random() < curse_chance:
            available_tiles = []
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    if self.dungeon.grid[y][x] == Dungeon.FLOOR:
                        if self.player and x == self.player.x and y == self.player.y:
                            continue
                        if any(e.x == x and e.y == y for e in self.enemies):
                            continue
                        if any(fi[0] == x and fi[1] == y for fi in self.floor_items):
                            continue
                        available_tiles.append((x, y))

            if available_tiles:
                x, y = random.choice(available_tiles)
                curse = random.choice(CURSE_ITEMS)
                self.floor_items.append((x, y, curse["name"], curse["symbol"]))

    def _spawn_equipment(self):
        """Spawn random weapons and armor on the dungeon."""
        self.weapons = []
        self.armors = []
        num_weapons = random.randint(0, 2)
        num_armors = random.randint(0, 2)
        scale = 1.2 ** (self.dungeon_level - 1)
        available_tiles = []
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.grid[y][x] == Dungeon.FLOOR:
                    if self.player and x == self.player.x and y == self.player.y:
                        continue
                    if any(e.x == x and e.y == y for e in self.enemies):
                        continue
                    if any(fi[0] == x and fi[1] == y for fi in self.floor_items):
                        continue
                    available_tiles.append((x, y))
        for _ in range(min(num_weapons, len(available_tiles))):
            x, y = random.choice(available_tiles)
            available_tiles.remove((x, y))
            if random.random() < 0.05:
                weapon = random.choice(LEGENDARY_WEAPONS)
                scaled_attack = max(1, int(weapon["attack"] * scale * 2))
                legendary_name = f"[LEGENDARY] {weapon['name']}"
                self.weapons.append((x, y, legendary_name, scaled_attack))
            else:
                weapon = random.choice(WEAPONS)
                scaled_attack = max(1, int(weapon["attack"] * scale))
                self.weapons.append((x, y, weapon["name"], scaled_attack))
        for _ in range(min(num_armors, len(available_tiles))):
            x, y = random.choice(available_tiles)
            available_tiles.remove((x, y))
            if random.random() < 0.05:
                armor = random.choice(LEGENDARY_ARMOR)
                scaled_defense = max(1, int(armor["defense"] * scale * 2))
                legendary_name = f"[LEGENDARY] {armor['name']}"
                self.armors.append((x, y, legendary_name, scaled_defense))
            else:
                armor = random.choice(ARMOR)
                scaled_defense = max(1, int(armor["defense"] * scale))
                self.armors.append((x, y, armor["name"], scaled_defense))

    def log_message(self, text: str):
        self.messages.append(text)
        if len(self.messages) > 5:
            self.messages.pop(0)

    def _distance(self, x1: int, y1: int, x2: int, y2: int):
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def _is_visible(self, x: int, y: int):
        return (
            self._distance(self.player.x, self.player.y, x, y) <= self.visibility_radius
        )

    def _update_visited(self):
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self._is_visible(x, y):
                    self.visited.add((x, y))

    @staticmethod
    def visible_length(text: str) -> int:
        """Calculate the visible length of a string, excluding ANSI escape codes.

        ANSI escape codes are sequences like \033[XXm that control text formatting
        but don't take up visible space when displayed.
        """
        import re

        # Remove ANSI escape sequences (ESC[ ... m patterns)
        ansi_pattern = r"\033\[[0-9;]*m"
        return len(re.sub(ansi_pattern, "", text))

    def render(self):
        self.clear_screen()

        # Calculate panel width
        panel_width = 35

        # Get terminal size for better layout
        try:
            import shutil

            term_width, term_height = shutil.get_terminal_size()
            use_side_panel = term_width >= 80
        except:
            use_side_panel = True

        total_attack = self.player.base_attack + self.player.weapon_attack
        total_defense = self.player.base_defense + self.player.armor_defense

        # Group duplicate items with counts
        item_counts = {}
        for item in self.player.inventory:
            item_counts[item] = item_counts.get(item, 0) + 1

        DIM = "\033[90m"
        BRIGHT_GREEN = "\033[92m"
        BRIGHT_RED = "\033[91m"
        BRIGHT_YELLOW = "\033[93m"
        CYAN = "\033[96m"
        RESET = "\033[0m"
        BOLD = "\033[1m"

        # Build dungeon map lines
        dungeon_lines = []
        for y in range(self.dungeon.height):
            row = ""
            for x in range(self.dungeon.width):
                if x == self.player.x and y == self.player.y:
                    row += BRIGHT_GREEN + self.PLAYER + RESET
                elif self._is_visible(x, y):
                    enemy_here = None
                    for enemy in self.enemies:
                        if enemy.x == x and enemy.y == y:
                            enemy_here = enemy
                            break
                    if enemy_here:
                        if enemy_here.is_bounty:
                            row += "\033[95m" + enemy_here.symbol + RESET
                        else:
                            row += BRIGHT_RED + enemy_here.symbol + RESET
                    else:
                        item_here = None
                        for fi in self.floor_items:
                            if fi[0] == x and fi[1] == y:
                                item_here = (fi[2], fi[3])
                                break
                        weapon_here = None
                        for wx, wy, wname, watk in self.weapons:
                            if wx == x and wy == y:
                                weapon_here = (wname, watk)
                                break
                        armor_here = None
                        for ax, ay, aname, adef in self.armors:
                            if ax == x and ay == y:
                                armor_here = (aname, adef)
                                break
                        if weapon_here:
                            row += "\033[95mW\033[0m"
                        elif armor_here:
                            row += "\033[94mA\033[0m"
                        elif item_here:
                            row += BRIGHT_YELLOW + item_here[1] + RESET
                        else:
                            tile = self.dungeon.grid[y][x]
                            if tile == Dungeon.TREASURE:
                                row += BRIGHT_YELLOW + tile + RESET
                            elif (
                                tile == Dungeon.STAIRS_UP or tile == Dungeon.STAIRS_DOWN
                            ):
                                row += CYAN + tile + RESET
                            else:
                                row += tile
                elif (x, y) in self.visited:
                    tile = self.dungeon.grid[y][x]
                    if tile in (
                        Dungeon.TREASURE,
                        Dungeon.TRAP,
                        Dungeon.ENEMY,
                        Dungeon.STAIRS_DOWN,
                        Dungeon.STAIRS_UP,
                    ):
                        row += DIM + Dungeon.FLOOR + RESET
                    else:
                        row += DIM + tile + RESET
                else:
                    row += " "
            dungeon_lines.append(row)

        # Build side panel (ASCII-only for better compatibility)
        panel_lines = []
        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Title
        if self.is_bounty_level:
            title = f"| {BOLD}FLOOR {self.dungeon_level} - BOUNTY{RESET}"
        else:
            title = f"| {BOLD}FLOOR {self.dungeon_level}{RESET}"
        panel_lines.append(
            title + " " * (panel_width - self.visible_length(title)) + "|"
        )

        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Stats
        # Health bar visual (constrained to 10 blocks max)
        hp_bar_width = 10
        max_hp_display = 50  # Cap display at 50
        hp_ratio = min(self.player.health, max_hp_display) / max_hp_display
        hp_filled = int(hp_bar_width * hp_ratio)
        hp_filled = max(0, min(hp_bar_width, hp_filled))
        hp_empty = hp_bar_width - hp_filled
        # Color based on HP level
        if hp_ratio > 0.7:
            hp_color = self.HP_FULL
        elif hp_ratio > 0.4:
            hp_color = self.HP_HIGH
        elif hp_ratio > 0.2:
            hp_color = self.HP_LOW
        else:
            hp_color = self.HP_CRITICAL
        hp_bar = hp_color + "█" * hp_filled + "░" * hp_empty + RESET

        # Status effects indicator
        status_str = ""
        if self.player.poison_turns > 0:
            status_str = " [POISON]"
        elif self.player.slow_turns > 0:
            status_str = " [SLOW]"
        elif self.player.stun_turns > 0:
            status_str = " [STUN]"

        hp_str = f"| HP:{self.player.health}/{self.player.MAX_HP} ATK:{total_attack} DEF:{total_defense}"
        hp_bar_str = f"| [{hp_bar}]{status_str}"
        panel_lines.append(
            hp_str + " " * (panel_width - self.visible_length(hp_str)) + "|"
        )
        panel_lines.append(
            hp_bar_str + " " * (panel_width - self.visible_length(hp_bar_str)) + "|"
        )

        score_str = f"| Score: {self.player.score}"
        panel_lines.append(
            score_str + " " * (panel_width - self.visible_length(score_str)) + "|"
        )

        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Equipment
        equip_header = f"| {BOLD}EQUIPMENT{RESET}"
        panel_lines.append(
            equip_header + " " * (panel_width - self.visible_length(equip_header)) + "|"
        )
        weapon_str = f"| W: {self.player.weapon_name} (+{self.player.weapon_attack})"
        panel_lines.append(
            weapon_str + " " * (panel_width - self.visible_length(weapon_str)) + "|"
        )
        armor_str = f"| A: {self.player.armor_name} (+{self.player.armor_defense})"
        panel_lines.append(
            armor_str + " " * (panel_width - self.visible_length(armor_str)) + "|"
        )

        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Inventory
        inv_header = f"| {BOLD}INVENTORY{RESET}"
        panel_lines.append(
            inv_header + " " * (panel_width - self.visible_length(inv_header)) + "|"
        )
        if item_counts:
            items = list(item_counts.items())[:4]  # Show max 4 items
            for item, count in items:
                if count > 1:
                    item_str = f"| * {item} x{count}"
                else:
                    item_str = f"| * {item}"
                panel_lines.append(
                    item_str + " " * (panel_width - self.visible_length(item_str)) + "|"
                )
        else:
            empty_str = "| (empty)"
            panel_lines.append(
                empty_str + " " * (panel_width - self.visible_length(empty_str)) + "|"
            )

        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Messages
        msg_header = f"| {BOLD}MESSAGES{RESET}"
        panel_lines.append(
            msg_header + " " * (panel_width - self.visible_length(msg_header)) + "|"
        )
        for msg in self.messages[-3:]:  # Show last 3 messages
            # Truncate long messages and strip ANSI codes for display
            if self.visible_length(msg) > panel_width - 4:
                # Need to truncate carefully with ANSI codes
                msg = msg[: panel_width - 7] + "..."
            panel_lines.append(
                f"| {msg}" + " " * (panel_width - self.visible_length(msg) - 3) + "|"
            )

        # Pad panel if needed
        while len(panel_lines) < self.dungeon.height + 4:
            panel_lines.append("|" + " " * (panel_width - 2) + "|")

        panel_lines.append("+" + "-" * (panel_width - 2) + "+")

        # Controls at bottom of panel (only show during gameplay)
        panel_lines.append("| Controls:" + " " * (panel_width - 12) + "|")
        panel_lines.append("| w/a/s/d - Move" + " " * (panel_width - 18) + "|")
        panel_lines.append("| c - Cook" + " " * (panel_width - 12) + "|")
        panel_lines.append("| q - Quit" + " " * (panel_width - 12) + "|")

        # Print header
        print()

        # Print dungeon and panel side by side
        # Each dungeon row is padded to self.width + 4 spaces, then panel follows
        max_lines = max(len(dungeon_lines), len(panel_lines))
        for i in range(max_lines):
            dungeon_line = dungeon_lines[i] if i < len(dungeon_lines) else ""
            panel_line = panel_lines[i] if i < len(panel_lines) else ""
            # Pad dungeon line to exactly self.width visible chars, then add 4 spaces
            visible_len = self.visible_length(dungeon_line)
            # Pad to fill dungeon width, then add 4 spaces before panel
            dungeon_padded = dungeon_line + " " * (self.width - visible_len) + "    "
            print(dungeon_padded + panel_line)

        # Flash effect on combat (show hit/damage briefly)
        if hasattr(self, "_flash_message") and self._flash_message:
            print("\n" + " " * 10 + self._flash_message)
            self._flash_message = None

        print()

    def get_char(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def handle_input(self):
        ch = self.get_char()
        dx, dy = 0, 0
        if ch.lower() == "w":
            dx, dy = 0, -1
        elif ch.lower() == "s":
            dx, dy = 0, 1
        elif ch.lower() == "a":
            dx, dy = -1, 0
        elif ch.lower() == "d":
            dx, dy = 1, 0
        elif ch.lower() == "c":
            self._handle_cooking()
            return
        elif ch.lower() == "q":
            self.running = False
            return

        if dx != 0 or dy != 0:
            new_x = self.player.x + dx
            new_y = self.player.y + dy
            enemy_at_pos = None
            for enemy in self.enemies:
                if enemy.x == new_x and enemy.y == new_y:
                    enemy_at_pos = enemy
                    break
            if enemy_at_pos:
                total_attack = self.player.base_attack + self.player.weapon_attack
                enemy_at_pos.hp -= total_attack
                self.log_message(
                    f"You hit the {enemy_at_pos.name}! HP: {enemy_at_pos.hp}/{enemy_at_pos.max_hp}"
                )
                self.play_sfx("hit")
                # Increase music intensity during combat
                if self.music_gen:
                    self.music_gen.set_intensity(0.7)
                # Flash effect for combat
                self._flash_message = f"\033[91m>>> COMBAT: {enemy_at_pos.name} HP: {enemy_at_pos.hp}/{enemy_at_pos.max_hp} <<<\033[0m"
                if enemy_at_pos.hp <= 0:
                    self.enemies.remove(enemy_at_pos)
                    if enemy_at_pos.is_bounty:
                        bounty_reward = 500 * self.dungeon_level
                        self.player.score += bounty_reward
                        self.log_message(f"BOUNTY COLLECTED! +{bounty_reward} points!")
                        self.log_message("See you, space crawler...")
                    else:
                        self.player.score += 50
                        self.log_message(f"{enemy_at_pos.name} defeated! +50 points")
                    drop_chance = 1.0 if enemy_at_pos.is_bounty else 0.5
                    if random.random() < drop_chance:
                        if enemy_at_pos.is_bounty:
                            drops = [
                                "Monster Meat",
                                "Goblin Ear",
                                "Slime Jelly",
                                "Bat Wing",
                            ]
                            drop_item = random.choice(drops)
                            self.player.inventory.append(drop_item)
                            self.log_message(f"The bounty dropped {drop_item}!")
                        else:
                            all_drops = [enemy_at_pos.drop_item, "Monster Meat"]
                            drop_item = random.choice(all_drops)
                            self.player.inventory.append(drop_item)
                            self.log_message(
                                f"The {enemy_at_pos.name} dropped {drop_item}!"
                            )
                        self.play_sfx("pickup")
            elif self.dungeon.is_walkable(new_x, new_y):
                self.player.x = new_x
                self.player.y = new_y
                if dx != 0 or dy != 0:
                    self._update_visited()
                    # Footstep sound
                    self.play_sfx("footstep")
                    # Return to calmer music when exploring
                    if self.music_gen:
                        self.music_gen.set_intensity(0.3)

        if dx != 0 or dy != 0:
            self._move_enemies()

            # Check if any enemies are nearby and increase tension
            nearby_enemies = sum(
                1
                for e in self.enemies
                if self._distance(e.x, e.y, self.player.x, self.player.y)
                <= self.visibility_radius
            )
            if self.music_gen:
                if nearby_enemies > 0:
                    self.music_gen.set_intensity(0.4 + nearby_enemies * 0.05)
                else:
                    self.music_gen.set_intensity(0.2)

    def _handle_cooking(self):
        inventory = self.player.inventory

        # Recipe 1: Slime Jelly + Cave Rice = Slime Onigiri (15 HP)
        if "Slime Jelly" in inventory and "Cave Rice" in inventory:
            inventory.remove("Slime Jelly")
            inventory.remove("Cave Rice")
            self.player.add_health(15)
            self.log_message("You made Slime Onigiri! +15 HP")
            self.play_sfx("cook")
            return
        # Recipe 2: Cave Apple = Dungeon Apple Jam (10 HP)
        if "Cave Apple" in inventory:
            inventory.remove("Cave Apple")
            self.player.add_health(10)
            self.log_message("You made Dungeon Apple Jam! +10 HP")
            self.play_sfx("cook")
            return
        # Recipe 3: Monster Meat + Flour = Monster Meat Hand Pie (20 HP)
        if "Monster Meat" in inventory and "Flour" in inventory:
            inventory.remove("Monster Meat")
            inventory.remove("Flour")
            self.player.add_health(20)
            self.log_message("You made Monster Meat Hand Pie! +20 HP")
            self.play_sfx("cook")
            return
        # Recipe 4: Ground Cave Corn = Underworld Grits (12 HP)
        if "Ground Cave Corn" in inventory:
            inventory.remove("Ground Cave Corn")
            self.player.add_health(12)
            self.log_message("You made Underworld Grits! +12 HP")
            self.play_sfx("cook")
            return
        # Recipe 5: Goblin Ear + Bat Wing = Cave Skewer (8 HP)
        if "Goblin Ear" in inventory and "Bat Wing" in inventory:
            inventory.remove("Goblin Ear")
            inventory.remove("Bat Wing")
            self.player.add_health(8)
            self.log_message("You roasted a Cave Skewer! +8 HP")
            self.play_sfx("cook")
            return
        # Recipe 6: Slime Jelly + any other ingredient = Suspicious Stew (10 HP)
        if "Slime Jelly" in inventory:
            other_ingredients = [
                "Goblin Ear",
                "Bat Wing",
                "Cave Rice",
                "Cave Apple",
                "Flour",
                "Ground Cave Corn",
            ]
            for other in other_ingredients:
                if other in inventory:
                    inventory.remove("Slime Jelly")
                    inventory.remove(other)
                    self.player.add_health(10)
                    self.log_message("You cooked Suspicious Stew! +10 HP")
                    self.play_sfx("cook")
                    return
        # Recipe 7: Single ingredient = minor heal (2 HP)
        ingredients = [
            "Goblin Ear",
            "Slime Jelly",
            "Bat Wing",
            "Cave Rice",
            "Cave Apple",
            "Flour",
            "Ground Cave Corn",
        ]
        for ingredient in ingredients:
            if ingredient in inventory:
                inventory.remove(ingredient)
                self.player.add_health(2)
                self.log_message(f"You cooked {ingredient}! +2 HP")
                self.play_sfx("cook")
                return
        self.log_message("You have nothing to cook.")

    def _move_enemies(self):
        for enemy in self.enemies:
            if (
                self._distance(enemy.x, enemy.y, self.player.x, self.player.y)
                <= self.visibility_radius
            ):
                old_x, old_y = enemy.x, enemy.y
                enemy.move_towards_player(self.player, self.dungeon, self.enemies)
                if enemy.x == self.player.x and enemy.y == self.player.y:
                    total_defense = self.player.base_defense + self.player.armor_defense

                    # Add damage variance: base_damage + random(0, floor_level)
                    damage_variance = random.randint(0, self.dungeon_level)
                    base_damage = enemy.damage + damage_variance

                    # Defense cap: can only block up to 80% of damage
                    max_block = base_damage * 0.8
                    effective_defense = min(total_defense, max_block)
                    damage = max(
                        1, int(base_damage - effective_defense)
                    )  # At least 1 damage

                    # Check if enemy can attack based on pattern
                    if not enemy.can_attack():
                        self.log_message(f"The {enemy.name} is recovering!")
                        continue

                    # Process player status effects
                    status_damage = self.player.tick_status_effects()
                    if status_damage > 0:
                        self.player.health -= status_damage
                        self.log_message(f"Poison deals {status_damage} damage!")

                    self.player.health -= damage
                    self.log_message(
                        f"The {enemy.name} attacks you! -{damage} HP. Your HP: {self.player.health}"
                    )
                    self.play_sfx("hurt")
                    # Flash effect for taking damage
                    self._flash_message = f"\033[91m>>> DAMAGE: -{damage} HP <<<\033[0m"
                    if self.player.health <= 0:
                        self.log_message("Game Over")
                        self.running = False
                    enemy.x, enemy.y = old_x, old_y

    def check_interactions(self):
        for item in self.floor_items[:]:
            fx, fy, fname, fsym = item
            if fx == self.player.x and fy == self.player.y:
                # Health potion handling
                if fname == "Health Potion":
                    heal_amount = min(20, self.player.MAX_HP - self.player.health)
                    self.player.add_health(20)
                    self.floor_items.remove(item)
                    self.log_message(f"Used Health Potion! +{heal_amount} HP")
                    self.play_sfx("pickup")
                    return
                # Curse item handling
                elif fname in ["Poison Vial", "Weakness Curse", "Slow Trap"]:
                    if fname == "Poison Vial":
                        self.player.apply_status("poison", 5)
                        self.log_message("You are poisoned!")
                    elif fname == "Weakness Curse":
                        self.player.apply_status("weakness", 10)
                        self.log_message("You feel weakened!")
                    elif fname == "Slow Trap":
                        self.player.apply_status("slow", 8)
                        self.log_message("You are slowed!")
                    self.floor_items.remove(item)
                    self.play_sfx("hurt")
                    return
                else:
                    # Regular items
                    self.player.inventory.append(fname)
                    self.floor_items.remove(item)
                    self.log_message(f"You picked up {fname}!")
                    self.play_sfx("pickup")
                    return

        for weapon in self.weapons[:]:
            wx, wy, wname, watk = weapon
            if wx == self.player.x and wy == self.player.y:
                if watk > self.player.weapon_attack:
                    old_weapon = self.player.weapon_name
                    self.player.weapon_name = wname
                    self.player.weapon_attack = watk
                    self.log_message(f"Equipped {wname}! (+{watk} ATK)")
                    if "[LEGENDARY]" in wname:
                        self.log_message("*** LEGENDARY FIND! ***")
                    if old_weapon != "None":
                        self.log_message(f"Replaced {old_weapon}")
                else:
                    if "[LEGENDARY]" in wname:
                        self.log_message(
                            f"Found {wname} (+{watk} ATK) - LEGENDARY but your current weapon is better!"
                        )
                    else:
                        self.log_message(
                            f"Found {wname} (+{watk} ATK) but your current weapon is better"
                        )
                self.weapons.remove(weapon)
                self.play_sfx("pickup")
                return

        for armor in self.armors[:]:
            ax, ay, aname, adef = armor
            if ax == self.player.x and ay == self.player.y:
                if adef > self.player.armor_defense:
                    old_armor = self.player.armor_name
                    self.player.armor_name = aname
                    self.player.armor_defense = adef
                    self.log_message(f"Equipped {aname}! (+{adef} DEF)")
                    if "[LEGENDARY]" in aname:
                        self.log_message("*** LEGENDARY FIND! ***")
                    if old_armor != "None":
                        self.log_message(f"Replaced {old_armor}")
                else:
                    if "[LEGENDARY]" in aname:
                        self.log_message(
                            f"Found {aname} (+{adef} DEF) - LEGENDARY but your current armor is better!"
                        )
                    else:
                        self.log_message(
                            f"Found {aname} (+{adef} DEF) but your current armor is better"
                        )
                self.armors.remove(armor)
                self.play_sfx("pickup")
                return

        tile = self.dungeon.get_tile(self.player.x, self.player.y)
        if tile == Dungeon.TREASURE:
            self.player.score += 100
            self.dungeon.grid[self.player.y][self.player.x] = Dungeon.FLOOR
            self.log_message("You found treasure! +100 points")
            self.play_sfx("pickup")
        elif tile == Dungeon.TRAP:
            self.player.health -= 2
            self.dungeon.grid[self.player.y][self.player.x] = Dungeon.FLOOR
            self.log_message("You triggered a trap! -2 HP")
            if self.player.health <= 0:
                self.log_message("Game Over")
                self.running = False
        elif tile == Dungeon.STAIRS_DOWN:
            self.player.health += 5
            self.dungeon_level += 1
            if self.is_bounty_level:
                self.log_message(
                    f"Bounty complete! Descending to Floor {self.dungeon_level}..."
                )
            else:
                self.log_message(
                    f"You found the exit! +5 HP! Descending to Floor {self.dungeon_level}..."
                )
            self.play_sfx("exit")
            # Increase music intensity as player goes deeper
            if self.music_gen:
                base_intensity = min(1.0, self.dungeon_level * 0.08)
                if self.is_bounty_level:
                    # Boss level - intense music
                    self.music_gen.set_boss_mode(True)
                    self.music_gen.set_intensity(1.0)
                else:
                    self.music_gen.set_boss_mode(False)
                    self.music_gen.set_intensity(base_intensity)
            # Level transition effect - brief pause
            import time

            print("\n" + " " * 20 + "*** Descending... ***")
            time.sleep(0.5)
            self.generate_new_dungeon()

    def show_start_screen(self):
        """Display the title screen with game instructions."""
        self.clear_screen()
        print("\n" * 3)
        print("  ╔═══════════════════════════════════════════════════════════════╗")
        print("  ║" + " " * 62 + " ║")
        print("  ║          ██████╗ █████╗ ██╗   ██╗███████╗██████╗ ███╗   ██╗   ║")
        print("  ║         ██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗████╗  ██║   ║")
        print("  ║         ██║     ███████║██║   ██║█████╗  ██████╔╝██╔██╗ ██║   ║")
        print("  ║         ██║     ██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██║╚██╗██║   ║")
        print("  ║         ╚██████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║██║ ╚████║   ║")
        print("  ║          ╚═════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ║")
        print("  ║" + " " * 62 + " ║")
        print("  ║      ██╗  ██╗██╗████████╗ ██████╗██╗  ██╗███████╗███╗   ██╗   ║")
        print("  ║      ██║ ██╔╝██║╚══██╔══╝██╔════╝██║  ██║██╔════╝████╗  ██║   ║")
        print("  ║      █████╔╝ ██║   ██║   ██║     ███████║█████╗  ██╔██╗ ██║   ║")
        print("  ║      ██╔═██╗ ██║   ██║   ██║     ██╔══██║██╔══╝  ██║╚██╗██║   ║")
        print("  ║      ██║  ██╗██║   ██║   ╚██████╗██║  ██║███████╗██║ ╚████║   ║")
        print("  ║      ╚═╝  ╚═╝╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝   ║")
        print("  ║" + " " * 62 + " ║")
        print("  ╠═══════════════════════════════════════════════════════════════╣")
        print("  ║" + " " * 62 + " ║")
        print("  ║  Descend into endless procedurally generated dungeons!        ║")
        print("  ║  Cook monster drops into meals to survive.                    ║")
        print("  ║  Find weapons and armor that scale with depth.                ║")
        print("  ║  Hunt bounty bosses every 5 floors!                           ║")
        print("  ║" + " " * 62 + " ║")
        print("  ╠═══════════════════════════════════════════════════════════════╣")
        print("  ║" + " " * 62 + " ║")
        print("  ║  CONTROLS:                                                    ║")
        print("  ║    w/a/s/d  - Move                                            ║")
        print("  ║    c        - Cook (use ingredients)                          ║")
        print("  ║    q        - Quit                                            ║")
        print("  ║" + " " * 62 + " ║")
        print("  ╠═══════════════════════════════════════════════════════════════╣")
        print("  ║" + " " * 62 + " ║")
        print("  ║  TIPS:                                                        ║")
        print("  ║    * Cook often - ingredients are plentiful, HP is precious   ║")
        print("  ║    * Gear scales - deeper floors give better stats            ║")
        print("  ║    * Watch for Legendaries - 5% chance for 2x stats           ║")
        print("  ║    * Prep for Bounties - heal up before floors 5, 10, 15...   ║")
        print("  ║" + " " * 62 + " ║")
        print("  ╚═══════════════════════════════════════════════════════════════╝")
        print()
        print("  Press any key to begin your descent...")
        self.get_char()

    def show_death_screen(self):
        """Display the death screen with final stats."""
        self.clear_screen()
        print("\n" * 5)
        print("  ╔════════════════════════════════════════════════════════════╗")
        print("  ║" + " " * 60 + "║")
        print("  ║    ██████╗  █████╗ ███╗   ███╗███████╗                     ║")
        print("  ║   ██╔════╝ ██╔══██╗████╗ ████║██╔════╝                     ║")
        print("  ║   ██║  ███╗███████║██╔████╔██║█████╗                       ║")
        print("  ║   ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝                       ║")
        print("  ║   ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗                     ║")
        print("  ║    ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝                     ║")
        print("  ║" + " " * 60 + "║")
        print("  ║          ██████╗ ██╗   ██╗███████╗██████╗  ██╗             ║")
        print("  ║         ██╔═══██╗██║   ██║██╔════╝██╔══██╗ ██║             ║")
        print("  ║         ██║   ██║██║   ██║█████╗  ██████╔╝ ██║             ║")
        print("  ║         ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗ ╚═╝             ║")
        print("  ║         ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║ ██╗             ║")
        print("  ║          ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝ ╚═╝             ║")
        print("  ║" + " " * 60 + "║")
        print("  ╠════════════════════════════════════════════════════════════╣")
        print("  ║" + " " * 60 + "║")
        print(f"  ║  Final Floor: {self.dungeon_level:<45}║")
        print(f"  ║  Final Score: {self.player.score:<45}║")
        print(f"  ║  Enemies Defeated: {self.player.score // 50:<40}║")
        print("  ║" + " " * 60 + "║")
        print("  ╠════════════════════════════════════════════════════════════╣")
        print("  ║" + " " * 60 + "║")
        print("  ║  EQUIPMENT:                                                ║")
        print(f"  ║    Weapon: {self.player.weapon_name:<48}║")
        print(f"  ║    Armor: {self.player.armor_name:<49}║")
        print("  ║" + " " * 60 + "║")
        print("  ╚════════════════════════════════════════════════════════════╝")
        print()
        print("  Press any key to return to the title screen...")

        # Use your Windows-safe input method
        self.get_char()

        # Wait for any key press
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def run(self):
        # Initialize audio
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.music_gen = ProceduralMusicGenerator(sample_rate=44100)
        self.sfx_gen = SoundEffectGenerator(sample_rate=44100)
        self.audio_initialized = True

        while True:
            # Show title screen
            self.music_gen.start()
            self.show_start_screen()
            self.music_gen.stop()

            # Start game
            self.running = True
            self.dungeon_level = 1
            self.music_gen.start()
            self.generate_new_dungeon()

            while self.running:
                self.render()
                self.handle_input()
                if self.running:
                    self.check_interactions()

            # Show death screen
            self.music_gen.stop()
            self.show_death_screen()

            # Ask if player wants to play again
            print("\n  Play again? (y/n): ", end="", flush=True)
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1).lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            if ch != "y":
                break

        pygame.quit()
        print("  Thanks for playing CAVERN KITCHEN!")
        print("  How deep will you go next time?")


def main():
    width = 30
    height = 15
    args = sys.argv[1:]
    if len(args) >= 1:
        width = int(args[0])
    if len(args) >= 2:
        height = int(args[1])
    if width < 10 or height < 10:
        print("Warning: Dungeon too small. Using minimum size 10x10.")
        width = max(width, 10)
        height = max(height, 10)
    if width > 100 or height > 50:
        print("Warning: Dungeon too large. Cap at 100x50.")
        width = min(width, 100)
        height = min(height, 50)

    game = Game(width, height)
    game.run()


if __name__ == "__main__":
    main()
