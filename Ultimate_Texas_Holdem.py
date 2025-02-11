import numpy as np
import random
from collections import Counter
from itertools import combinations

## TO DO:
# https://www.youtube.com/watch?v=mENr3b4IlqQ&ab_channel=StackWild


class Card:
    values = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
    suits = ['h','d','c','s']

    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
    
    def __str__(self):
        return f"{self.value}{self.suit}"

class Deck:
    def __init__(self):
        self.cards = [Card(value, suit) for value in Card.values for suit in Card.suits]
    
    def __iter__(self):
        return iter(self.cards)

    def __str__(self):
        return ', '.join(str(card) for card in self.cards)

    def shuffle(self):
        n = len(self.cards)
        for i in range(n - 1, 0, -1):
            j = random.randint(0, i)
            self.cards[i], self.cards[j] = self.cards[j], self.cards[i]
        return self

    def deal_card(self):
        if not self.cards:
            raise ValueError("No Cards Exist")
        return self.cards.pop()

class Board:
    def __init__(self, cards):
        self.cards = cards

    def append(self, card):
        self.cards.append(card)

    def __str__(self):
        return f"[{', '.join(str(card) for card in self.cards)}]"
    
class Hand:
    def __init__(self, cards):
        self.cards = cards

    def append(self, card):
        self.cards.append(card)
    
    def __str__(self):
        return f"[{', '.join(str(card) for card in self.cards)}]"
    
    def evaluate_hand(self, hand, board):
        hand_score = best_hand(hand+board)[0]
        return hand_score
        
class Player:
    def __init__(self, balance, hand, bets):
        self.balance = balance
        self.hand = hand
        self.bets = bets
        self.current_decision = None
    
    def make_decision(self, decision):
        self.current_decision = decision

class Dealer:
    def __init__(self, hand):
        self.hand = hand
    
    def qualifies(self, hand, board):
        return evaluate_hand(hand, board) >= 1

class Bets:
    def __init__(self, ante = 0, blind = 0, trips = 0, progressive = 0):
        self.ante = ante
        self.blind = blind
        self.trips = trips
        self.progressive = progressive
    
    def __str__(self):
        return f"Bets - Ante/Blind: {self.ante}, Trips: {self.trips}, Progressive: {self.progressive}"

class Decision:
    def __init__(self, action=None, amount=0):
        self.action = action  
        self.amount = amount

    def bet(self, amount):
        self.action = 'bet'
        self.amount = amount

    def check(self):
        self.action = 'check'
       
    def fold(self):
        self.action = 'fold'

    def __str__(self):
        if self.action == 'bet':
            return f"Action: {self.action}, Amount: {self.amount}"
        else:
            return f"Action: {self.action}"

class Strategy:
    def __init__(self):
        self.strategy = strategy

class Game:
    def __init__(self):
        self.round = round




### Main Hand Scoring Functions

def compare_hands(player_hand, dealer_hand, board):

    all_cards = player_hand.cards + dealer_hand.cards + board.cards

    if not is_valid_deck(all_cards)[0]:
        raise ValueError(f"Invalid cards detected: duplicates or non-existent card: '{is_valid_deck(all_cards)[1]}'")

    player_result = best_hand(player_hand.cards + board.cards)
    dealer_result = best_hand(dealer_hand.cards + board.cards)

    player_score, player_best_hand, player_description = player_result
    dealer_score, dealer_best_hand, dealer_description = dealer_result

    player_summary = f"Player: {player_best_hand}: {player_description}"
    dealer_summary = f"Dealer: {dealer_best_hand}: {dealer_description}"

    if player_score > dealer_score:
        winner = "Player"
    elif player_score < dealer_score:
        winner = "Dealer"
    
    else:
        for player_card, dealer_card in zip(player_best_hand.cards, dealer_best_hand.cards):

            player_card_value = card_vals([player_card])[0]
            dealer_card_value = card_vals([dealer_card])[0]

            if player_card_value > dealer_card_value:
                winner = "Player"
                break
            elif player_card_value < dealer_card_value:
                winner = "Dealer"
                break
            else:
                winner = "Tie"
    
    player_best_hand_str = [str(card) for card in player_best_hand.cards] 
    dealer_best_hand_str = [str(card) for card in dealer_best_hand.cards]

    # Compare hands currently returns strings of descriptions and of player and dealer hands rather than the card objects themselves
    # This is for testing/display purposes only and if we need to use this output elsewhere as an input it should keep convention as an object  

    return winner, 'Wins!',' Player: ', player_best_hand_str, player_description, ' Dealer: ', dealer_best_hand_str, dealer_description

def best_hand(cards):
    all_hands = list(combinations(cards, 5))
    all_hands = [Hand(list(hand)) for hand in all_hands]

    hand_scores = [score_hand(hand)[0] for hand in all_hands]
    hand_results = [score_hand(hand)[2] for hand in all_hands]

    hands_sorted_by_score = list(zip(hand_scores, hand_results))

    best_score = max(hands_sorted_by_score, key=lambda x: x[0])[0]
    best_hands = [hand for score, hand in hands_sorted_by_score if score == best_score]
    best_hands_sorted_by_kicker_sum = sorted(best_hands, key=lambda hand: sum_of_kickers(Hand(hand)), reverse=True)

    best_hand = Hand(best_hands_sorted_by_kicker_sum[0])
    hand_score, _, _, hand_description = score_hand(best_hand)

    return hand_score, best_hand, hand_description



