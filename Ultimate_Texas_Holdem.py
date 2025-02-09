import numpy as np
import random
from collections import Counter
from itertools import combinations

class Card:
    values = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    suits = ['h','d','c','s']

    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
    
    def __str__(self):
        return self.value + self.suit

class Deck:
    def __init__(self):
        self.cards = [Card(value, suit) for value in Card.values for suit in Card.suits]
    
    def __iter__(self):
        return iter(self.cards)

    def __str__(self):
        return ', '.join(str(card) for card in self.cards)

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_card(self):
        if not self.cards:
            raise ValueError("No Cards Exist")
        return self.cards.pop()

    def reset(self):
        'resets deck to unshuffled state'
        self.__init__()

class Hand:
    def __init__(self, cards):
        self.cards = cards
        self.strength = strength
    
    def __str__(self):
        return ', '.join(str(card) for card in self.cards)

    def evaluate_hand(self):
        hand_ranking = ['AsKsQsJsTs','AhKhQhJhTh']
        
class Player:
    def __init__(self, balance, hand):
        self.balance = balance
        self.hand = hand
        self.current_decision = None
    
    def make_decision(self, decision):
        self.current_decision = decision
        
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




### STAND ALONE EVALUATOR FUNCTIONS

def highest_card(cards):
    values = "23456789TJQKA" 
    highest_card = max(cards, key=lambda card: values.index(card[0]))
    return highest_card[0]

def sum_of_kickers(hand):
    values = [c[0] for c in hand]
    counts = Counter(values)
    kickers = [v for v in values if counts[v] == 1]
    return sum(card_vals(kickers))

def num_of_kind(cards):
    return Counter(c[0] for c in cards)

def count_pairs(cards):
    return sum(i > 1 for i in num_of_kind(cards).values())

def largest_pair(cards):
    return max(num_of_kind(cards).values())

def is_straight(cards):
    values = [c[0] for c in cards]
    index = "A23456789TJQKA"["K" in values:].index
    indices = sorted(index(v) for v in values)
    return all(x == y for x, y in enumerate(indices, indices[0]))

def is_flush(cards):
    suit_pop = Counter(c[1] for c in cards)
    return any(s > 4 for s in suit_pop.values())

def straight_sort(cards):
    values = [c[0] for c in cards]
    index = "A23456789TJQKA"["K" in values:].index
    return sorted(cards, key=lambda x:index(x[0]), reverse=True)

def flush_sort(cards):
    suit_pop = Counter(c[1] for c in cards)
    return sorted(cards, key=lambda x: suit_pop[x[1]], reverse=True)

def pair_sort(cards):
    num = num_of_kind(cards)
    return sorted(cards, key=lambda x: num[x[0]], reverse=True)

def card_vals(cards):
    """Converts card values to corresponding integers for comparison."""
    value_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, 
                 "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return [value_map[card[0]] for card in cards]

def first_card(cards):
    return cards[0][0]

def second_card(cards):
    return cards[1][0]

def third_card(cards):
    return cards[2][0]

def fourth_card(cards):
    return cards[3][0]

def fifth_card(cards):
    return cards[4][0]

def score_hand(cards):
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
        

    return hand_score, card_vals(cards), cards, hand_description

def best_hand(cards):
    all_hands = list(combinations(cards, 5)) 
    scored_hands = [(score_hand(hand)[0], score_hand(hand)[2]) for hand in all_hands] 

    best_score = max(scored_hands, key=lambda x: x[0])[0] 

    best_hands = [hand for score, hand in scored_hands if score == best_score]  

    best_hands_sorted = sorted(best_hands, key=lambda hand: sum_of_kickers(hand), reverse=True) 


    best_hand = best_hands_sorted[0]
    hand_score, _, _, hand_description = score_hand(best_hand) 

    return best_hand, hand_description



hand = ['As', 'Ad']
board = ['Js', 'Td', '6h', '4s', 'Qs']
print(*best_hand(hand+board))






# deck = Deck()
# deck.shuffle()
# print(deck)
# for card in deck:
#     card = deck.deal_card()
#     print(card)
