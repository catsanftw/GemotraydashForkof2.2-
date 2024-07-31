import pygame
import random
import json
import math
from array import array

# Initialize Pygame and its mixer
pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
except pygame.error:
    print("Warning: Unable to initialize sound mixer. Game will run without sound.")

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Geometry Dash 2.2 NES Edition")

# Colors
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RED, BLUE, GREEN, GRAY, YELLOW, PURPLE = (255, 0, 0), (0, 0, 255), (0, 255, 0), (128, 128, 128), (255, 255, 0), (128, 0, 128)

# Fonts
font = pygame.font.Font(None, 36)
title_font = pygame.font.Font(None, 72)

# Game modes
CUBE, SHIP, BALL, UFO, WAVE = 0, 1, 2, 3, 4

# Player properties
player_size = 40
player_x = 100
player_y = HEIGHT - player_size - 60
player_y_velocity = 0
jump_height = -15
gravity = 0.8

# Ground properties
ground_height = 60

# Game variables
score = 0
game_mode = CUBE
practice_mode = False

# Level editor variables
editor_grid_size = 40
editor_scroll_x = 0
current_object = 'block'

# Level structure
level = []

# Improved NES-style sound engine
class NESSound:
    def __init__(self):
        self.sample_rate = 44100
        self.amplitude = 2 ** 15 - 1  # 16-bit audio

    def square_wave(self, frequency, duration, duty_cycle=0.5):
        num_samples = int(self.sample_rate * duration)
        period = int(self.sample_rate / frequency)
        samples = array('h', [0] * num_samples)

        for i in range(num_samples):
            if (i % period) / period < duty_cycle:
                samples[i] = self.amplitude
            else:
                samples[i] = -self.amplitude

        return pygame.mixer.Sound(buffer=samples)

    def triangle_wave(self, frequency, duration):
        num_samples = int(self.sample_rate * duration)
        period = int(self.sample_rate / frequency)
        samples = array('h', [0] * num_samples)

        for i in range(num_samples):
            value = ((i % period) / period * 4 - 2)
            if value > 1:
                value = 2 - value
            elif value < -1:
                value = -2 - value
            samples[i] = int(value * self.amplitude)

        return pygame.mixer.Sound(buffer=samples)

    def noise(self, duration, frequency=440):
        num_samples = int(self.sample_rate * duration)
        samples = array('h', [0] * num_samples)

        register = 1
        for i in range(num_samples):
            bit = (register ^ (register >> 1)) & 1
            register = (register >> 1) | (bit << 14)
            samples[i] = (bit * 2 - 1) * self.amplitude

        return pygame.mixer.Sound(buffer=samples)

    def envelope(self, sound, attack=0.01, decay=0.1, sustain=0.7, release=0.1):
        samples = array('h', sound.get_raw())
        num_samples = len(samples)
        attack_samples = int(attack * self.sample_rate)
        decay_samples = int(decay * self.sample_rate)
        sustain_samples = int(sustain * self.sample_rate)
        release_samples = int(release * self.sample_rate)

        for i in range(num_samples):
            if i < attack_samples:
                factor = i / attack_samples
            elif i < attack_samples + decay_samples:
                factor = 1.0 - (1.0 - sustain) * ((i - attack_samples) / decay_samples)
            elif i < attack_samples + decay_samples + sustain_samples:
                factor = sustain
            else:
                factor = sustain * (1 - (i - (attack_samples + decay_samples + sustain_samples)) / release_samples)
            
            samples[i] = int(samples[i] * factor)

        return pygame.mixer.Sound(buffer=samples)

# Initialize NESSound
nes_sound = NESSound()

# Create improved NES-style sounds
try:
    sounds = {
        "jump": nes_sound.envelope(nes_sound.square_wave(660, 0.1, 0.125), attack=0.01, decay=0.05, sustain=0.1, release=0.05),
        "land": nes_sound.envelope(nes_sound.square_wave(330, 0.1, 0.5), attack=0.01, decay=0.05, sustain=0.1, release=0.05),
        "collect": nes_sound.envelope(nes_sound.triangle_wave(880, 0.1), attack=0.01, decay=0.05, sustain=0.05, release=0.05),
        "crash": nes_sound.envelope(nes_sound.noise(0.2), attack=0.01, decay=0.1, sustain=0.1, release=0.1),
    }

    # Adjust volume
    for sound in sounds.values():
        sound.set_volume(0.2)
except Exception as e:
    print(f"Warning: Unable to create sounds. Error: {e}")
    sounds = {}