def score_hand(hand):
    cards = hand.cards

    pairs = count_pairs(cards)
    largest = largest_pair(cards)

    straight = is_straight(cards)
    flush = is_flush(cards)

    cards = straight_sort(cards)
    hand_score = 0
    hand_description = ""

    if flush and straight:
        hand_score, cards = 8, flush_sort(cards)
        hand_description = f"{first_card(cards)} High Straight Flush"
    elif largest == 4:
        hand_score, cards = 7, pair_sort(cards)
        hand_description = f"Quad {first_card(cards)}s {fifth_card(cards)} kicker"
    elif pairs == 2 and largest == 3:
        hand_score, cards = 6, pair_sort(cards)
        hand_description= f"Full House: {first_card(cards)}s over {fifth_card(cards)}s"
    elif flush:
        hand_score, cards = 5, flush_sort(cards)
        hand_description = f"{first_card(cards)} High Flush"

    elif straight:
        hand_score = 4
        hand_description = f"{first_card(cards)} High Straight"
    elif largest == 3:
        hand_score, cards = 3, pair_sort(cards)
        hand_description = f"Trip {first_card(cards)}s {fourth_card(cards)} kicker"
    else:
        hand_score, cards = pairs, pair_sort(cards)
        if hand_score == 2:
            hand_description = f"Two-Pair: {first_card(cards)}s and {third_card(cards)}s {fifth_card(cards)} kicker"
        elif hand_score == 1:
            hand_description = f"Pair of {first_card(cards)}s {third_card(cards)} kicker"
        else:
            hand_description = f"{first_card(cards)} High"
        

    return hand_score, card_vals(cards), cards, hand_description




#### Helper Evaluator Functions 

def create_card(card_str):
    value = card_str[:-1]  # All but last character for value
    suit = card_str[-1]    # Last character for suit
    return Card(value, suit)


def is_valid_deck(cards):
    valid_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    valid_suits = ['h', 'd', 'c', 's']

    seen_cards = set()
    for card in cards:
        card_str = str(card)  
        if card_str in seen_cards:
            return False, card 

        seen_cards.add(card_str)
        
        if card.value not in valid_ranks or card.suit not in valid_suits:
            return False, card
    return True, card


def highest_card(cards):
    values = "23456789TJQKA" 
    highest_card = max(cards, key=lambda card: values.index(card.value))
    return highest_card.value

def sum_of_kickers(hand):
    values = [c.value for c in hand.cards]
    counts = Counter(values)
    kickers = [c for c in hand.cards if counts[c.value] == 1]
    return sum(card_vals(kickers))

def num_of_kind(cards):
    return Counter(c.value for c in cards)

def count_pairs(cards):
    return sum(i > 1 for i in num_of_kind(cards).values())

def largest_pair(cards):
    return max(num_of_kind(cards).values())

def is_straight(cards):
    values = [c.value for c in cards]
    index = "A23456789TJQKA"["K" in values:].index
    indices = sorted(index(v) for v in values)
    return all(x == y for x, y in enumerate(indices, indices[0]))

def is_flush(cards):
    suit_pop = Counter(c.suit for c in cards)
    return any(s > 4 for s in suit_pop.values())

def straight_sort(cards):
    values = [c.value for c in cards]
    index = "A23456789TJQKA"["K" in values:].index
    return sorted(cards, key=lambda x:index(x.value), reverse=True)

def flush_sort(cards):
    suit_pop = Counter(c.suit for c in cards)
    return sorted(cards, key=lambda x: suit_pop[x.suit], reverse=True)

def pair_sort(cards):
    num = num_of_kind(cards)  
    return sorted(cards, key=lambda x: (num[x.value], card_vals([x])[0]), reverse=True)


def card_vals(cards):
    """Converts card values to corresponding integers for comparison."""
    value_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, 
                 "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return [value_map[card.value] for card in cards]

def first_card(cards):
    return cards[0].value

def second_card(cards):
    return cards[1].value

def third_card(cards):
    return cards[2].value

def fourth_card(cards):
    return cards[3].value

def fifth_card(cards):
    return cards[4].value

# player_cards = ['As', 'Kd']
# dealer_cards = ['Ad', 'Kc']
# board_cards = ['Jd', 'Qd', '9h', 'Ts', '3h']

# player_hand = Hand([create_card(card) for card in player_cards])
# dealer_hand = Hand([create_card(card) for card in dealer_cards])
# board = [create_card(card) for card in board_cards]

deck = Deck()
deck.shuffle()

player_hand = Hand([])
dealer_hand = Hand([])
board = Board([])

for i in range(9):  
    card = deck.deal_card()
    if i > 3:  
        board.append(card)
    elif i % 2 == 0: 
        player_hand.append(card)
    elif i % 2 == 1: 
        dealer_hand.append(card)

print(f"Player: {player_hand}, Dealer: {dealer_hand}, Board: {board}")
print(*compare_hands(player_hand, dealer_hand, board))

# hand = [Card('2','c'), Card('8','h'), Card('J','s'), Card('2','d'), Card('K','h')]
# sorted_hand = pair_sort(hand)
# print(f"{sorted_hand}")  # Output the sorted list of cards

