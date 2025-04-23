import itertools
import os
import time
import platform
from collections import Counter
from tinydb import TinyDB

# Ensure the directory exists
if not os.path.exists(os.path.join(os.path.expanduser("~"), "Documents", "YahtzeeCalc")):
    os.makedirs(os.path.join(os.path.expanduser("~"), "Documents", "YahtzeeCalc"))
    
# Path to the roll data file
ROLL_DATA_FILE = os.path.join(os.path.join(os.path.join(os.path.expanduser("~"), "Documents"), "YahtzeeCalc"), "roll_data.json")

# Initialize TinyDB
db = TinyDB(ROLL_DATA_FILE)
rolls_table = db.table("rolls")

# Yahtzee categories
CATEGORIES = {
    "ones": lambda dice: sum(d for d in dice if d == 1),
    "twos": lambda dice: sum(d for d in dice if d == 2),
    "threes": lambda dice: sum(d for d in dice if d == 3),
    "fours": lambda dice: sum(d for d in dice if d == 4),
    "fives": lambda dice: sum(d for d in dice if d == 5),
    "sixes": lambda dice: sum(d for d in dice if d == 6),
    "three_of_a_kind": lambda dice: sum(dice) if any(v >= 3 for v in Counter(dice).values()) else 0,
    "four_of_a_kind": lambda dice: sum(dice) if any(v >= 4 for v in Counter(dice).values()) else 0,
    "full_house": lambda dice: 25 if sorted(Counter(dice).values()) == [2, 3] else 0,
    "small_straight": lambda dice: 30 if len(set(dice).intersection({1, 2, 3, 4})) == 4 or len(set(dice).intersection({2, 3, 4, 5})) == 4 or len(set(dice).intersection({3, 4, 5, 6})) == 4 else 0,
    "large_straight": lambda dice: 40 if set(dice) in [{1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}] else 0,
    "yahtzee": lambda dice: 50 if len(set(dice)) == 1 else 0,
    "chance": lambda dice: sum(dice),
}

def clear():
    if platform.system() == "Windows":
        os.system('cls')
    elif platform.system() == "Linux":
        os.system('clear')
    elif platform.system() == "Darwin":
        os.system('clear')
    else:
        print("Unsupported OS. Unable to clear the screen.")
        time.sleep(2)

def load_roll_data():
    """Load roll data from TinyDB."""
    roll_data = Counter()
    for entry in rolls_table.all():
        roll_key = tuple(entry["roll"])
        roll_data[roll_key] = entry["count"]
    return roll_data

def save_roll_data(roll_data):
    """Save roll data to TinyDB."""
    rolls_table.truncate()  # Clear the table before saving
    for roll_key, count in roll_data.items():
        rolls_table.insert({"roll": list(roll_key), "count": count})

def calculate_scores(dice, played_categories):
    """Calculate scores for all categories based on the current dice roll, excluding played categories."""
    return {category: func(dice) for category, func in CATEGORIES.items() if category not in played_categories}

def recommend_rerolls(dice, roll_data, max_rerolls=3):
    # Count frequency of individual numbers from roll_data
    number_frequency = Counter()
    for roll, freq in roll_data.items():
        for num in roll:
            number_frequency[num] += freq

    if number_frequency:
        most_common_numbers = {num for num, _ in number_frequency.most_common(2)}
    else:
        most_common_numbers = set()

    expected_values = {}

    # Allow for 1 or 2 rerolls
    for i in range(1, max_rerolls + 1):
        for reroll_indices in itertools.combinations(range(5), i):
            reroll_values = list(itertools.product(range(1, 7), repeat=len(reroll_indices)))

            scores = []
            for new_values in reroll_values:
                simulated_dice = dice[:]
                for index, value in zip(reroll_indices, new_values):
                    simulated_dice[index] = value

                roll_key = tuple(sorted(simulated_dice))
                weight = roll_data.get(roll_key, 1)

                # Bias toward keeping frequent numbers
                bonus = sum(1 for d in simulated_dice if d in most_common_numbers)
                adjusted_score = max(calculate_scores(simulated_dice, set()).values()) * weight * (1 + 0.1 * bonus)
                scores.append(adjusted_score)

            expected_values[reroll_indices] = sum(scores) / len(scores)

    if not expected_values:
        return [], max(calculate_scores(dice, set()).values())

    best_reroll_indices = max(expected_values, key=expected_values.get)
    best_reroll_values = [dice[i] for i in best_reroll_indices]
    return best_reroll_values, expected_values[best_reroll_indices]


def main():
    print("Welcome to YahtzeeCalc!")
    time.sleep(3)
    roll_count = 0  # Initialize reroll count for a turn
    played_categories = set()  # Keep track of categories already used in the game

    # Load roll data
    roll_data = load_roll_data()

    while True:
        clear()
        # Get user input
        input_dice = input("Enter your dice roll (e.g., 1 2 3 4 5): \n").strip()
        try:
            dice = list(map(int, input_dice.split()))
            if len(dice) != 5 or any(d < 1 or d > 6 for d in dice):
                raise ValueError
        except ValueError:
            clear()
            print("Invalid input. Please enter five numbers between 1 and 6.")
            time.sleep(3)
            continue

        while roll_count < 3:  # Allow up to 2 rerolls
            # Recommend rerolls
            reroll_indices, expected_reroll_value = recommend_rerolls(dice, roll_data, max_rerolls=2 - roll_count)

            # Calculate scores, excluding played categories
            scores = calculate_scores(dice, played_categories)
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]
            formatted_category = best_category.replace("_", " ")

            # Decide whether to reroll or score
            if best_score >= expected_reroll_value:
                print(f"\nRecommended action: Score in '{formatted_category}' for {best_score} points.")
                time.sleep(3)
                played_categories.add(best_category)  # Mark the category as played
                roll_count = 0  # Reset reroll count after scoring
                break
            else:
                if roll_count <= 3:
                    print(f"\nRecommended action: Reroll dice with {reroll_indices} (Expected value: {expected_reroll_value:.2f}).")
                    time.sleep(3)
                    roll_count += 1  # Increment reroll count
                    break  # Exit loop to simulate reroll (user would reroll and re-enter dice)

        if roll_count >= 3:
            # Reroll limit reached, suggest the best scoring action
            scores = calculate_scores(dice, played_categories)
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]
            formatted_category = best_category.replace("_", " ")
            print(f"\nReroll limit reached. Recommended action: Score in '{formatted_category}' for {best_score} points.")
            time.sleep(3)
            played_categories.add(best_category)  # Mark the category as played
            roll_count = 0  # Reset reroll count after forced scoring

        # Update roll data
        roll_key = tuple(sorted(dice))
        roll_data[roll_key] += 1

        # Save the updated roll data to the database
        save_roll_data(roll_data)
        time.sleep(3)
        clear()

if __name__ == "__main__":
    main()