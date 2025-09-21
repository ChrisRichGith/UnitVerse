import uuid
import json
import os
from flask import Flask, render_template, redirect, url_for
import random

# --- DATA CLASSES ---
class Unit:
    def __init__(self, name, hp, attack, initiative, cost, xp=0, level=1, unit_id=None):
        self.id = unit_id if unit_id else str(uuid.uuid4())
        self.name = name
        self.level = level
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.initiative = initiative
        self.cost = cost
        self.xp = xp
        self.is_defeated = False
        self.position = None

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "level": self.level, "hp": self.hp,
            "max_hp": self.max_hp, "attack": self.attack, "initiative": self.initiative,
            "cost": self.cost, "xp": self.xp
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            unit_id=data.get("id"), name=data.get("name"), level=data.get("level", 1),
            hp=data.get("hp"), attack=data.get("attack"), initiative=data.get("initiative"),
            cost=data.get("cost"), xp=data.get("xp", 0)
        )

    def __repr__(self):
        return f"{self.name} (HP: {self.hp}/{self.max_hp})"

class Player:
    def __init__(self, name, is_ai=False):
        self.name = name
        self.is_ai = is_ai
        self.gold = 100
        self.units = []
        self.barracks = []
        self.board = {(r, c): None for r in range(3) for c in range(2)}

    def to_dict(self):
        return { "name": self.name, "barracks": [u.to_dict() for u in self.barracks] }

    @classmethod
    def from_dict(cls, data):
        player = cls(name=data.get("name"))
        player.barracks = [Unit.from_dict(u_data) for u_data in data.get("barracks", [])]
        return player

    def find_first_available_slot(self):
        for r in range(3):
            for c in range(2):
                if self.board.get((r,c)) is None: return (r,c)
        return None

    def place_unit(self, unit, position):
        if self.board.get(position) is None:
            unit.position = position
            self.board[position] = unit
            return True
        return False

class Game:
    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.players = [player1, player2]
        self.turn_order = []
        self.current_turn_index = 0
        self.game_state = "title_screen"
        self.shop_units = []
        self.round_count = 0
        self.combat_log = []
        self.winner = None
        self.survivors = []

    def start_combat(self):
        all_units = self.player1.units + self.player2.units
        self.turn_order = sorted(all_units, key=lambda u: u.initiative, reverse=True)
        self.game_state = "combat"
        self.current_turn_index = 0

    def get_current_attacker(self):
        if not self.turn_order: return None
        return self.turn_order[self.current_turn_index]

    def execute_turn(self):
        if self.game_state != "combat": return None
        attacker = self.get_current_attacker()
        if attacker.is_defeated: return None
        opponent_player = self.player2 if attacker in self.player1.units else self.player1
        target = None
        for r in range(3):
            for c in range(2):
                unit = opponent_player.board.get((r, c))
                if unit and not unit.is_defeated:
                    target = unit
                    break
            if target: break
        if target:
            damage = attacker.attack
            target.hp -= damage
            if target.hp <= 0:
                target.hp = 0
                target.is_defeated = True
            return {
                'type': 'attack', 'attacker_id': attacker.id, 'attacker_name': attacker.name,
                'target_id': target.id, 'target_name': target.name, 'damage': damage,
                'target_hp_after': target.hp, 'defeated': target.is_defeated
            }
        return {'type': 'info', 'message': f"{attacker.name} hat kein Ziel gefunden."}

    def check_game_over(self):
        p1_alive = any(not u.is_defeated for u in self.player1.units)
        p2_alive = any(not u.is_defeated for u in self.player2.units)
        return not p1_alive or not p2_alive

    def run_full_combat(self):
        self.start_combat()
        while self.round_count < 20:
            self.round_count += 1
            self.combat_log.append({'type': 'round', 'number': self.round_count})
            for i in range(len(self.turn_order)):
                self.current_turn_index = i
                action = self.execute_turn()
                if action: self.combat_log.append(action)
                if self.check_game_over():
                    self.game_state = "finished"
                    self.determine_winner()
                    return

        self.game_state = "finished"
        self.determine_winner()

    def _calculate_total_hp_percentage(self, player):
        if not player.units: return 0
        total_current_hp = sum(u.hp for u in player.units)
        total_max_hp = sum(u.max_hp for u in player.units)
        if total_max_hp == 0: return 0
        return (total_current_hp / total_max_hp) * 100

    def determine_winner(self):
        p1_alive = any(not u.is_defeated for u in self.player1.units)
        p2_alive = any(not u.is_defeated for u in self.player2.units)
        winner_obj = None
        if not p1_alive: winner_obj = self.player2
        elif not p2_alive: winner_obj = self.player1
        elif self.round_count >= 20:
            p1_hp_pct = self._calculate_total_hp_percentage(self.player1)
            p2_hp_pct = self._calculate_total_hp_percentage(self.player2)
            self.combat_log.append({'type': 'info', 'message': "Rundenlimit erreicht!"})
            if p1_hp_pct > p2_hp_pct: winner_obj = self.player1
            elif p2_hp_pct > p1_hp_pct: winner_obj = self.player2
            else: self.winner = "Unentschieden"
        if winner_obj:
            self.winner = {'name': winner_obj.name}

        # Award XP and identify survivors
        xp_to_award = 0
        if self.winner != "Unentschieden" and self.winner['name'] == self.player1.name:
            xp_to_award = 50 # Win
        else:
            xp_to_award = 10 # Loss or Draw

        for unit in self.player1.units:
            if not unit.is_defeated:
                unit.xp += xp_to_award
                self.survivors.append(unit)

