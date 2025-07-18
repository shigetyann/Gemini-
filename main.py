import pyxel
import random

class Game:
    def __init__(self):
        pyxel.init(160, 160, title="Cave Explorer", fps=60)

        # World settings
        self.world_width = 2048
        self.camera_x = 0
        
        # Player
        self.player_start_x = 20
        self.player_x = self.player_start_x
        self.player_y = 120
        self.player_vy = 0
        self.player_health = 3
        self.jumps_left = 2
        self.invincible_timer = 0
        self.player_shoot_cooldown = 0
        self.player_direction = 1
        self.enemy_safe_zone = self.player_start_x + (4 * 8)

        # Weapon
        self.weapon_type = 'normal'
        self.charge_level = 0
        self.enemy_kill_count = 0
        self.upgrade_items = []
        self.game_paused = False
        self.weapon_selection = 0

        # Ammo
        self.normal_ammo = 20
        self.shotgun_ammo = 20
        self.charge_ammo = 20
        self.max_normal_ammo = 20
        self.max_shotgun_ammo = 20
        self.max_charge_ammo = 20
        self.distance_moved = 0
        self.last_player_x = self.player_x

        # Health Recovery
        self.collected_coins_for_heart = 0
        self.hearts = []

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

        # Game State
        self.game_started = False
        self.level_initialized = False
        self.time_left = 180 * 60
        self.game_over = False
        self.game_clear = False
        self.start_protection_timer = 0

        pyxel.run(self.update, self.draw)

    def setup_level(self):
        self.stage.clear()
        self.spikes.clear()
        self.enemies.clear()
        self.bullets.clear()
        self.coins.clear()
        self.upgrade_items.clear()
        self.hearts.clear()

        current_x = 0
        while current_x < self.world_width:
            ground_length = random.randint(80, 200)
            self.stage.append((current_x, 132, ground_length, 28, 3))
            current_x += ground_length
            if current_x < self.world_width - 150:
                gap_width = random.randint(32, 56)
                current_x += gap_width

        for x, y, w, h, col in self.stage:
            if y == 132:
                for i in range(x, x + w, 64):
                    if random.random() < 0.35 and i > 80:
                        spike_x = random.randint(i, i + 48)
                        if spike_x < x + w - 16:
                            self.spikes.append((spike_x, 124, 16, 8, 6))

        platforms = []
        min_gap = 24
        for _ in range(15):
            for _ in range(100):
                plat_w = random.randint(40, 80)
                plat_x = random.randint(100, self.world_width - 100 - plat_w)
                plat_y = random.choice([92, 108])
                is_valid_spot = True
                for ex, _, ew, _, _ in platforms:
                    if (plat_x < ex + ew + min_gap and plat_x + plat_w + min_gap > ex):
                        is_valid_spot = False
                        break
                if is_valid_spot:
                    platforms.append((plat_x, plat_y, plat_w, 8, 3))
                    break
        self.stage.extend(platforms)

        for x, y, w, h, col in self.stage:
            for i in range(x, x + w, 16):
                if random.random() < 0.2:
                    self.coins.append((i + 4, y - 12, 8, 8, 10))

        patrol_count = 0
        shooter_count = 0
        for x, y, w, h, col in self.stage:
            if y == 132 and w > 60 and random.random() < 0.5 and patrol_count < 4:
                enemy_x = x + 10
                if enemy_x >= self.enemy_safe_zone:
                    self.enemies.append({
                        'x': enemy_x, 'y': y - 8, 'speed': random.choice([-0.8, 0.8]),
                        'type': 'patrol', 'min_x': x, 'max_x': x + w - 8, 'color': 8
                    })
                    patrol_count += 1
            elif y != 132 and w > 40 and random.random() < 0.4 and shooter_count < 3:
                enemy_x = x + w // 2 - 4
                self.enemies.append({
                    'x': enemy_x, 'y': y - 8, 'type': 'shooter', 'shoot_timer': random.randint(60, 120),
                    'color': 14
                })
                shooter_count += 1
        
        self.goal = (self.world_width - 40, 116, 8, 16, 11)

    def create_sprites(self):
        pyxel.image(0).set(0, 0, [
            "00AA0000", "0A7AA000", "A7999A00", "A9999A00",
            "A9999A00", "A9999A00", "0AAAA000", "00AA0000",
        ])

    def update(self):
        if self.game_paused:
            if pyxel.btnp(pyxel.KEY_UP):
                self.weapon_selection = (self.weapon_selection - 1) % 2
            if pyxel.btnp(pyxel.KEY_DOWN):
                self.weapon_selection = (self.weapon_selection + 1) % 2
            if pyxel.btnp(pyxel.KEY_RETURN):
                if self.weapon_selection == 0:
                    self.weapon_type = 'shotgun'
                else:
                    self.weapon_type = 'charge'
                self.game_paused = False
            return

        if not self.game_started:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.game_started = True
                self.start_protection_timer = 180
                if not self.level_initialized:
                    self.setup_level()
                    self.level_initialized = True
            return

        if self.game_over or self.game_clear:
            if pyxel.btnp(pyxel.KEY_R):
                self.restart()
            return

        if self.start_protection_timer > 0:
            self.start_protection_timer -= 1

        self.time_left -= 1
        if self.time_left <= 0:
            self.game_over = True

        self.update_player()
        self.update_enemies()
        self.update_bullets()
        self.check_collisions()
        self.update_camera()

    def update_player(self):
        # Track horizontal movement for ammo replenishment
        self.distance_moved += abs(self.player_x - self.last_player_x)
        self.last_player_x = self.player_x

        if self.distance_moved >= 120:
            if self.weapon_type == 'normal':
                self.normal_ammo = self.max_normal_ammo
            elif self.weapon_type == 'shotgun':
                self.shotgun_ammo = self.max_shotgun_ammo
            elif self.weapon_type == 'charge':
                self.charge_ammo = self.max_charge_ammo
            self.distance_moved = 0

        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x = max(self.player_x - 2, 0)
            self.player_direction = -1
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x = min(self.player_x + 2, self.world_width - 8)
            self.player_direction = 1

        self.player_y += self.player_vy
        self.player_vy = min(self.player_vy + 0.5, 3)

        on_ground = self.check_ground_collision()
        if on_ground:
            self.player_vy = 0
            self.jumps_left = 2

        if pyxel.btnp(pyxel.KEY_SPACE) and self.jumps_left > 0:
            if self.jumps_left == 2:
                self.player_vy = -6
            else:
                self.player_vy = -5
            self.jumps_left -= 1

        if self.player_shoot_cooldown > 0:
            self.player_shoot_cooldown -= 1

        if self.weapon_type == 'charge':
            if pyxel.btn(pyxel.KEY_F):
                self.charge_level = min(self.charge_level + 1, 90)
            if pyxel.btnr(pyxel.KEY_F) and self.player_shoot_cooldown == 0:
                ammo_cost = 1 + (self.charge_level // 10) # 1 to 10 bullets
                
                if self.charge_ammo >= ammo_cost:
                    bullet_size = 2 + int((self.charge_level / 90) * 22)
                    bullet_x = self.player_x + 4 - bullet_size / 2
                    bullet_y = self.player_y + 4 - bullet_size / 2
                    self.bullets.append({
                        'x': bullet_x, 'y': bullet_y, 'vx': 4 * self.player_direction, 
                        'vy': 0, 'color': 5, 'shooter': 'player', 'size': bullet_size
                    })
                    self.player_shoot_cooldown = 20
                    self.charge_ammo -= ammo_cost
                self.charge_level = 0
        elif pyxel.btn(pyxel.KEY_F) and self.player_shoot_cooldown == 0:
            if self.weapon_type == 'normal':
                if self.normal_ammo > 0:
                    self.bullets.append({
                        'x': self.player_x + 4, 'y': self.player_y + 4, 'vx': 4 * self.player_direction, 
                        'vy': 0, 'color': 5, 'shooter': 'player', 'size': 2
                    })
                    self.player_shoot_cooldown = 20
                    self.normal_ammo -= 1
            elif self.weapon_type == 'shotgun':
                if self.shotgun_ammo > 0:
                    for i in range(-1, 2):
                        self.bullets.append({
                            'x': self.player_x + 4, 'y': self.player_y + 4, 'vx': 4 * self.player_direction, 
                            'vy': i * 0.5, 'color': 5, 'shooter': 'player', 'size': 2
                        })
                    self.player_shoot_cooldown = 60
                    self.shotgun_ammo -= 1

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

        for enemy in self.enemies[:]:
            if enemy['type'] == 'patrol':
                enemy['x'] += enemy['speed']
                if enemy['x'] < enemy['min_x'] or enemy['x'] > enemy['max_x']:
                    enemy['speed'] *= -1
            elif enemy['type'] == 'shooter':
                enemy['shoot_timer'] -= 1
                player_dist = abs(self.player_x - enemy['x'])
                if enemy['shoot_timer'] <= 0 and player_dist < 120:
                    dx = self.player_x - enemy['x']
                    dy = self.player_y - enemy['y']
                    dist = (dx**2 + dy**2)**0.5
                    if dist > 0:
                        self.bullets.append({
                            'x': enemy['x'] + 4, 'y': enemy['y'] + 4,
                            'vx': (dx / dist) * 2, 'vy': (dy / dist) * 2, 'color': 8, 'shooter': 'enemy', 'size': 2
                        })
                    enemy['shoot_timer'] = random.randint(100, 160)
            elif enemy['type'] == 'stream':
                enemy['x'] += enemy['speed']
                if self.start_protection_timer > 0 and (enemy['x'] < self.enemy_safe_zone or enemy['x'] < self.camera_x - 20):
                    self.enemies.remove(enemy)
            elif enemy['type'] == 'chase':
                dx = self.player_x - enemy['x']
                dy = self.player_y - enemy['y']
                dist = (dx**2 + dy**2)**0.5
                if dist > 0: enemy['x'] += (dx / dist) * enemy['speed']; enemy['y'] += (dy / dist) * enemy['speed']
                if self.start_protection_timer > 0 and (enemy['x'] < self.enemy_safe_zone or enemy['x'] < self.camera_x - 20):
                    self.enemies.remove(enemy)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['vx']
            bullet['y'] += bullet['vy']
            if (bullet['x'] < self.camera_x - 10 or bullet['x'] > self.camera_x + pyxel.width + 10 or
                bullet['y'] < -10 or bullet['y'] > pyxel.height + 10):
                self.bullets.remove(bullet)

    def check_collisions(self):
        if self.invincible_timer == 0:
            for enemy in self.enemies[:]:
                if abs(self.player_x - enemy['x']) < 6 and abs(self.player_y - enemy['y']) < 6:
                    self.player_health -= 1; self.invincible_timer = 120
                    if self.player_health <= 0: self.game_over = True
                    break
        if self.invincible_timer == 0:
            for bullet in self.bullets[:]:
                if bullet['shooter'] == 'enemy' and abs(self.player_x - bullet['x']) < 4 and abs(self.player_y - bullet['y']) < 4:
                    self.player_health -= 1
                    self.invincible_timer = 120
                    self.bullets.remove(bullet)
                    if self.player_health <= 0: self.game_over = True
                    break

        for bullet in self.bullets[:]:
            if bullet['shooter'] == 'player':
                for enemy in self.enemies[:]:
                    # AABB collision detection
                    if (bullet['x'] < enemy['x'] + 8 and
                        bullet['x'] + bullet['size'] > enemy['x'] and
                        bullet['y'] < enemy['y'] + 8 and
                        bullet['y'] + bullet['size'] > enemy['y']):
                        self.enemies.remove(enemy)
                        self.score += 50
                        self.enemy_kill_count += 1
                        if self.enemy_kill_count % 10 == 0:
                            self.upgrade_items.append({'x': enemy['x'], 'y': enemy['y'], 'w': 4, 'h': 4, 'color': 11})
                        
                        # If it's not a charge shot, remove the bullet
                        if self.weapon_type != 'charge':
                            self.bullets.remove(bullet)
                        break

        if self.invincible_timer == 0:
            for x, y, w, h, col in self.spikes:
                if (self.player_x + 7 > x and self.player_x < x + w -1 and self.player_y + 7 > y):
                    self.player_health -= 1; self.invincible_timer = 120
                    if self.player_health <= 0: self.game_over = True
                    break

        for coin in self.coins[:]:
            cx, cy, cw, ch, ccol = coin
            if (self.player_x + 8 > cx and self.player_x < cx + cw and
                self.player_y + 8 > cy and self.player_y < cy + ch):
                self.coins.remove(coin)
                self.score += 10
                self.collected_coins_for_heart += 1
                if self.collected_coins_for_heart >= 10:
                    self.hearts.append({'x': self.player_x, 'y': self.player_y, 'w': 8, 'h': 8, 'color': 8}) # Red heart
                    self.collected_coins_for_heart = 0

        for heart in self.hearts[:]:
            if (self.player_x + 8 > heart['x'] and self.player_x < heart['x'] + heart['w'] and
                self.player_y + 8 > heart['y'] and self.player_y < heart['y'] + heart['h']):
                self.hearts.remove(heart)
                self.player_health = min(self.player_health + 1, 3) # Max 3 health

        for item in self.upgrade_items[:]:
            if (self.player_x + 8 > item['x'] and self.player_x < item['x'] + item['w'] and
                self.player_y + 8 > item['y'] and self.player_y < item['y'] + item['h']):
                self.upgrade_items.remove(item)
                self.game_paused = True

        gx, gy, gw, gh, gcol = self.goal
        if (self.player_x + 8 > gx and self.player_x < gx + gw and self.player_y + 8 > gy and self.player_y < gy + gh):
            self.game_clear = True
        if self.player_y > pyxel.height: self.game_over = True

    def update_camera(self):
        self.camera_x = max(0, min(self.player_x - pyxel.width / 2, self.world_width - pyxel.width))

    def draw(self):
        pyxel.cls(0)
        
        if self.game_paused:
            self.draw_game_world()
            pyxel.rect(30, 50, 100, 60, 0)
            pyxel.text(40, 60, "SELECT WEAPON", 7)
            pyxel.text(50, 80, "SHOTGUN", 5 if self.weapon_selection == 0 else 7)
            pyxel.text(50, 90, "CHARGE SHOT", 5 if self.weapon_selection == 1 else 7)
            return

        if not self.game_started:
            pyxel.text(50, 40, "CAVE EXPLORER", 7)
            pyxel.text(65, 70, "START", pyxel.frame_count % 16)
            pyxel.text(40, 90, "Press SPACE to Play", 7)
            pyxel.text(20, 110, "Controls:", 7)
            pyxel.text(20, 120, "  Move: Left/Right Arrows", 7)
            pyxel.text(20, 130, "  Jump: Space (Double Jump)", 7)
            pyxel.text(20, 140, "  Shoot: F key", 7)
            pyxel.text(20, 150, "Goal: Reach the Yellow Post", 7)
        else:
            self.draw_game_world()
            pyxel.camera()
            pyxel.text(5, 5, f"Health: {self.player_health}", 7)
            pyxel.text(50, 5, f"Score: {self.score}", 7)
            pyxel.text(100, 5, f"Time: {self.time_left // 60}", 7)
            
            # Display Ammo
            current_ammo = 0
            if self.weapon_type == 'normal':
                current_ammo = self.normal_ammo
            elif self.weapon_type == 'shotgun':
                current_ammo = self.shotgun_ammo
            elif self.weapon_type == 'charge':
                current_ammo = self.charge_ammo
            pyxel.text(5, 15, f"Ammo: {current_ammo}", 7)

            if self.weapon_type == 'charge' and self.charge_level > 0:
                pyxel.rect(self.player_x - self.camera_x - 8, self.player_y - 10, (self.charge_level / 90) * 24, 2, 11)

            if self.game_over: pyxel.text(60, 70, "GAME OVER", 8); pyxel.text(40, 90, "Press R to Restart", 7)
            if self.game_clear: pyxel.text(60, 70, "GAME CLEAR!", 11); pyxel.text(40, 90, "Press R to Restart", 7)

    def draw_game_world(self):
        pyxel.camera(self.camera_x, 0)
        for x, y, w, h, col in self.stage: pyxel.rect(x, y, w, h, col)
        for x, y, w, h, col in self.spikes: pyxel.rect(x, y, w, h, col)
        for x, y, w, h, col in self.coins: pyxel.blt(x, y, 0, 0, 0, w, h, 0)
        for item in self.upgrade_items: pyxel.rect(item['x'], item['y'], item['w'], item['h'], item['color'])
        for heart in self.hearts: pyxel.rect(heart['x'], heart['y'], heart['w'], heart['h'], heart['color'])
        gx, gy, gw, gh, gcol = self.goal
        pyxel.rect(gx, gy, gw, gh, gcol)
        for bullet in self.bullets:
            pyxel.rect(bullet['x'], bullet['y'], bullet['size'], bullet['size'], bullet['color'])
        for enemy in self.enemies: pyxel.rect(enemy['x'], enemy['y'], 8, 8, enemy['color'])
        if self.invincible_timer % 10 < 5: pyxel.rect(self.player_x, self.player_y, 8, 8, 7)
            
    def restart(self):
        self.camera_x = 0
        self.player_x = self.player_start_x
        self.player_y = 120
        self.player_vy = 0
        self.player_health = 3
        self.jumps_left = 2
        self.invincible_timer = 0
        self.player_shoot_cooldown = 0
        self.player_direction = 1
        self.weapon_type = 'normal'
        self.charge_level = 0
        self.enemy_kill_count = 0
        self.upgrade_items = []
        self.game_paused = False
        self.coins.clear()
        self.bullets.clear()
        self.score = 0
        self.normal_ammo = self.max_normal_ammo
        self.shotgun_ammo = self.max_shotgun_ammo
        self.charge_ammo = self.max_charge_ammo
        self.distance_moved = 0
        self.last_player_x = self.player_start_x
        self.collected_coins_for_heart = 0
        self.hearts.clear()
        self.setup_level()
        self.enemy_spawn_timer = 0
        self.time_left = 180 * 60
        self.game_over = False
        self.game_clear = False
        self.game_started = False
        self.level_initialized = False

Game()