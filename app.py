import uuid
from flask import Flask, render_template, redirect, url_for

import random

# --- DATA CLASSES ---
class Unit:
    def __init__(self, name, hp, attack, initiative, cost):
        self.id = str(uuid.uuid4())
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.initiative = initiative
        self.cost = cost
        self.is_defeated = False
        self.position = None

    def __repr__(self):
        return f"{self.name} (HP: {self.hp}/{self.max_hp})"

class Player:
    def __init__(self, name, is_ai=False):
        self.name = name
        self.is_ai = is_ai
        self.gold = 100 # Starting gold
        self.units = []
        self.board = {(r, c): None for r in range(2) for c in range(3)} # 2 rows, 3 columns

    def place_unit(self, unit, position):
        if self.board.get(position) is None:
            unit.position = position
            self.board[position] = unit
            return True
        return False

    def find_first_available_slot(self):
        for r in range(2):
            for c in range(3):
                if self.board.get((r,c)) is None:
                    return (r,c)
        return None

class Game:
    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.players = [player1, player2]
        self.turn_order = []
        self.current_turn_index = 0
        self.game_state = "title_screen" # title_screen, preparation, combat, finished
        self.shop_units = []

    def start_combat(self):
        all_units = [u for p in self.players for u in p.units]
        self.turn_order = sorted(all_units, key=lambda u: u.initiative, reverse=True)
        self.game_state = "combat"
        self.current_turn_index = 0

    def get_current_attacker(self):
        if not self.turn_order: return None
        return self.turn_order[self.current_turn_index]

    def execute_turn(self):
        """Executes a single, simple attack turn."""
        if self.game_state != "combat":
            return

        attacker = self.get_current_attacker()
        if attacker.is_defeated:
            # Skip defeated units
            self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
            return

        # Determine opponent
        attacking_player = self.player1 if attacker in self.player1.board.values() else self.player2
        opponent_player = self.player2 if attacking_player is self.player1 else self.player1

        # Find first available target, respecting rows (front-row protection)
        target = None
        for r in range(2): # Iterate rows 0, 1
            for c in range(3): # Iterate columns 0, 1, 2
                unit = opponent_player.board.get((r, c))
                if unit and not unit.is_defeated:
                    target = unit
                    break # Found a target in this row, stop searching columns
            if target:
                break # Found a target in this row, stop searching rows

        if target:
            # Apply damage
            target.hp -= attacker.attack
            if target.hp <= 0:
                target.hp = 0
                target.is_defeated = True

        # Check for game over
        self.check_game_over()

        # Advance to next turn
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)

    def check_game_over(self):
        """Checks if all units of a player are defeated."""
        p1_all_defeated = all(u.is_defeated for u in self.player1.board.values() if u)
        p2_all_defeated = all(u.is_defeated for u in self.player2.board.values() if u)
        if p1_all_defeated or p2_all_defeated:
            self.game_state = "finished"

# --- UNIT GENERATION ---
UNIT_NAMES = ["Goblin", "Orc", "Elf", "Dwarf", "Knight", "Mage", "Rogue", "Golem"]

def generate_random_unit():
    """Generates a new random unit with balanced stats and a cost."""
    name = random.choice(UNIT_NAMES)
    hp = random.randint(50, 100)
    attack = random.randint(10, 25)
    initiative = random.randint(1, 10)

    # Cost is a simple sum of stats
    cost = int((hp / 5) + attack + initiative)

    return Unit(name, hp, attack, initiative, cost)

# --- GAME SETUP ---
def setup_game():
    """Creates a new, empty game, ready for the title screen."""
    p1 = Player(name="Spieler 1")
    p2 = Player(name="PC", is_ai=True)
    new_game = Game(p1, p2)
    return new_game

# --- FLASK APP ---
app = Flask(__name__)
game = None # Global game state

@app.route('/')
def index():
    global game
    if game is None:
        game = setup_game()
    return render_template('index.html', game=game)

@app.route('/next_turn', methods=['POST'])
def next_turn():
    if game:
        game.execute_turn()
    return redirect(url_for('index'))

def pc_shopping_ai(player, shop_units):
    """A simple AI for the PC to buy and place units."""
    if not player.is_ai:
        return

    can_afford_something = True
    while can_afford_something:
        can_afford_something = False
        # Find the most expensive unit the AI can afford
        best_buy = None
        for unit in shop_units:
            if player.gold >= unit.cost:
                if best_buy is None or unit.cost > best_buy.cost:
                    best_buy = unit
                    can_afford_something = True

        if best_buy:
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

@app.route('/start_game', methods=['POST'])
def start_game():
    """Prepares the game for the shopping phase."""
    global game
    game = setup_game() # Reset the game to a clean state
    game.game_state = "preparation"
    # Populate the shop with 5 random units
    game.shop_units = [generate_random_unit() for _ in range(5)]

    # PC opponent does its shopping
    pc_shopping_ai(game.player2, game.shop_units)

    return redirect(url_for('index'))

@app.route('/buy_unit/<unit_id>', methods=['POST'])
def buy_unit(unit_id):
    """Handles the player buying a unit from the shop."""
    if game and game.game_state == "preparation":
        player = game.player1

        # Find the unit in the shop
        unit_to_buy = next((u for u in game.shop_units if u.id == unit_id), None)

        if unit_to_buy and player.gold >= unit_to_buy.cost:
            # Check if there is space on the board
            slot = player.find_first_available_slot()
            if slot:
                # Process purchase
                player.gold -= unit_to_buy.cost
                player.units.append(unit_to_buy)
                player.place_unit(unit_to_buy, slot)
                game.shop_units.remove(unit_to_buy)

    return redirect(url_for('index'))

@app.route('/start_combat', methods=['POST'])
def start_combat():
    """Transitions the game from preparation to combat."""
    if game and game.game_state == "preparation":
        game.start_combat()
    return redirect(url_for('index'))

@app.route('/new_game', methods=['POST'])
def new_game():
    global game
    game = setup_game()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
