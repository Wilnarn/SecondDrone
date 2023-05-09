import pygame

# Initialize the player, only need once
pygame.mixer.init()

# Load music and play
pygame.mixer.music.load("space-odyssey.mp3")
pygame.mixer.music.play()

# The while loop keeps the code running while music is playing
while pygame.mixer.music.get_busy() == True:
    continue