# Button class placeholder
class Button:
    def __init__(self, x, y, width, height, text, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.color = GRAY

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surf = font.render(self.text, True, BLACK)
        screen.blit(text_surf, (self.rect.x + (self.rect.width - text_surf.get_width()) // 2,
                                self.rect.y + (self.rect.height - text_surf.get_height()) // 2))

    def click(self):
        self.action()

# Utility functions
def draw_ground():
    pygame.draw.rect(screen, GREEN, (0, HEIGHT - ground_height, WIDTH, ground_height))

def draw_level():
    for obj in level:
        color = RED if obj['type'] == 'block' else YELLOW if obj['type'] == 'orb' else BLUE if obj['type'] == 'portal' else GRAY
        pygame.draw.rect(screen, color, (obj['x'] - editor_scroll_x, obj['y'], editor_grid_size, editor_grid_size))

def draw_player(x, y):
    pygame.draw.rect(screen, BLUE, (x, y, player_size, player_size))

def draw_hud():
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))

def main_menu():
    play_button = Button(WIDTH // 2 - 100, HEIGHT // 2 - 50, 200, 50, "Play", start_game)
    editor_button = Button(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 50, "Editor", start_editor)

    running = True
    while running:
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_button.rect.collidepoint(event.pos):
                    play_button.click()
                elif editor_button.rect.collidepoint(event.pos):
                    editor_button.click()

        play_button.draw(screen)
        editor_button.draw(screen)

        pygame.display.flip()
        pygame.time.Clock().tick(60)

def start_game():
    game_loop()

def start_editor():
    # Placeholder for level editor functionality
    pass

# Improved game loop
def game_loop():
    global player_y, player_y_velocity, score, game_mode, practice_mode, editor_scroll_x

    player_y = HEIGHT - player_size - 60
    player_y_velocity = 0
    score = 0
    editor_scroll_x = 0
    was_on_ground = True

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_mode in [CUBE, SHIP, UFO] and player_y == HEIGHT - player_size - ground_height:
                        player_y_velocity = jump_height
                        if "jump" in sounds:
                            sounds["jump"].play()
                    elif game_mode == BALL:
                        player_y_velocity *= -1
                        if "jump" in sounds:
                            sounds["jump"].play()
                    elif game_mode == WAVE:
                        player_y_velocity = -abs(player_y_velocity)  # Always move upwards
                        if "jump" in sounds:
                            sounds["jump"].play()
                elif event.key == pygame.K_m:
                    game_mode = (game_mode + 1) % 5
                elif event.key == pygame.K_p:
                    practice_mode = not practice_mode
                elif event.key == pygame.K_ESCAPE:
                    return True

        # Update player position
        if game_mode in [CUBE, BALL, UFO]:
            player_y_velocity += gravity
        elif game_mode == SHIP:
            if pygame.key.get_pressed()[pygame.K_SPACE]:
                player_y_velocity -= gravity / 2
            else:
                player_y_velocity += gravity / 2
        elif game_mode == WAVE:
            player_y_velocity = math.sin(editor_scroll_x * 0.1) * 5

        player_y += player_y_velocity

        # Check if player just landed
        on_ground = player_y >= HEIGHT - player_size - ground_height
        if on_ground and not was_on_ground:
            if "land" in sounds:
                sounds["land"].play()
        was_on_ground = on_ground

        if player_y > HEIGHT - player_size - ground_height:
            player_y = HEIGHT - player_size - ground_height
            player_y_velocity = 0
        elif player_y < 0:
            player_y = 0
            player_y_velocity = 0

        # Move level (simulating player movement)
        editor_scroll_x += 5

        # Check for collision
        for obj in level:
            if (player_x < obj['x'] - editor_scroll_x + 40 and
                player_x + player_size > obj['x'] - editor_scroll_x and
                player_y < obj['y'] + 40 and
                player_y + player_size > obj['y']):
                if obj['type'] == 'block' or obj['type'] == 'spike':
                    if not practice_mode:
                        if "crash" in sounds:
                            sounds["crash"].play()
                        print(f"Game Over! Final Score: {score}")
                        return True
                    else:
                        player_y = HEIGHT - player_size - ground_height
                        player_y_velocity = 0
                elif obj['type'] == 'orb':
                    player_y_velocity = jump_height
                    if "collect" in sounds:
                        sounds["collect"].play()
                elif obj['type'] == 'portal':
                    game_mode = (game_mode + 1) % 5

        # Increase score
        score += 1

        # Clear the screen
        screen.fill(BLACK)

        # Draw game elements
        draw_ground()
        draw_level()
        draw_player(player_x, player_y)
        draw_hud()

        # Update the display
        pygame.display.flip()

        # Control the frame rate
        pygame.time.Clock().tick(60)

if __name__ == "__main__":
    main_menu()
    pygame.quit()
