import pygame


def read_steer_axis() -> float:
    """Return -1 (left), 0 (center), or +1 (right) from the keyboard."""
    keys = pygame.key.get_pressed()
    left = keys[pygame.K_LEFT] or keys[pygame.K_a]
    right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    if left and not right:
        return -1.0
    if right and not left:
        return 1.0
    return 0.0