# --- PERSISTENCE ---
SAVE_FILE = "player_data.json"
def save_data(player):
    with open(SAVE_FILE, "w") as f:
        json.dump(player.to_dict(), f, indent=4)

def load_data():
    if not os.path.exists(SAVE_FILE):
        return Player(name="Spieler 1")
    with open(SAVE_FILE, "r") as f:
        try: return Player.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError): return Player(name="Spieler 1")

# --- UNIT GENERATION ---
UNIT_NAMES = ["Goblin", "Orc", "Elf", "Dwarf", "Knight", "Mage", "Rogue", "Golem"]
def generate_random_unit():
    name = random.choice(UNIT_NAMES)
    hp = random.randint(50, 100)
    attack = random.randint(10, 25)
    initiative = random.randint(1, 10)
    cost = int((hp / 5) + attack + initiative)
    return Unit(name, hp, attack, initiative, cost)

# --- FLASK APP ---
app = Flask(__name__)
player1 = load_data()
game = Game(player1, Player(name="PC", is_ai=True))

@app.route('/')
def index():
    return render_template('index.html', game=game, player1=player1)

@app.route('/barracks')
def barracks():
    return render_template('barracks.html', player1=player1)

def pc_shopping_ai(player, shop_units):
    """A simple AI for the PC to buy and place units."""
    if not player.is_ai:
        return

    can_afford_something = True
    while can_afford_something:
        can_afford_something = False
        # Find the most expensive unit the AI can afford
        best_buy = None
        # Iterate over a copy of the list as we modify it
        for unit in list(shop_units):
            if player.gold >= unit.cost:
                if best_buy is None or unit.cost > best_buy.cost:
                    best_buy = unit

        if best_buy:
            can_afford_something = True
            # Buy the unit
            slot = player.find_first_available_slot()
            if slot:
                player.gold -= best_buy.cost
                player.units.append(best_buy)
                player.place_unit(best_buy, slot)
                shop_units.remove(best_buy)
            else:
                # No space left on board
                break
        else:
            # Can't afford anything that's left
            break

@app.route('/start_game', methods=['POST'])
def start_game():
    global game, player1
    player1.units = []
    player1.board = {(r, c): None for r in range(3) for c in range(2)}
    player1.gold = 100
    p2 = Player(name="PC", is_ai=True)
    game = Game(player1, p2)
    game.game_state = "preparation"
    game.shop_units = [generate_random_unit() for _ in range(5)]
    pc_shopping_ai(game.player2, game.shop_units)
    return redirect(url_for('index'))

@app.route('/buy_unit/<unit_id>', methods=['POST'])
def buy_unit(unit_id):
    """Handles the player buying a unit from the shop."""
    if game and game.game_state == "preparation":
        # Find the unit in the shop
        unit_to_buy = next((u for u in game.shop_units if u.id == unit_id), None)

        if unit_to_buy and player1.gold >= unit_to_buy.cost:
            # Check if there is space on the board
            slot = player1.find_first_available_slot()
            if slot:
                # Process purchase
                player1.gold -= unit_to_buy.cost
                player1.units.append(unit_to_buy)
                player1.place_unit(unit_to_buy, slot)
                game.shop_units.remove(unit_to_buy)

    return redirect(url_for('index'))

@app.route('/move_to_barracks/<unit_id>', methods=['POST'])
def move_to_barracks(unit_id):
    if game and game.game_state == "finished":
        survivor_to_move = next((u for u in game.survivors if u.id == unit_id), None)

        if survivor_to_move and len(player1.barracks) < 3:
            # Avoid duplicates
            if not any(u.id == survivor_to_move.id for u in player1.barracks):
                # Heal the unit before moving it to the barracks
                survivor_to_move.hp = survivor_to_move.max_hp
                player1.barracks.append(survivor_to_move)
                save_data(player1)
                # Remove from the list of available survivors on this screen
                game.survivors.remove(survivor_to_move)

    # Redirect back to the same results page
    return render_template('combat_replay.html', game=game, combat_log_json=game.combat_log)

@app.route('/start_combat', methods=['POST'])
def start_combat():
    if game and game.game_state == "preparation":
        game.run_full_combat()
        return render_template('combat_replay.html', game=game, combat_log_json=game.combat_log)
    return redirect(url_for('index'))

@app.route('/upgrade_unit/<unit_id>', methods=['POST'])
def upgrade_unit(unit_id):
    """Handles the unit upgrade logic."""
    unit_to_upgrade = next((u for u in player1.barracks if u.id == unit_id), None)

    if unit_to_upgrade:
        xp_needed = unit_to_upgrade.level * 100
        if unit_to_upgrade.xp >= xp_needed:
            # Consume XP and level up
            unit_to_upgrade.xp -= xp_needed
            unit_to_upgrade.level += 1

            # Randomly increase two attributes
            stats_to_upgrade = ["max_hp", "attack", "initiative"]
            upgrades = random.sample(stats_to_upgrade, 2)

            for stat in upgrades:
                if stat == "max_hp":
                    unit_to_upgrade.max_hp += 10
                    unit_to_upgrade.hp += 10 # Also heal to new max
                elif stat == "attack":
                    unit_to_upgrade.attack += 2
                elif stat == "initiative":
                    unit_to_upgrade.initiative += 1

            save_data(player1)

    return redirect(url_for('barracks'))

@app.route('/new_game', methods=['POST'])
def new_game():
    global game
    # We need to reload player data to get the latest barracks state
    player1 = load_data()
    game = Game(player1, Player(name="PC", is_ai=True))
    game.game_state = "title_screen"
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
