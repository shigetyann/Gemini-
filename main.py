
import pyxel
import random

class Game:
    def __init__(self):
        pyxel.init(256, 160, title="Cave Explorer", fps=60)

        # World settings
        self.world_width = 1024
        self.camera_x = 0
        
        # Player
        self.player_start_x = 20
        self.player_x = self.player_start_x
        self.player_y = 120
        self.player_vy = 0
        self.player_health = 3
        self.jumps_left = 2
        self.invincible_timer = 0

        # Game Elements
        self.stage = []
        self.spikes = []
        self.enemies = []
        self.bullets = []
        self.goal = (0,0,0,0,0)
        self.max_enemies = 20
        self.enemy_spawn_timer = 0
        self.coins = []
        self.score = 0
        self.create_sprites()
        self.setup_level()

        # Game State
        self.game_started = False
        self.time_left = 180 * 60 # 3 minutes in frames
        self.game_over = False
        self.game_clear = False

        pyxel.run(self.update, self.draw)

    def setup_level(self):
        # Clear all dynamic elements
        self.stage.clear()
        self.spikes.clear()
        self.enemies.clear()

        # 1. Generate Ground with Gaps (Pit Traps)
        current_x = 0
        while current_x < self.world_width:
            ground_length = random.randint(80, 200)
            self.stage.append((current_x, 132, ground_length, 28, 3)) # Ground block
            current_x += ground_length
            if current_x < self.world_width - 150: # Avoid gap near the end
                gap_width = random.randint(32, 56) # Jumpable gap
                current_x += gap_width

        # 2. Generate Spikes on Ground
        for x, y, w, h, col in self.stage:
            if y == 132: # Only on main ground
                for i in range(x, x + w, 64):
                    if random.random() < 0.35 and i > 80: # 35% chance, not in start area
                        spike_x = random.randint(i, i + 48)
                        if spike_x < x + w - 16:
                            self.spikes.append((spike_x, 124, 16, 8, 6)) # Light Grey Spikes

        # 3. Generate Platforms with Minimum Gap
        platforms = []
        min_gap = 24  # 3 * player width (8px)
        for _ in range(15):  # Attempt to create 15 platforms
            for _ in range(100):  # Try 100 times to find a valid spot
                plat_w = random.randint(40, 80)
                plat_x = random.randint(100, self.world_width - 100 - plat_w)
                plat_y = random.choice([92, 108])

                is_valid_spot = True
                # Check against other newly generated platforms for overlap
                for ex, _, ew, _, _ in platforms:
                    if (plat_x < ex + ew + min_gap and
                        plat_x + plat_w + min_gap > ex):
                        is_valid_spot = False
                        break
                
                if is_valid_spot:
                    platforms.append((plat_x, plat_y, plat_w, 8, 3))
                    break  # Found a spot, move to the next platform
        
        self.stage.extend(platforms)

        # 5. Generate Coins
        for x, y, w, h, col in self.stage:
            for i in range(x, x + w, 16):
                if random.random() < 0.2: # 20% chance for a coin
                    self.coins.append((i + 4, y - 12, 8, 8, 10)) # Yellow coins

        # 6. Place Initial Enemies (Patrol and Shooter)
        patrol_count = 0
        shooter_count = 0
        for x, y, w, h, col in self.stage:
            # Place Patrol enemies on the ground
            if y == 132 and w > 60 and random.random() < 0.5 and patrol_count < 4:
                enemy_x = x + 10
                self.enemies.append({
                    'x': enemy_x, 'y': y - 8, 'speed': random.choice([-0.8, 0.8]),
                    'type': 'patrol', 'min_x': x, 'max_x': x + w - 8, 'color': 8 # Red
                })
                patrol_count += 1
            # Place Shooter enemies on platforms
            elif y != 132 and w > 40 and random.random() < 0.4 and shooter_count < 3:
                enemy_x = x + w // 2 - 4
                self.enemies.append({
                    'x': enemy_x, 'y': y - 8, 'type': 'shooter', 'shoot_timer': random.randint(60, 120),
                    'color': 14 # Dark Blue
                })
                shooter_count += 1
        
        # 7. Set Goal Position
        self.goal = (self.world_width - 40, 116, 8, 16, 11)

    def create_sprites(self):
        # Coin Sprite (8x8) at img=0, u=0, v=0
        pyxel.image(0).set(0, 0, [
            "00AA0000",
            "0A7AA000",
            "A7999A00",
            "A9999A00",
            "A9999A00",
            "A9999A00",
            "0AAAA000",
            "00AA0000",
            " ",
        ])

    def update(self):
        if not self.game_started:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.game_started = True
            return

        if self.game_over or self.game_clear:
            if pyxel.btnp(pyxel.KEY_R):
                self.restart()
            return

        self.time_left -= 1
        if self.time_left <= 0:
            self.game_over = True

        self.update_player()
        self.update_enemies()
        self.update_bullets()
        self.check_collisions()
        self.update_camera()

    def update_player(self):
        # Movement
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x = max(self.player_x - 2, 0)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x = min(self.player_x + 2, self.world_width - 8)

        # Gravity
        self.player_y += self.player_vy
        self.player_vy = min(self.player_vy + 0.5, 3)

        on_ground = self.check_ground_collision()
        if on_ground:
            self.player_vy = 0
            self.jumps_left = 2

        # Double Jump
        if pyxel.btnp(pyxel.KEY_SPACE) and self.jumps_left > 0:
            self.player_vy = -8
            self.jumps_left -= 1

        # Invincibility
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def check_ground_collision(self):
        for x, y, w, h, col in self.stage:
            if (self.player_x + 8 > x and self.player_x < x + w and
                self.player_y + 8 > y and self.player_y < y + h and self.player_vy >= 0):
                self.player_y = y - 8
                return True
        return False

    def update_enemies(self):
        # Spawn new random enemies
        self.enemy_spawn_timer -= 1
        if len(self.enemies) < self.max_enemies and self.enemy_spawn_timer <= 0:
            spawn_x = self.camera_x + pyxel.width + 10
            spawn_y = random.choice([124, 100, 84])
            enemy_type = random.choice(['stream', 'chase'])
            if enemy_type == 'stream':
                self.enemies.append({'x': spawn_x, 'y': spawn_y, 'speed': -random.uniform(1.0, 2.0), 'type': 'stream', 'color': 9})
            elif enemy_type == 'chase':
                self.enemies.append({'x': spawn_x, 'y': spawn_y, 'speed': random.uniform(0.4, 0.8), 'type': 'chase', 'color': 10})
            self.enemy_spawn_timer = random.randint(90, 150)

        # Update enemy positions
        for enemy in self.enemies[:]:
            if enemy['type'] == 'patrol':
                enemy['x'] += enemy['speed']
                if enemy['x'] < enemy['min_x'] or enemy['x'] > enemy['max_x']:
                    enemy['speed'] *= -1
            elif enemy['type'] == 'shooter':
                enemy['shoot_timer'] -= 1
                player_dist = abs(self.player_x - enemy['x'])
                if enemy['shoot_timer'] <= 0 and player_dist < 120:
                    # Shoot a bullet towards the player
                    dx = self.player_x - enemy['x']
                    dy = self.player_y - enemy['y']
                    dist = (dx**2 + dy**2)**0.5
                    if dist > 0:
                        self.bullets.append({
                            'x': enemy['x'] + 4, 'y': enemy['y'] + 4,
                            'vx': (dx / dist) * 2, 'vy': (dy / dist) * 2, 'color': 8
                        })
                    enemy['shoot_timer'] = random.randint(100, 160)
            elif enemy['type'] == 'stream':
                enemy['x'] += enemy['speed']
                if enemy['x'] < self.camera_x - 20: self.enemies.remove(enemy)
            elif enemy['type'] == 'chase':
                dx = self.player_x - enemy['x']
                dy = self.player_y - enemy['y']
                dist = (dx**2 + dy**2)**0.5
                if dist > 0: enemy['x'] += (dx / dist) * enemy['speed']; enemy['y'] += (dy / dist) * enemy['speed']
                if enemy['x'] < self.camera_x - 20: self.enemies.remove(enemy)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['vx']
            bullet['y'] += bullet['vy']
            # Remove bullets that are off-screen
            if (bullet['x'] < self.camera_x or bullet['x'] > self.camera_x + pyxel.width or
                bullet['y'] < 0 or bullet['y'] > pyxel.height):
                self.bullets.remove(bullet)

    def check_collisions(self):
        # Player vs Enemies
        if self.invincible_timer == 0:
            for enemy in self.enemies:
                if abs(self.player_x - enemy['x']) < 6 and abs(self.player_y - enemy['y']) < 6:
                    self.player_health -= 1; self.invincible_timer = 120
                    if self.player_health <= 0: self.game_over = True
                    break
        # Player vs Bullets
        if self.invincible_timer == 0:
            for bullet in self.bullets[:]:
                if abs(self.player_x - bullet['x']) < 4 and abs(self.player_y - bullet['y']) < 4:
                    self.player_health -= 1
                    self.invincible_timer = 120
                    self.bullets.remove(bullet)
                    if self.player_health <= 0: self.game_over = True
                    break # Exit after one hit

        # Player vs Spikes
        if self.invincible_timer == 0:
            for x, y, w, h, col in self.spikes:
                if (self.player_x + 7 > x and self.player_x < x + w -1 and self.player_y + 7 > y):
                    self.player_health -= 1; self.invincible_timer = 120
                    if self.player_health <= 0: self.game_over = True
                    break

        # Player vs Coins
        for coin in self.coins[:]:
            cx, cy, cw, ch, ccol = coin
            if (self.player_x + 8 > cx and self.player_x < cx + cw and
                self.player_y + 8 > cy and self.player_y < cy + ch):
                self.coins.remove(coin)
                self.score += 10

        # Player vs Goal
        gx, gy, gw, gh, gcol = self.goal
        if (self.player_x + 8 > gx and self.player_x < gx + gw and self.player_y + 8 > gy and self.player_y < gy + gh):
            self.game_clear = True
        # Fall death
        if self.player_y > pyxel.height: self.game_over = True

    def update_camera(self):
        self.camera_x = max(0, min(self.player_x - pyxel.width / 2, self.world_width - pyxel.width))

    def draw(self):
        pyxel.cls(0)
        if not self.game_started:
            pyxel.text(110, 70, "START", pyxel.frame_count % 16); pyxel.text(80, 90, "Press SPACE to Play", 7); return

        pyxel.camera(self.camera_x, 0)
        # Draw stage, spikes, goal
        for x, y, w, h, col in self.stage: pyxel.rect(x, y, w, h, col)
        for x, y, w, h, col in self.spikes: pyxel.rect(x, y, w, h, col) # Spikes are now color 6
        for x, y, w, h, col in self.coins: pyxel.blt(x, y, 0, 0, 0, w, h, 0)
        gx, gy, gw, gh, gcol = self.goal
        pyxel.rect(gx, gy, gw, gh, gcol)
        # Draw bullets
        for bullet in self.bullets:
            pyxel.rect(bullet['x'], bullet['y'], 2, 2, bullet['color'])
        # Draw enemies
        for enemy in self.enemies: pyxel.rect(enemy['x'], enemy['y'], 8, 8, enemy['color'])
        # Draw player
        if self.invincible_timer % 10 < 5: pyxel.rect(self.player_x, self.player_y, 8, 8, 7)

        pyxel.camera()
        # Draw UI
        pyxel.text(5, 5, f"Health: {self.player_health}", 7)
        pyxel.text(80, 5, f"Score: {self.score}", 7)
        pyxel.text(180, 5, f"Time: {self.time_left // 60}", 7)
        if self.game_over: pyxel.text(110, 70, "GAME OVER", 8); pyxel.text(90, 90, "Press R to Restart", 7)
        if self.game_clear: pyxel.text(110, 70, "GAME CLEAR!", 11); pyxel.text(90, 90, "Press R to Restart", 7)
            
    def restart(self):
        self.camera_x = 0
        self.player_x = self.player_start_x
        self.player_y = 120
        self.player_vy = 0
        self.player_health = 3
        self.jumps_left = 2
        self.invincible_timer = 0
        self.coins.clear()
        self.bullets.clear()
        self.score = 0
        self.setup_level()
        self.enemy_spawn_timer = 0
        self.time_left = 180 * 60
        self.game_over = False
        self.game_clear = False
        self.game_started = False

Game()
