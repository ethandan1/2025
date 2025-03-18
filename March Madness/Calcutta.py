import numpy as np
import pandas as pd
import json
import re
from termcolor import colored
import math
from scipy.optimize import minimize
import os
import csv

# TO Do:
# 1. Change growth method to have a better estimate
# 3. Decide how to weigh the initial pot with the new estimated pot, and slowly reduce the weighting of the initial pot
# 4.         do this by using the percentage fair share / 100 done so far in the auction to weight the new estimate
# 4 years of auction data, let's synthesize that into % underpriced by pick # and by seed # and graph those as well         


class CalcuttaAuction:
    def __init__(self, champ_odds, second_place_odds, final_four_odds, elite_eight_odds, sweet_sixteen_odds, round_32_odds, fanduel_champ_odds, fanduel_second_place_odds, fanduel_final_four_odds, fanduel_elite_eight_odds, fanduel_sweet_sixteen_odds, fanduel_round_32_odds, KenPom_champ_odds, KenPom_second_place_odds, KenPom_final_four_odds, KenPom_elite_eight_odds, KenPom_sweet_sixteen_odds, KenPom_round_32_odds, round_32_vig, team_seeds, auction_results, auction_relative):
        """
        Initialize the auction system.
        :param champ_odds: Dictionary of American odds for teams to win the championship.
        :param second_place_odds: Dictionary of American odds for teams to reach the championship game.
        :param final_four_odds: Dictionary of American odds for teams to reach the Final Four.
        :param elite_eight_odds: Dictionary of American odds for teams to reach the Elite Eight.
        :param sweet_sixteen_odds: Dictionary of American odds for teams to reach the Sweet Sixteen.
        :param round_32_odds: Dictionary of American odds for teams to reach the Round of 32.
        :param round_32_vig: The vig adjustment for Round of 32 odds.
        :param team_seeds: Dictionary mapping teams to their seed numbers.
        :param odds_type: The type of odds used in the input data (e.g., "american", "percentage", "both").
        """
        self.estimated_pot = 200000
        self.original_pot = self.estimated_pot  # Store original estimate
        self.last_pot = self.estimated_pot  # Store last round's estimate
        self.auction_results = auction_results
        self.auction_relative = auction_relative
        self.team_seeds = team_seeds
        
        # Convert odds and remove vig
        self.champ_odds = self.devig_odds(champ_odds, expected_total=1, odds_type="Percentage")
        self.second_place_odds = self.devig_odds(second_place_odds, expected_total=2, odds_type="Percentage")
        self.final_four_odds = self.devig_odds(final_four_odds, expected_total=4, odds_type="Percentage")
        self.elite_eight_odds = self.devig_odds(elite_eight_odds, expected_total=8, odds_type="Percentage")
        self.sweet_sixteen_odds = self.devig_odds(sweet_sixteen_odds, expected_total=16, odds_type="Percentage")
        self.round_32_odds = self.devig_odds(round_32_odds, expected_total=32, odds_type="Percentage")
        
        self.fanduel_champ_odds = self.devig_odds(fanduel_champ_odds, expected_total=1, odds_type="American")
        self.fanduel_second_place_odds = self.devig_odds(fanduel_second_place_odds, expected_total = 2, odds_type = "American")
        self.fanduel_final_four_odds = self.devig_odds(fanduel_final_four_odds, expected_total=4, odds_type="American")
        self.fanduel_elite_eight_odds =  self.devig_odds(fanduel_elite_eight_odds, expected_total=8, odds_type="American")
        self.fanduel_sweet_sixteen_odds = self.devig_odds(fanduel_sweet_sixteen_odds, expected_total=16, odds_type="American") 
        self.fanduel_round_32_odds = self.devig_odds(fanduel_round_32_odds, expected_total=32, odds_type="American")

        self.KenPom_champ_odds = self.devig_odds(KenPom_champ_odds, expected_total = 1, odds_type = "Percentage")
        self.KenPom_second_place_odds = self.devig_odds(KenPom_second_place_odds, expected_total = 2, odds_type = "Percentage")
        self.KenPom_final_four_odds = self.devig_odds(KenPom_final_four_odds, expected_total = 4, odds_type = "Percentage")
        self.KenPom_elite_eight_odds = self.devig_odds(KenPom_elite_eight_odds, expected_total = 8, odds_type = "Percentage")
        self.KenPom_sweet_sixteen_odds = self.devig_odds(KenPom_sweet_sixteen_odds, expected_total = 16, odds_type = "Percentage")
        self.KenPom_round_32_odds = self.devig_odds(KenPom_round_32_odds, expected_total = 32, odds_type = "Percentage")

        # Generate team probabilities
        self.odds_dict = self.generate_team_odds(Fanduel = True)

        print(f"Initial estimated pot: ${self.estimated_pot:,.0f}")
        print("")

    def devig_odds(self, odds_dict, expected_total, odds_type):
        if odds_type.lower() == "percentage":
            total_prob = sum(odds_dict.values())/100
            adj_factor = total_prob / expected_total
            return {team: odds/100 / adj_factor for team, odds in odds_dict.items()}
        else:

            """Convert American odds to probabilities and remove vig based on expected number of teams per round."""
            probabilities = {team: self.american_to_prob(odds, "American") for team, odds in odds_dict.items()}
            total_prob = sum(probabilities.values())
            
            adj_factor = total_prob / expected_total  # Adjusts based on # of teams that should get here
            return {team: prob / adj_factor for team, prob in probabilities.items()}
    
    def american_to_prob(self, odds, odds_type):
        if odds_type.lower() == "percentage":
            return odds / 100
        else:
            return (abs(odds) / (abs(odds) + 100))*100 if odds < 0 else (100 / (odds + 100))*100

    def generate_team_odds(self, Fanduel):
        odds_dict = {}
        output_file="team_odds.csv"
        for team in self.champ_odds:
            if Fanduel:
                odds_dict[team] = [
                    (self.fanduel_round_32_odds[team] * 0.4 + self.KenPom_round_32_odds[team] * 0.4 + self.round_32_odds[team] * 0.2),
                    (self.fanduel_sweet_sixteen_odds[team] * 0.4 + self.KenPom_sweet_sixteen_odds[team] * 0.4 + self.sweet_sixteen_odds[team] * 0.2),
                    (self.fanduel_elite_eight_odds[team] * 0.4 + self.KenPom_elite_eight_odds[team] * 0.4 + self.elite_eight_odds[team] * 0.2),
                    (self.fanduel_final_four_odds[team] * 0.4 + self.KenPom_final_four_odds[team] * 0.4 + self.final_four_odds[team] * 0.2),
                    (self.fanduel_second_place_odds[team] * 0.4 + self.KenPom_second_place_odds[team] * 0.4 + self.second_place_odds[team] * 0.2),
                    (self.fanduel_champ_odds[team] * 0.4 + self.KenPom_champ_odds[team] * 0.4 + self.champ_odds[team] * 0.2)
                ]
            else:
                odds_dict[team] = [
                    self.round_32_odds[team],
                    self.sweet_sixteen_odds[team],
                    self.elite_eight_odds[team],
                    self.final_four_odds[team],
                    self.second_place_odds[team],
                    self.champ_odds[team]
                ]
        
        sorted_teams = sorted(odds_dict.items(), key=lambda x: x[1][5], reverse=True)
        if Fanduel:
            print("Fanduel 40%, KenPom 40%, 538 20%")

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Team', 'Rd 32', 'Sweet 16', 'Elite 8', 'Final 4', 'Title Game', 'Champion'])
            for team, odds in sorted_teams:
                odds = [round(odd * 100, 2) for odd in odds]
                writer.writerow([team] + odds)

        print(f"Data Checks:")
        print(f"Sum of round 32 odds: {round(sum([odds[0] for odds in odds_dict.values()]),4)}")
        print(f"Sum of sweet sixteen odds: {round(sum([odds[1] for odds in odds_dict.values()]),4)}")
        print(f"Sum of elite eight odds: {round(sum([odds[2] for odds in odds_dict.values()]),4)}")
        print(f"Sum of final four odds: {round(sum([odds[3] for odds in odds_dict.values()]),4)}")
        print(f"Sum of second place odds: {round(sum([odds[4] for odds in odds_dict.values()]),4)}")
        print(f"Sum of championship odds: {round(sum([odds[5] for odds in odds_dict.values()]),4)}")

        return odds_dict
    
    def calculate_fair_value(self):
        adjusted_pot = self.estimated_pot * .97

        seed_bonus_counter = 0

        payout_percentages = [0.0075, 0.015, 0.0225, 0.035, 0.06, 0.08] #incremental values, since multiplying by probability for team to reach this round and summing
        fair_values = {}
        fair_shares = {}
        for team, odds in self.odds_dict.items():
            if team not in self.team_seeds:
                print(f"Warning: No seed found for team {team}")
            else:
                seed = self.team_seeds[team]
                seed_str = str(seed)

                team_fair_share = 0.97 * sum(prob * pct for prob, pct in zip(odds, payout_percentages))

                if len(self.auction_results) == 0:
                    fair_values[f"{team} ({seed_str})"] = team_fair_share * self.estimated_pot
                    fair_shares[f"{team} ({seed_str})"] = team_fair_share
                else:
                    fair_values[team] = team_fair_share * self.estimated_pot
                    fair_shares[team] = team_fair_share
        
                # Apply bonus for 13-16 seeds
            
                if self.team_seeds.get(team) >= 13:
                    seed_bonus_counter += 1
                    
                    if len(self.auction_results) == 0:
                        fair_values[f"{team} ({seed_str})"] += round((0.03 / 16) * self.estimated_pot, 2)
                        fair_shares[f"{team} ({seed_str})"] += 0.03 / 16
                    else:
                        fair_values[team] += round((0.03 / 16) * self.estimated_pot, 2)
                        fair_shares[team] += 0.03 / 16

                #print(f"Team: {team}, Fair Percentage: {round(team_fair_share*100,5)}")

        if seed_bonus_counter != 16:
            raise ValueError(f"warning: seed bonus counter is {seed_bonus_counter}, not 16")

        fair_values = dict(sorted(fair_values.items(), key=lambda item: item[1], reverse=True))
        
        fair_values_as_pct = round(sum(fair_values.values())/self.estimated_pot,4)
        if fair_values_as_pct != 1:
            print(f"ERROR: Fair values as % of pool, must be 1:  {round(sum(fair_values.values())/self.estimated_pot,4)}")
        print("")
        return fair_values, fair_shares
    
    def update_pot(self, team, sale_price, a=0.0886, b=4.22):
        if team not in self.odds_dict:
            print("Error: Team not found in odds dictionary.")
            return

        fair_share_sum = 0
        self.auction_results[team] = sale_price
        total_sales = sum(self.auction_results.values())

        self.last_pot = self.estimated_pot  # Store previous estimate before change
        
        payout_percentages = [0.0075, 0.015, 0.0225, 0.035, 0.06, 0.08]
        fair_shares = {team: .97* sum(prob * pct for prob, pct in zip(odds, payout_percentages)) for team, odds in self.odds_dict.items()}
        for team in fair_shares.keys():
            seed_str = str(self.team_seeds.get(team))
            if self.team_seeds.get(team) >= 13:
                fair_shares[team] += (0.03 / 16)
        
        for team in self.auction_results:
            fair_share_sum += fair_shares[team]
            seed_str = str(self.team_seeds.get(team))
            
        
        # Calculate new estimated pot
        team_implied_total = sale_price / fair_shares[team]
        estimated_total = total_sales / fair_share_sum
        
        
        last_team_sold = list(self.auction_results.keys())[-1]
        last_sale_price = self.auction_results[last_team_sold]

        self.auction_relative[team] = (self.auction_results[team] / (fair_shares[team]*self.estimated_pot) - 1) * 100

        self.generate_auction_df_for_year_and_params(self.auction_results, fair_shares_2025, (a,b), 2025)

        print(f"\033[34m--------------------------------------------------------------------------------------------------------------------\033[0m")
        print(f"{last_team_sold} ({seed_str}) sold for ${last_sale_price:,.0f}, and was expected to be {fair_shares[last_team_sold]*100:.2f}% of the pool")
        print(f"{last_team_sold} ({seed_str}) implies a total pot of ${team_implied_total:,.0f}")
        print("")
        print(f"Total Auction sales: ${total_sales:,.0f}")
        print(f"Total Expected Pool % Sold: {fair_share_sum*100:,.2f}%")
        print(f"All Teams Implied Total Pot: ${estimated_total:,.0f}")
        
        # Apply exponential decay weighting
        initial_estimate = 200000  # Initial estimated pot
        N = len(self.auction_results)  # Number of teams auctioned
        W_initial = math.exp(- (a * N + b * fair_share_sum))  # Decaying weight
        fomo_factor = 0.1 * (1 - W_initial) * (1 - N/64)

        self.estimated_pot = W_initial * initial_estimate + (1 - W_initial) * estimated_total + fomo_factor * estimated_total

        

        print("")
        print(f"Previous estimated pot: ${self.last_pot:,.0f}")
        print(f"\033[32mUpdated estimated pot: ${self.estimated_pot:,.0f}\033[0m -- {round(W_initial*100,2)}% initial estimate: ${round(initial_estimate):,.0f}, {round((1-W_initial)*100,2)}% total_expected_pot: ${round(estimated_total):,.0f}, fomo_factor: {fomo_factor*100:.2f}%")
        print(f"\033[34m--------------------------------------------------------------------------------------------------------------------\033[0m")
        print("")
    
    def run_live_update(self):
        while True:
            team = input("Enter team name (or 'exit' to stop, 'undo' to revert last entry): ").strip()
            if team.lower() == 'exit':
                break
            if team.lower() == 'adjust':
                try:
                    new_pot = float(input("Enter new estimated pot: ").strip())
                    self.estimated_pot = new_pot
                    fair_values, fair_shares = self.calculate_fair_value()
                    self.print_results_table(fair_values, fair_shares)
                    continue
                except ValueError:
                    print("Error: Pot must be a number.")
                    continue

            if team.lower() == 'undo' and self.auction_results:
                last_team = list(self.auction_results.keys())[-1]
                self.estimated_pot = self.last_pot
                del self.auction_results[last_team]
                print("")
                print(f"Undo last entry: {last_team}")
                fair_values, fair_shares = self.calculate_fair_value()
                # print(fair_values, fair_shares)
                self.print_results_table(fair_values, fair_shares)
                continue
            
            if team not in self.odds_dict:
                print("Invalid team. Try again.")
                continue
                
            if team in self.auction_results:
                print("Error: Team has already been sold.")
                continue
            
            self.show_team_details(team)
            try:
                price = float(input(f"Enter sale price for {team}: ").strip())
            except ValueError:
                print("Error: Price must be a number.")
                continue
                
            self.update_pot(team, price)
            fair_values, fair_shares = self.calculate_fair_value()
            self.print_results_table(fair_values, fair_shares)

    def print_results_table(self, fair_values, fair_shares):
        # Formatting setup
        max_team_length = max(len(team) for team in fair_values.keys())
        max_value_length = max(len(f"{float(value):,.0f}") for value in fair_values.values()) + 2
        max_percent_length = max(len(f"{fair_share*100:.2f}%") for fair_share in fair_shares.values())

        team_col_width = max_team_length + 6
        value_col_width = max_value_length - 1
        percent_col_width = max_percent_length + 6

        # Print header
        print(f"{'Team':<{team_col_width}}{'Fair Value':>{value_col_width}} |{'Fair Share':>{percent_col_width}}  Auction Results")
        separator = "-" * team_col_width + "-" * value_col_width + "----+-" + "-" * percent_col_width + "-" * 20
        print(separator)
        
        # Print team data
        for team_and_seed, value in fair_values.items():
            if len(self.auction_results) == 0:
                team = team_and_seed
                fair_share = fair_shares[team]
            else:
                team = team_and_seed.split(" (")[0]
                seed = self.team_seeds[team]
                seed_str = str(seed)
                fair_share = fair_shares[team]

            if team in self.auction_results:
                sale_price = self.auction_results[team]
                
                team_str = f"{team} ({seed_str})"
                value_str = f"{float(value):,.0f}"
                percent_str = f"{fair_share*100:.2f}%"

                team_padded = team_str.ljust(team_col_width)
                value_padded = value_str.rjust(value_col_width)
                percent_padded = percent_str.rjust(percent_col_width)
                
                team_colored = colored(team_padded, 'blue')
                value_colored = colored(value_padded, 'blue')
                percent_colored = colored(percent_str, 'blue')
                
                if sale_price > value:
                    sale_price_colored = colored(f" ${sale_price:,.0f}", 'red')
                else:
                    sale_price_colored = colored(f" ${sale_price:,.0f}", 'green')
                
                print(f"{team_colored}  {value_colored}  |  {percent_colored}        {sale_price_colored}")
            else:
                if len(self.auction_results) == 0:
                    team_str = team
                    value_str = f"{float(value):,.0f}"
                    percent_str = f"{fair_share*100:.2f}%"
                else:
                    team_str = f"{team} ({seed_str})"
                    value_str = f"{float(value):,.0f}"
                    percent_str = f"{fair_share*100:.2f}%"
                
                team_padded = team_str.ljust(max_team_length + 5)
                value_padded = value_str.rjust(max_value_length + 2)
                
                print(f"{team_padded}{value_padded}  |  {percent_str}")

    def show_team_details(self, team):
        N = len(self.auction_results)


        # Calculate fair values for various scenarios
        expected_pot = self.estimated_pot
        width = max(0.15 * (1 - N/64),.05)
        min_pot_estimate = expected_pot * (1 - width)
        max_pot_estimate = expected_pot * (1 + width)
    
        # Calculate bear case (bottom range)
        self.estimated_pot = min_pot_estimate
        bear_fair_values, _ = self.calculate_fair_value()
        
        # Calculate bull case (top range)
        self.estimated_pot = max_pot_estimate
        bull_fair_values, _ = self.calculate_fair_value()
        
        # Calculate expected case (midpoint)
        self.estimated_pot = expected_pot
        fair_values, fair_shares = self.calculate_fair_value()
        
        # Find the team in the keys
        team_key = None
        for key in fair_values.keys():
            if len(self.auction_results) == 0:
                if key.split(" (")[0] == team:
                    print(key)
                    team_key = key
                    break
            else:
                if key == team:
                    team_key = key
                    break
        
        if not team_key:
            print(f"Team '{team}' not found.")
            return
        
        seed = self.team_seeds[team]
        seed_str = str(seed)
        team_str = f"{team} ({seed_str})"
        
        # ----- SECTION 1: FAIR VALUE DETAILS -----
        # Determine column widths
        team_col_width = len(team_str) + 6
        value_col_width = max(
            len(f"${float(bear_fair_values[team_key]):,.0f}"),
            len(f"${float(fair_values[team_key]):,.0f}"),
            len(f"${float(bull_fair_values[team_key]):,.0f}")
            
        ) + 8
        percent_col_width = len(f"{fair_shares[team_key]*100:.2f}%") + 4

        total_width = 110
        
        print("\n" + "=" * total_width)
        print(f"TEAM DETAILS: {team_str}")
        print("=" * total_width + "\n")
        
        # Header for section 1
        print("FAIR VALUE ANALYSIS:")
        width_adj = 6
        print(f"{'Team':<{team_col_width-3}}{' | '}{' FV ($'}{min_pot_estimate:,.0f}{') |':<{value_col_width-width_adj}}{'FV ($'}{self.estimated_pot:,.0f}{') | ':<{value_col_width-width_adj}}{'FV ($'}{max_pot_estimate:,.0f}{') | ':<{value_col_width-width_adj}}{'Fair Share %':<{percent_col_width-width_adj}}")
        separator = "-" * total_width
        print(separator)
        
        # Data for section 1
        col_adj = 4
        team_padded = f"{team_str}    | ".ljust(team_col_width)
        bear_value = f"     ${float(bear_fair_values[team_key]):,.0f}".ljust(value_col_width+col_adj-2) + ' | '
        exp_value = f"    ${float(fair_values[team_key]):,.0f}".ljust(value_col_width+col_adj) + '| '
        bull_value = f"      ${float(bull_fair_values[team_key]):,.0f}".ljust(value_col_width+col_adj) + '| '
        percent_str = f"    {fair_shares[team_key]*100:.2f}%".ljust(percent_col_width+col_adj)
        
        print(f"{team_padded}{bear_value}{exp_value}{bull_value}{percent_str}")
        print("\n")
        
       # ----- SECTION 2: RELEVANT TRANSACTIONS -----
        print("RELEVANT TRANSACTIONS:")

        # Get sorted list of teams by fair value
        sorted_teams = [k.split(" (")[0] for k in fair_values.keys()]

        relevant_teams = []
        team_fair_share = fair_shares[team_key]
        seed = self.team_seeds[team]

        for t in sorted_teams:
            # Find the key for this team in fair_shares
            t_key = None
            for key in fair_values.keys():
                if key.split(" (")[0] == t:
                    t_key = key
                    break
                    
            if t_key is None:
                continue
                
            t_fair_share = fair_shares[t_key]
            
            # Check if team has same seed or fair_share within 10% of current team
            percentage_diff = abs(t_fair_share - team_fair_share) / team_fair_share
            if self.team_seeds.get(t) == seed or percentage_diff <= 0.1:
                if t in self.auction_results or t == team:
                    relevant_teams.append(t)

        # Ensure the current team is always included
        if team not in relevant_teams:
            relevant_teams = [team]

        # Column widths for transactions table
        team_trans_width = max(len("Relevant Transactions"), max([len(f"{t} ({self.team_seeds[t]})") for t in relevant_teams]) + 7)
        share_width = max(len("Fair Share %"), max([len(f"{fair_shares.get(t, 0)*100:.2f}%") for t in relevant_teams]) + 7)
        diff_width = 20

        # Calculate price width safely
        if any(t in self.auction_results for t in relevant_teams):
            price_width = max(len("Price"), max([len(f"${self.auction_results[t]:,.0f}") for t in relevant_teams if t in self.auction_results]) + 2)
        else:
            price_width = len("Price") + 5  # Default width if no teams have been sold

        # Header for section 2
        header = (f"{'Relevant Transactions':<{team_trans_width}} | {'Price':<{price_width}} | "
                f"{'Fair Share %':<{share_width}} | {'% Over/Under FV':<{diff_width}}")
        print(header)
        
        # Create separator with vertical lines
        parts = ["-" * (team_trans_width), "-" * (price_width), "-" * (share_width), "-" * (diff_width)]
        separator = "-+-".join(parts)
        print(separator)

        # Data for section 2
        for t in relevant_teams:
            t_str = f"{t} ({self.team_seeds[t]})".ljust(team_trans_width)
            t_key = None
            for key in fair_values:
                if key.split(" (")[0] == t:
                    t_key = key
                    break
            
            if t in self.auction_results:
                price = self.auction_results[t]

                seed_str = str(self.team_seeds[t])
                if len(self.auction_results) == 0:
                    team_key = f"{t} ({seed_str})"
                else:
                    team_key = t

                price_str = f"${price:,.0f}".ljust(price_width)
                pct_diff = auction_relative[t]
                if pct_diff > 0:
                    diff_str = colored(f"+{pct_diff:.1f}%".ljust(diff_width), 'red')
                else:
                    diff_str = colored(f"{pct_diff:.1f}%".ljust(diff_width), 'green')
            else:
                price_str = "".ljust(price_width)
                diff_str = "".ljust(diff_width)

            share_str = f"{fair_shares[t_key]*100:.2f}%".ljust(share_width)
            print(f"{t_str} | {price_str} | {share_str} | {diff_str}")
        print("\n")
        
        # ----- SECTION 3: ODDS BREAKDOWN -----
        print("ODDS BREAKDOWN:")
        # Column widths for odds table
        odds_type_width = 12
        rounds_width = 10
        
        # Header for section 2
        header = (f"{'Odds Type':<{odds_type_width-1}} | {'Round 32':<{rounds_width-3}} | {'Sweet 16':<{rounds_width-3}} | "
              f"{'Elite 8 ':<{rounds_width-3}} | {'Final 4 ':<{rounds_width-3}} | {'2nd Place':<{rounds_width-4}} | {'Winner':<{rounds_width-3}}")
        print(header)
        
        #Separator for section 2
        parts = ["-" * (odds_type_width-1)]
        for _ in range(6):
            parts.append("-" * (rounds_width-2))
        separator = "-+-".join(parts)
        print(separator)

        width_adj = 2
        # Data for FanDuel odds
        fd_row = f"{'FD Odds':<{odds_type_width-1}} | "
        fd_r32 = f"{self.fanduel_round_32_odds[team]*100:.1f}%".ljust(rounds_width-width_adj) + " | "
        fd_s16 = f"{self.fanduel_sweet_sixteen_odds[team]*100:.1f}%".ljust(rounds_width-width_adj) + " | "
        fd_e8 = f"{self.fanduel_elite_eight_odds[team]*100:.1f}%".ljust(rounds_width-width_adj) + " | "
        fd_f4 = f"{self.fanduel_final_four_odds[team]*100:.1f}%".ljust(rounds_width-width_adj) + " | "
        fd_2nd =f"{self.fanduel_second_place_odds[team]*100:.1f}%".ljust(rounds_width-width_adj) + " | "
        fd_win = f"{self.fanduel_champ_odds[team]*100:.1f}%".ljust(rounds_width-width_adj)
        print(f"{fd_row}{fd_r32}{fd_s16}{fd_e8}{fd_f4}{fd_2nd}{fd_win}")
        
        # Data for KenPom odds
        kp_row = f"{'KenPom Odds':<{odds_type_width-1}} | "
        kp_r32 = f"{self.KenPom_round_32_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_s16 = f"{self.KenPom_sweet_sixteen_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_e8 = f"{self.KenPom_elite_eight_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_f4 = f"{self.KenPom_final_four_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_2nd = f"{self.KenPom_second_place_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_win = f"{self.KenPom_champ_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj)
        print(f"{kp_row}{kp_r32}{kp_s16}{kp_e8}{kp_f4}{kp_2nd}{kp_win}")
        print("\n")

        # Data for KenPom odds
        kp_row = f"{'538 Odds':<{odds_type_width-1}} | "
        kp_r32 = f"{self.round_32_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_s16 = f"{self.sweet_sixteen_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_e8 = f"{self.elite_eight_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_f4 = f"{self.final_four_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_2nd = f"{self.second_place_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj) + " | " 
        kp_win = f"{self.champ_odds.get(team, 0)*100:.1f}%".ljust(rounds_width-width_adj)
        print(f"{kp_row}{kp_r32}{kp_s16}{kp_e8}{kp_f4}{kp_2nd}{kp_win}")
        print("\n")

    def past_auction_study(self, auction_results, year):
        team_implied_total_pot = {}
        all_teams_implied_total_pot = {}
        teams_in_auction_order = list(auction_results.keys())

        running_total = 0
        running_fair_pct = 0

        payout_percentages = [0.0075, 0.015, 0.0225, 0.035, 0.06, 0.08]
        fair_shares = {}

        for team, odds in auction.odds_dict.items():
            team_fair_share = .97 * sum(prob * pct for prob, pct in zip(odds, payout_percentages))

            seed = auction.team_seeds[team]
            if seed is None:
                print(f"Team not found in team_seeds: '{team}'")
            elif seed >= 13:
                team_fair_share += (0.03 / 16)
            fair_shares[team] = team_fair_share

        for team in teams_in_auction_order:
            price_paid = auction_results[team]
            running_total += price_paid
            
            if team in fair_shares:
                running_fair_pct += fair_shares[team]
            else:
                print(f"Warning: {team} not found in odds dictionary")
                continue
            
            if running_fair_pct > 0:
                all_teams_implication = running_total / running_fair_pct
                all_teams_implied_total_pot[team] = all_teams_implication

                individual_team_implication = price_paid / fair_shares[team]
                team_implied_total_pot[team] = individual_team_implication

        results_df = pd.DataFrame({
            'Auction_Order': list(range(1, len(team_implied_total_pot) + 1)),
            'Team': list(team_implied_total_pot.keys()),
            'Seed': [auction.team_seeds.get(team, 0) for team in team_implied_total_pot.keys()],
            'Price_Paid': [round(auction_results[team]) for team in team_implied_total_pot.keys()],
            'Team_Implied_Total_Pot': [round(value) for value in team_implied_total_pot.values()],
            'All_Teams_Implied_Total_Pot': [round(value) for value in all_teams_implied_total_pot.values()],
            'Cumulative_Spent': [round(sum(list(auction_results.values())[:i+1])) for i in range(len(team_implied_total_pot))],
            'Fair_Value_Pct': [round(fair_shares.get(team, 0)*100, 2) for team in team_implied_total_pot.keys()],
            'Cumulative_Fair_Pct': [round(sum([fair_shares.get(teams_in_auction_order[j], 0) for j in range(i+1)])*100, 2)
                                    for i in range(len(team_implied_total_pot))]
        })

        folder_path = "Auction CSVs"
        filename = f"implied_total_pot_{year}_auction.csv"
        filename = os.path.join(folder_path, filename)
        results_df.to_csv(filename, index=False)
        return results_df

    def get_initial_estimate(self, year):
        """Determine the initial estimate as a percentage of the previous year's final pot."""
        if year == 2021:
            return 125000
        elif year == 2022:
            return 120000
        elif year == 2023:
            return 145000
        elif year == 2024:
            return 135000

    def simulate_auction(self, auction_results, fair_shares, initial_estimate, a, b, C, year):
        """Simulates the auction process and computes the Mean Squared Error for the estimated pot."""
        estimated_pots = []
        actual_pots = []
        estimated_pot = initial_estimate
        total_sales = 0
        fair_share_sum = 0
        N = 0

        for team, sale_price in auction_results.items():
            seed_str = f" ({team_seeds_data[year][team]})" 
            N += 1
            total_sales += sale_price
            fair_share_sum += fair_shares[team+seed_str]
            W_initial = math.exp(- (a * N + b * fair_share_sum))

            estimated_pot = W_initial * initial_estimate + (1 - W_initial) * (total_sales / fair_share_sum)

            estimated_pots.append(estimated_pot)
            actual_pots.append(sum(auction_results.values()))  # The true pot value at this point

        mse = round(np.mean((np.array(estimated_pots) - np.array(actual_pots)) ** 2))


        log_data.append({"Year": year, "a": a, "b": b, "C": C, "MSE": mse, "root(MSE)": round(math.sqrt(mse)), "Estimated_Pot": round(initial_estimate), "Actual_Pot": sum(auction_results.values())})

        return mse

    def cross_validation(self, auction_results_data, fair_share_data, max_iterations=10000):
        """Perform cross-validation by leaving out one year at a time and training the model."""
        
        results = []  # List to store the results for each iteration (year left out)
        optimal_params_by_year = {}  # Dictionary to store optimal parameters for each year
        
        # Get the list of all years
        all_years = list(auction_results_data.keys())
        
        # Helper function to optimize the parameters
        def callback(params, iteration_results, years_to_use):
            a, b, C = params
            mse_total = objective(params, years_to_use)
            iteration_results.append({
                'Iteration': len(iteration_results) + 1,
                'a': round(a, 4),
                'b': round(b, 4),
                'C': round(C, 2),
                'Training_MSE': round(math.sqrt(mse_total), 2)
            })
        
        # Helper function for the objective function
        def objective(params, years_to_use):
            a, b, C = params
            mse_total = 0
            for year in years_to_use:
                initial_estimate = self.get_initial_estimate(year)
                mse_total += self.simulate_auction(auction_results_data[year], fair_share_data[year], initial_estimate, a, b, C, year)
            return mse_total / len(years_to_use)  # Average MSE across training years

        # Loop through each year, leaving that year out for testing
        for year_to_leave_out in all_years:
            print(f"\nTraining and testing with {year_to_leave_out} left out.")
            
            # Create the training data by excluding the current year
            years_to_use = [year for year in all_years if year != year_to_leave_out]
            
            # List to store the iterations for the current year-to-leave-out
            iteration_results = []
            
            # Initial guess for parameters
            initial_guess = [0.3, 3.0, 5000]
            bounds = [(0.01, 2), (1, 20), (-10000, 50000)]  # Example bounds for a, b, C
            
            # Run optimization with callback for leaving out the year
            result = minimize(lambda params: objective(params, years_to_use), initial_guess, bounds=bounds, method='Powell', options={'maxiter': max_iterations, 'disp': True}, callback=lambda params: callback(params, iteration_results, years_to_use))
            
            # After optimization is complete, test the model on the left-out year
            a, b, C = result.x  # Optimal parameters from final iteration
            optimal_params_by_year[year_to_leave_out] = (a, b, C)  # Store the optimal parameters
            
            final_mse = result.fun
            
            # Test the model on the left-out year
            initial_estimate = self.get_initial_estimate(year_to_leave_out)
            test_mse = self.simulate_auction(auction_results_data[year_to_leave_out], fair_share_data[year_to_leave_out], initial_estimate, a, b, C, year_to_leave_out)
            
            # Append the results of the final test for the current leave-out year
            iteration_results.append({
                'Iteration': 'Final Test',
                'a': round(a, 4),
                'b': round(b, 4),
                'C': round(C, 2),
                'Training_MSE': round(math.sqrt(final_mse), 2),
                'Test_MSE': round(math.sqrt(test_mse), 2)
            })
            
            # Add the iteration results for this leave-out year to the overall results
            for iteration_result in iteration_results:
                iteration_result['Year_Left_Out'] = year_to_leave_out
                results.append(iteration_result)
        
        # Now, run the model on all years without leaving any out (5th iteration)
        print("\nTraining and testing with no year left out.")
        
        # Create the training data by using all years
        years_to_use = all_years
        
        # List to store the iterations for the no-year-left-out case
        iteration_results = []
        
        # Run optimization for all years (no leave-out)
        result = minimize(lambda params: objective(params, years_to_use), initial_guess, bounds=bounds, method='Powell', options={'maxiter': max_iterations, 'disp': True}, callback=lambda params: callback(params, iteration_results, years_to_use))
        
        # After optimization is complete, test the model on all years
        a, b, C = result.x  # Optimal parameters from final iteration
        optimal_params_by_year['All_Years'] = (a, b, C)  # Store the optimal parameters
        
        final_mse = result.fun
        
        # Test the model on all years
        for year in all_years:
            initial_estimate = self.get_initial_estimate(year)
            test_mse = self.simulate_auction(auction_results_data[year], fair_share_data[year], initial_estimate, a, b, C, year)
            
            # Append the results of the final test for the current leave-out year
            iteration_results.append({
                'Iteration': 'Final Test',
                'a': round(a, 4),
                'b': round(b, 4),
                'C': round(C, 2),
                'Training_MSE': round(math.sqrt(final_mse), 2),
                'Test_MSE': round(math.sqrt(test_mse), 2)
            })
        
        # Add the iteration results for the no-year-left-out case to the overall results
        for iteration_result in iteration_results:
            iteration_result['Year_Left_Out'] = 'All_Years'
            results.append(iteration_result)

        # Create a DataFrame from the results and save to CSV
        df = pd.DataFrame(results)
        df.to_csv('cross_validation_results.csv', index=False)
        print("Cross-validation complete. Results saved to 'cross_validation_results.csv'.")
        
        # Return the optimal parameters by year for later use
        return optimal_params_by_year

    def generate_auction_df_for_year_and_params(self, auction_results, fair_shares, optimal_params, year):
        """
        Generate a DataFrame for a specific year with the optimal parameters (a, b).
        """
        # Extract optimal parameters (a, b) for the given year
        a, b = optimal_params

        # Initialize data structures for simulation
        team_implied_total_pot = {}
        all_teams_implied_total_pot = {}
        smart_estimated_pot = {}
        W_initial_values = {}
        fair_value_pcts = {}
        teams_in_auction_order = list(auction_results.keys())

        running_total = 0
        running_fair_pct = 0
        N = 0
        initial_estimate = self.original_pot 

        for team in teams_in_auction_order:
            N += 1
            seed_str = f" ({team_seeds_data[year][team]})"
            price_paid = auction_results[team]
            running_total += price_paid
            running_fair_pct += fair_shares[team+seed_str]
            W_initial = math.exp(- (a * N + b * running_fair_pct))
            

            all_teams_implication = running_total / running_fair_pct
            all_teams_implied_total_pot[team] = all_teams_implication

            individual_team_implication = price_paid / fair_shares[team+seed_str]
            team_implied_total_pot[team] = individual_team_implication

            fomo_factor = 0.1 * (1 - W_initial) * (1 - N/64)
            
            self.estimated_pot = W_initial * initial_estimate + (1 - W_initial) * all_teams_implication + fomo_factor * all_teams_implication
            smart_estimated_pot[team] = self.estimated_pot

            W_initial_values[team] = W_initial
            fair_value_pcts[team] = round(fair_shares[team+seed_str]*100,2)


            #print(fair_shares)

        # Create the DataFrame to hold all relevant results
        results_df = pd.DataFrame({
            'Auction_Order': list(range(1, len(team_implied_total_pot) + 1)),
            'Team': list(team_implied_total_pot.keys()),
            'Price_Paid': [round(auction_results[team]) for team in team_implied_total_pot.keys()],
            'Team_Implied_Total_Pot': team_implied_total_pot.values(),
            'All_Teams_Implied_Total_Pot': all_teams_implied_total_pot.values(),
            'Cumulative_Spent': [round(sum(list(auction_results.values())[:i+1])) for i in range(len(team_implied_total_pot))],
            'Fair_Value_Pct': fair_value_pcts.values(),
            'Smart_Estimated_Pot': smart_estimated_pot.values(),
            'Initial_Estimate_Weighting (W_initial)': W_initial_values.values(),
            'Complement_Estimate_Weighting (1-W_initial)': [(1 - W_initial) for W_initial in W_initial_values.values()],
        })

        filename = f'Live 2025 Auction Graph.csv'
        folder_path = "Weighting Optimization CSVs"
        filename = os.path.join(folder_path, filename)
        results_df.to_csv(filename, index=False)
        return results_df

    def generate_raw_fd_odds_csv(self):
        for team in auction.fanduel_champ_odds:
            fanduel_round_32_odds_2025[team] = auction.american_to_prob(fanduel_round_32_odds_2025[team], "American")
            fanduel_sweet_sixteen_odds_2025[team] = auction.american_to_prob(fanduel_sweet_sixteen_odds_2025[team], "American")
            fanduel_elite_eight_odds_2025[team] = auction.american_to_prob(fanduel_elite_eight_odds_2025[team], "American")
            fanduel_final_four_odds_2025[team] = auction.american_to_prob(fanduel_final_four_odds_2025[team], "American")
            fanduel_second_place_odds_2025[team] = auction.american_to_prob(fanduel_second_place_odds_2025[team], "American")
            fanduel_champ_odds_2025[team] = auction.american_to_prob(fanduel_champ_odds_2025[team], "American")

        # Then create the dictionary with the converted odds
        odds_dict = {}
        for team in auction.fanduel_champ_odds:
            odds_dict[team] = [
                fanduel_round_32_odds_2025[team], 
                fanduel_sweet_sixteen_odds_2025[team], 
                fanduel_elite_eight_odds_2025[team], 
                fanduel_final_four_odds_2025[team], 
                fanduel_second_place_odds_2025[team], 
                fanduel_champ_odds_2025[team]
            ]

        # Sort teams by champion odds (highest to lowest)
        sorted_teams = sorted(odds_dict.items(), key=lambda x: x[1][5], reverse=True)

        output_file = "FD_Raw_Odds.csv"
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Team', 'Rd 32', 'Sweet 16', 'Elite 8', 'Final 4', 'Title Game', 'Champion'])
            for team, odds in sorted_teams:
                # No need to multiply by 100 since american_to_prob already returns percentage values
                odds = [round(odd, 2) for odd in odds]
                writer.writerow([team] + odds)
    
    def generate_american_fd_odds_csv(self):
        odds_dict = {}
        for team in auction.fanduel_champ_odds:
            odds_dict[team] = [
                fanduel_round_32_odds_2025[team], 
                fanduel_sweet_sixteen_odds_2025[team], 
                fanduel_elite_eight_odds_2025[team], 
                fanduel_final_four_odds_2025[team], 
                fanduel_second_place_odds_2025[team], 
                fanduel_champ_odds_2025[team]
            ]

        # Sort teams by champion odds (highest to lowest)
        sorted_teams = sorted(odds_dict.items(), key=lambda x: x[1][5], reverse=False)

        output_file = "FD_American_Odds.csv"
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Team', 'Rd 32', 'Sweet 16', 'Elite 8', 'Final 4', 'Title Game', 'Champion'])
            for team, odds in sorted_teams:
                # No need to multiply by 100 since american_to_prob already returns percentage values
                odds = [round(odd, 2) for odd in odds]
                writer.writerow([team] + odds)

    def generate_devigged_fd_odds_csv(self):
        odds_dict = {}
        for team in auction.fanduel_champ_odds:
            odds_dict[team] = [
                auction.fanduel_round_32_odds[team]*100, 
                auction.fanduel_sweet_sixteen_odds[team]*100, 
                auction.fanduel_elite_eight_odds[team]*100, 
                auction.fanduel_final_four_odds[team]*100, 
                auction.fanduel_second_place_odds[team]*100, 
                auction.fanduel_champ_odds[team]*100
            ]

        # Sort teams by champion odds (highest to lowest)
        sorted_teams = sorted(odds_dict.items(), key=lambda x: x[1][5], reverse=True)

        output_file = "FD_Devigged_Odds.csv"
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Team', 'Rd 32', 'Sweet 16', 'Elite 8', 'Final 4', 'Title Game', 'Champion'])
            for team, odds in sorted_teams:
                # No need to multiply by 100 since american_to_prob already returns percentage values
                odds = [round(odd, 2) for odd in odds]
                writer.writerow([team] + odds) 
# Seed and Odds Data Below 2021 - 2024

round_32_vig = 0

team_seeds_2025 = {
    "Duke": 1,
    "Florida": 1,
    "Houston": 1,
    "Auburn": 1,
    "Alabama": 2,
    "Saint John's": 2,
    "Tennessee": 2,
    "Michigan State": 2,
    "Wisconsin": 3,
    "Texas Tech": 3,
    "Kentucky": 3,
    "Iowa State": 3,
    "Arizona": 4,
    "Maryland": 4,
    "Purdue": 4,
    "Texas A&M": 4,
    "Oregon": 5,
    "Memphis": 5,
    "Clemson": 5,
    "Michigan": 5,
    "BYU": 6,
    "Missouri": 6,
    "Illinois": 6,
    "Ole Miss": 6,
    "Saint Mary's": 7,
    "Kansas": 7,
    "UCLA": 7,
    "Marquette": 7,
    "Gonzaga": 8,
    "Connecticut": 8,
    "Louisville": 8,
    "Mississippi State": 8,
    "Baylor": 9,
    "Oklahoma": 9,
    "Georgia": 9,
    "Creighton": 9,
    "Utah State": 10,
    "Arkansas": 10,
    "New Mexico": 10,
    "Vanderbilt": 10,
    "VCU": 11,
    "Drake": 11,
    "UNC/San Diego State": 11,
    "Texas/Xavier": 11,
    "Colorado State": 12,
    "Liberty": 12,
    "McNeese": 12,
    "UC San Diego": 12,
    "Grand Canyon": 13,
    "High Point": 13,
    "Yale": 13,
    "Akron": 13,
    "UNC Wilmington": 14,
    "Troy": 14,
    "Lipscomb": 14,
    "Montana": 14,
    "Omaha": 15,
    "Wofford": 15,
    "Bryant": 15,
    "Robert Morris": 15,
    "American/Mount St. Mary's": 16,
    "Norfolk State": 16,
    "SIUE": 16,
    "Alabama State/Saint Francis": 16 }
team_seeds_2024 = {
    "Connecticut": 1,
    "Purdue": 1,
    "Houston": 1,
    "UNC": 1,
    "Arizona": 2,
    "Tennessee": 2,
    "Iowa State": 2,
    "Marquette": 2,
    "Creighton": 3,
    "Baylor": 3,
    "Kentucky": 3,
    "Illinois": 3,
    "Auburn": 4,
    "Alabama": 4,
    "Duke": 4,
    "Kansas": 4,
    "Gonzaga": 5,
    "Wisconsin": 5,
    "San Diego State": 5,
    "Saint Mary's": 5,
    "Texas Tech": 6,
    "BYU": 6,
    "South Carolina": 6,
    "Clemson": 6,
    "Florida": 7,
    "Texas": 7,
    "Washington State": 7,
    "Dayton": 7,
    "Nebraska": 8,
    "Mississippi State": 8,
    "Florida Atlantic": 8,
    "Utah State": 8,
    "Texas A&M": 9,
    "Northwestern": 9,
    "TCU": 9,
    "Michigan State": 9,
    "Drake": 10,
    "Nevada": 10,
    "Boise State/Colorado": 10,
    "Virginia/Colorado State": 10,
    "NC State": 11,
    "New Mexico": 11,
    "Oregon": 11,
    "Duquesne": 11,
    "UAB": 12,
    "McNeese State": 12,
    "Grand Canyon": 12,
    "James Madison": 12,
    "Yale": 13,
    "College of Charleston": 13,
    "Vermont": 13,
    "Samford": 13,
    "Morehead State": 14,
    "Oakland": 14,
    "Akron": 14,
    "Colgate": 14,
    "South Dakota State": 15,
    "Longwood": 16,
    "Stetson": 16,
    "Western Kentucky": 15,
    "Long Beach State": 15,
    "Howard/Wagner": 16,
    "Montana State/Grambling": 16,
    "Saint Peter's": 15,
    }
team_seeds_2023 = {
    "Houston": 1,
    "Alabama": 1,
    "UCLA": 2,
    "Purdue": 1,
    "Texas": 2,
    "Tennessee": 4,
    "Connecticut": 4,
    "Gonzaga": 3,
    "Arizona": 2,
    "Kansas": 1,
    "Marquette": 2,
    "Saint Mary's": 5,
    "Creighton": 6,
    "San Diego State": 5,
    "Baylor": 3,
    "Xavier": 3,
    "Kansas State": 3,
    "Utah State": 10,
    "Iowa State": 6,
    "Duke": 5,
    "Kentucky": 6,
    "West Virginia": 9,
    "Texas A&M": 7,
    "Indiana": 4,
    "Memphis": 8,
    "Maryland": 8,
    "Arkansas": 8,
    "Virginia": 4,
    "Florida Atlantic": 9,
    "Michigan State": 7,
    "Auburn": 9,
    "TCU": 6,
    "Boise State": 10,
    "USC": 10,
    "Miami FL": 5,
    "Providence": 11,
    "Iowa": 8,
    "Illinois": 9,
    "Penn State": 10,
    "Northwestern": 7,
    "Missouri": 7,
    "NC State": 11,
    "Drake": 12,
    "Oral Roberts": 12,
    "Nevada/Arizona State": 11,
    "Kent State": 13,
    "VCU": 12,
    "Charleston": 12,
    "Iona": 13,
    "Pittsburgh": 11,
    "Furman": 13,
    "Louisiana": 13,
    "UC Santa Barbara": 14,
    "Montana State": 14,
    "Vermont": 15,
    "Grand Canyon": 14,
    "Princeton": 15,
    "Colgate": 15,
    "Kennesaw State": 14,
    "Northern Kentucky": 16,
    "UNC Asheville": 15,
    "Texas A&M Corpus Chris": 16,
    "Howard": 16,
    "Southern": 16,
    "FDU/Texas Southern": 16
    }
team_seeds_2022 = {
    "Gonzaga": 1,
    "Arizona": 1,
    "Kansas": 1,
    "Baylor": 1,
    "Kentucky": 2,
    "Auburn": 2,
    "Tennessee": 3,
    "Houston": 5,
    "Texas Tech": 3,
    "UCLA": 4,
    "Villanova": 2,
    "Iowa": 5,
    "Duke": 2,
    "Purdue": 3,
    "LSU": 6,
    "Texas": 6,
    "Saint Mary's": 5,
    "Connecticut": 5,
    "Illinois": 4,
    "Arkansas": 4,
    "San Diego State": 8,
    "Loyola Chicago": 10,
    "San Francisco": 10,
    "Wisconsin": 3,
    "Virginia Tech": 11,
    "Alabama": 6,
    "Colorado State": 6,
    "Ohio State": 7,
    "Murray State": 7,
    "Boise State": 8,
    "Michigan": 11,
    "USC": 7,
    "North Carolina": 8,
    "Iowa State": 11,
    "Providence": 4,
    "Memphis": 9,
    "Davidson": 10,
    "TCU": 9,
    "Michigan State": 7,
    "Seton Hall": 8,
    "Creighton": 9,
    "Miami FL": 10,
    "UAB": 12,
    "Marquette": 9,
    "Vermont": 13,
    "Indiana": 12,
    "South Dakota State": 13,
    "Chattanooga": 13,
    "Richmond": 12,
    "New Mexico State": 12,
    "Rutgers/ND": 11,
    "Colgate": 14,
    "Jacksonville State": 15,
    "Montana State": 14,
    "Akron": 13,
    "Saint Peter's": 15,
    "Longwood": 14,
    "Delaware": 15,
    "Cal State Fullerton": 15,
    "Yale": 14,
    "Georgia State": 16,
    "Norfolk State": 16,
    "Texas Southern": 16,
    "Wright State": 16
    }
team_seeds_2021 = {
    "Gonzaga": 1,
    "Illinois": 1,
    "Michigan": 1,
    "Baylor": 1,
    "Houston": 2,
    "Iowa": 2,
    "Ohio State": 2,
    "Alabama": 2,
    "Villanova": 5,
    "Loyola Chicago": 8,
    "Purdue": 4,
    "Florida State": 4,
    "Virginia": 4,
    "Arkansas": 3,
    "Tennessee": 5,
    "USC": 6,
    "Wisconsin": 9,
    "Colorado": 5,
    "San Diego State": 6,
    "Texas Tech": 6,
    "Connecticut": 7,
    "West Virginia": 3,
    "Kansas": 3,
    "BYU": 6,
    "Texas": 3,
    "Creighton": 5,
    "St. Bonaventure": 9,
    "Oklahoma State": 4,
    "North Carolina": 8,
    "Maryland": 10,
    "LSU": 8,
    "Rutgers": 10,
    "Florida": 7,
    "Georgia Tech": 9,
    "Oregon": 7,
    "Utah State": 11,
    "Clemson": 7,
    "Syracuse": 11,
    "Virginia Tech": 10,
    "Oklahoma": 8,
    "VCU": 10,
    "Michigan State/UCLA": 11,
    "Missouri": 9,
    "Georgetown": 12,
    "Wichita State/Drake": 11,
    "North Texas": 13,
    "UC Santa Barbara": 12,
    "Oregon State": 12,
    "Ohio": 13,
    "Abilene Christian": 14,
    "Colgate": 14,
    "Liberty": 13,
    "UNC Greensboro": 13,
    "Winthrop": 12,
    "Eastern Washington": 14,
    "Grand Canyon": 15,
    "Morehead State": 14,
    "Cleveland State": 15,
    "Oral Roberts": 15,
    "Drexel": 16,
    "Iona": 15,
    "Hartford": 16,
    "Mount St. Mary's/Texas Southern": 16,
    "Norfolk State/Appalachian State": 16
    }


KenPom_champ_odds_2025 = {
    "Duke": 22.9,
    "Florida": 18.8,
    "Auburn": 14.9,
    "Houston": 12.2,
    "Tennessee": 5.7,
    "Alabama": 4.2,
    "Michigan State": 2.7,
    "Texas Tech": 2.6,
    "Iowa State": 1.9,
    "Maryland": 1.7,
    "Saint John's": 1.7, 
    "Wisconsin": 1.3,
    "Arizona": 1.2,
    "Gonzaga": 1.1,
    "Kentucky": 0.8,
    "Texas A&M": 0.7,
    "Purdue": 0.6,
    "Missouri": 0.6,
    "Clemson": 0.6,
    "Illinois": 0.5,
    "Kansas": 0.4,
    "Saint Mary's": 0.4,
    "Ole Miss": 0.3,
    "Michigan": 0.3,
    "UCLA": 0.3,
    "Louisville": 0.3,
    "Marquette": 0.2,
    "BYU": 0.2,
    "Oregon": 0.1,
    "Baylor": 0.1,
    "VCU": 0.1,
    "Connecticut": 0.09,
    "UC San Diego": 0.07,
    "Mississippi State": 0.07,
    "Georgia": 0.05,
    "UNC/San Diego State": 0.1,  
    "Colorado State": 0.05,
    "Creighton": 0.04,
    "Oklahoma": 0.04,
    "Arkansas": 0.03,
    "New Mexico": 0.03,
    "Texas/Xavier": 0.02,  
    "Drake": 0.01,
    "Memphis": 0.01,
    "Utah State": 0.01,
    "Vanderbilt": 0.01,
    "McNeese": 0.008,
    "Liberty": 0.007,
    "Yale": 0.003,
    "High Point": 0,  
    "Lipscomb": 0,  
    "Troy": 0,  
    "UNC Wilmington": 0,  
    "Akron": 0,  
    "Robert Morris": 0,  
    "Grand Canyon": 0,  
    "Wofford": 0,  
    "Bryant": 0,  
    "Montana": 0,  
    "Omaha": 0,  
    "Norfolk State": 0,  
    "SIUE": 0,  
    "American/Mount St. Mary's": 0, 
    "Alabama State/Saint Francis": 0  }
KenPom_second_place_odds_2025 = {
    "Duke": 35.6,
    "Florida": 32.7,
    "Auburn": 27.2,
    "Houston": 20.9,
    "Tennessee": 11.8,
    "Alabama": 9.3,
    "Michigan State": 7.0,
    "Texas Tech": 6.5,
    "Iowa State": 5.2,
    "Maryland": 4.7,
    "Saint John's": 4.8, 
    "Wisconsin": 3.6,
    "Arizona": 3.3,
    "Gonzaga": 2.7,
    "Kentucky": 2.4,
    "Texas A&M": 2.3,
    "Purdue": 2.0,
    "Missouri": 2.0,
    "Clemson": 1.8,
    "Illinois": 1.5,
    "Kansas": 1.3,
    "Saint Mary's": 1.2,
    "Ole Miss": 1.1,
    "Michigan": 1.1,
    "UCLA": 0.9,
    "Louisville": 0.9,
    "Marquette": 0.9,
    "BYU": 0.8,
    "Oregon": 0.5,
    "Baylor": 0.5,
    "VCU": 0.4,
    "Connecticut": 0.4,
    "UC San Diego": 0.3,
    "Mississippi State": 0.3,
    "Georgia": 0.2,
    "UNC/San Diego State": 0.4,  
    "Colorado State": 0.2,
    "Creighton": 0.2,
    "Oklahoma": 0.2,
    "Arkansas": 0.2,
    "New Mexico": 0.2,
    "Texas/Xavier": 0.15,  
    "Drake": 0.08,
    "Memphis": 0.09,
    "Utah State": 0.08,
    "Vanderbilt": 0.07,
    "McNeese": 0.05,
    "Liberty": 0.04,
    "Yale": 0.02,
    "High Point": 0.007,
    "Lipscomb": 0.000,
    "Troy": 0.003,
    "UNC Wilmington": 0.002,
    "Akron": 0,  
    "Robert Morris": 0,  
    "Grand Canyon": 0.002,
    "Wofford": 0,  
    "Bryant": 0,  
    "Montana": 0,  
    "Omaha": 0,  
    "Norfolk State": 0,  
    "SIUE": 0,  
    "American/Mount St. Mary's": 0,  
    "Alabama State/Saint Francis": 0  }
KenPom_final_four_odds_2025 = {
    "Duke": 52.5,
    "Florida": 50.1,
    "Auburn": 45.8,
    "Houston": 37.3,
    "Tennessee": 25.1,
    "Alabama": 16.8,
    "Michigan State": 16.8,
    "Texas Tech": 13.8,
    "Iowa State": 13.0,
    "Maryland": 11.1,
    "Saint John's": 11.2, 
    "Wisconsin": 8.5,
    "Arizona": 8.2,
    "Gonzaga": 7.1,
    "Kentucky": 7.6,
    "Texas A&M": 6.7,
    "Purdue": 6.2,
    "Missouri": 5.2,
    "Clemson": 5.7,
    "Illinois": 5.0,
    "Kansas": 3.8,
    "Saint Mary's": 3.5,
    "Ole Miss": 3.6,
    "Michigan": 3.5,
    "UCLA": 3.4,
    "Louisville": 3.0,
    "Marquette": 3.1,
    "BYU": 3.1,
    "Oregon": 1.8,
    "Baylor": 1.5,
    "VCU": 1.4,
    "Connecticut": 1.3,
    "UC San Diego": 1.1,
    "Mississippi State": 1.0,
    "Georgia": 0.9,
    "UNC/San Diego State": 1.8,  
    "Colorado State": 1.0,
    "Creighton": 1.0,
    "Oklahoma": 0.8,
    "Arkansas": 0.7,
    "New Mexico": 0.8,
    "Texas/Xavier": 0.8,  
    "Drake": 0.4,
    "Memphis": 0.4,
    "Utah State": 0.5,
    "Vanderbilt": 0.3,
    "McNeese": 0.3,
    "Liberty": 0.2,
    "Yale": 0.1,
    "High Point": 0.07,
    "Lipscomb": 0.08,
    "Troy": 0.03,
    "UNC Wilmington": 0.01,
    "Akron": 0.01,
    "Robert Morris": 0.002,
    "Grand Canyon": 0.02,
    "Wofford": 0.001,
    "Bryant": 0.001,
    "Montana": 0.002,
    "Omaha": 0.001,
    "Norfolk State": 0, 
    "SIUE": 0,  
    "American/Mount St. Mary's": 0,  
    "Alabama State/Saint Francis": 0  }
KenPom_elite_eight_odds_2025 = {
    "Duke": 69.4,
    "Florida": 67.3,
    "Auburn": 63.3,
    "Houston": 54.4,
    "Tennessee": 48.2,
    "Alabama": 45.6,
    "Michigan State": 38.6,
    "Texas Tech": 34.1,
    "Iowa State": 30.8,
    "Maryland": 21.5,
    "Saint John's": 31.0,  
    "Wisconsin": 26.1,
    "Arizona": 17.4,
    "Gonzaga": 13.8,
    "Kentucky": 20.8,
    "Texas A&M": 14.3,
    "Purdue": 14.2,
    "Missouri": 16.2,
    "Clemson": 13.0,
    "Illinois": 14.2,
    "Kansas": 12.6,
    "Saint Mary's": 11.1,
    "Ole Miss": 11.2,
    "Michigan": 8.3,
    "UCLA": 10.3,
    "Louisville": 6.8,
    "Marquette": 10.2,
    "BYU": 8.9,
    "Oregon": 5.1,
    "Baylor": 4.0,
    "VCU": 6.1,
    "Connecticut": 3.6,
    "UC San Diego": 4.0,
    "Mississippi State": 2.9,
    "Georgia": 2.6,
    "UNC/San Diego State": 4.9,  
    "Colorado State": 3.2,
    "Creighton": 2.8,
    "Oklahoma": 2.5,
    "Arkansas": 3.6,
    "New Mexico": 3.6,
    "Texas/Xavier": 3.6,  
    "Drake": 2.2,
    "Memphis": 1.7,
    "Utah State": 2.4,
    "Vanderbilt": 2.0,
    "McNeese": 1.4,
    "Liberty": 1.1,
    "Yale": 0.6,
    "High Point": 0.5,
    "Lipscomb": 0.6,
    "Troy": 0.3,
    "UNC Wilmington": 0.2,
    "Akron": 0.1,
    "Robert Morris": 0.04,
    "Grand Canyon": 0.2,
    "Wofford": 0.2,
    "Bryant": 0.03,
    "Montana": 0.03,
    "Omaha": 0.04,
    "Norfolk State": 0.009,
    "SIUE": 0.004,
    "American/Mount St. Mary's": 0.001, 
    "Alabama State/Saint Francis": 0.002  }
KenPom_sweet_sixteen_odds_2025 = {
    "Duke": 84.6,
    "Florida": 85.0,
    "Auburn": 80.4,
    "Houston": 71.5,
    "Tennessee": 69.6,
    "Alabama": 69.9,
    "Michigan State": 65.7,
    "Texas Tech": 58.2,
    "Iowa State": 56.2,
    "Maryland": 66.1,
    "Saint John's": 59.6, 
    "Wisconsin": 57.0,
    "Arizona": 61.5,
    "Gonzaga": 22.4,
    "Kentucky": 49.4,
    "Texas A&M": 45.3,
    "Purdue": 45.0,
    "Missouri": 32.6,
    "Clemson": 40.5,
    "Illinois": 35.2,
    "Kansas": 28.4,
    "Saint Mary's": 23.1,
    "Ole Miss": 26.0,
    "Michigan": 30.5,
    "UCLA": 21.7,
    "Louisville": 13.1,
    "Marquette": 23.1,
    "BYU": 24.0,
    "Oregon": 26.6,
    "Baylor": 8.7,
    "VCU": 18.4,
    "Connecticut": 8.5,
    "UC San Diego": 18.3,
    "Mississippi State": 6.7,
    "Georgia": 6.0,
    "UNC/San Diego State": 14.2,  
    "Colorado State": 18.3,
    "Creighton": 6.5,
    "Oklahoma": 6.4,
    "Arkansas": 11.4,
    "New Mexico": 10.8,
    "Texas/Xavier": 12.8, 
    "Drake": 7.7,
    "Memphis": 12.8,
    "Utah State": 7.5,
    "Vanderbilt": 6.6,
    "McNeese": 9.5,
    "Liberty": 9.4,
    "Yale": 5.9,
    "High Point": 4.9,
    "Lipscomb": 3.6,
    "Troy": 2.5,
    "UNC Wilmington": 1.6,
    "Akron": 2.4,
    "Robert Morris": 0.4,
    "Grand Canyon": 2.8,
    "Wofford": 1.3,
    "Bryant": 0.4,
    "Montana": 0.6,
    "Omaha": 0.5,
    "Norfolk State": 0.1,
    "SIUE": 0.06,
    "American/Mount St. Mary's": 0.029, 
    "Alabama State/Saint Francis": 0.008  }
KenPom_round_32_odds_2025 = {
    "Duke": 99.5,
    "Florida": 99.0,
    "Auburn": 99.7,
    "Houston": 98.6,
    "Tennessee": 93.4,
    "Alabama": 97.0,
    "Michigan State": 95.8,
    "Texas Tech": 90.9,
    "Iowa State": 85.8,
    "Maryland": 89.7,
    "Saint John's": 95.1, 
    "Wisconsin": 94.1,
    "Arizona": 89.8,
    "Gonzaga": 69.0,
    "Kentucky": 86.4,
    "Texas A&M": 78.4,
    "Purdue": 80.4,
    "Missouri": 71.6,
    "Clemson": 72.2,
    "Illinois": 66.2,
    "Kansas": 63.8,
    "Saint Mary's": 65.8,
    "Ole Miss": 59.6,
    "Michigan": 58.5,
    "UCLA": 65.1,
    "Louisville": 59.7,
    "Marquette": 61.1,
    "BYU": 54.3,
    "Oregon": 65.4,
    "Baylor": 52.5,
    "VCU": 45.7,
    "Connecticut": 52.3,
    "UC San Diego": 41.5,
    "Mississippi State": 47.5,
    "Georgia": 31.0,
    "UNC/San Diego State": 40.5,  
    "Colorado State": 54.8,
    "Creighton": 40.3,
    "Oklahoma": 47.7,
    "Arkansas": 36.2,
    "New Mexico": 38.9,
    "Texas/Xavier": 33.8,  
    "Drake": 28.4,
    "Memphis": 45.2,
    "Utah State": 34.9,
    "Vanderbilt": 34.2,
    "McNeese": 27.8,
    "Liberty": 34.6,
    "Yale": 21.6,
    "High Point": 19.6,
    "Lipscomb": 14.2,
    "Troy": 13.6,
    "UNC Wilmington": 9.1,
    "Akron": 10.2,
    "Robert Morris": 3.0,
    "Grand Canyon": 10.3,
    "Wofford": 6.6,
    "Bryant": 4.2,
    "Montana": 5.9,
    "Omaha": 4.9,
    "Norfolk State": 1.0,
    "SIUE": 1.4,
    "American/Mount St. Mary's": 0.5,  
    "Alabama State/Saint Francis": 0.27 }


champ_odds_2025_538 = {
    "Duke": 18.5,
    "Florida": 13.8,
    "Houston": 15.6,
    "Auburn": 11.9,
    "Alabama": 5.4,
    "Saint John's": 3.4,
    "Tennessee": 5.1,
    "Michigan State": 3.6,
    "Wisconsin": 1.1,
    "Texas Tech": 3.0,
    "Kentucky": 0.9,
    "Iowa State": 1.7,
    "Arizona": 1.4,
    "Maryland": 1.8,
    "Purdue": 0.5,
    "Texas A&M": 1.0,
    "Oregon": 0.2,
    "Memphis": 0.2,
    "Clemson": 1.0,
    "Michigan": 0.6,
    "BYU": 0.6,
    "Missouri": 0.4,
    "Illinois": 0.7,
    "Ole Miss": 0.5,
    "Saint Mary's": 0.4,
    "Kansas": 0.8,
    "UCLA": 0.3,
    "Marquette": 0.4,
    "Gonzaga": 1.3,
    "Connecticut": 0.5,
    "Louisville": 0.9,
    "Mississippi State": 0.1,
    "Baylor": 0.2,
    "Oklahoma": 0.1,
    "Georgia": 0.1,
    "Creighton": 0.2,
    "Utah State": 0.0,
    "Arkansas": 0.0,
    "New Mexico": 0.1,
    "Vanderbilt": 0.0,
    "VCU": 0.3,
    "Drake": 0.1,
    "UNC/San Diego State": 0.3,
    "Texas/Xavier": 0.3,
    "Colorado State": 0.2,
    "Liberty": 0.0,
    "McNeese": 0.0,
    "UC San Diego": 0.1,
    "Grand Canyon": 0.0,
    "High Point": 0.0,
    "Yale": 0.0,
    "Akron": 0.0,
    "UNC Wilmington": 0.0,
    "Troy": 0.0,
    "Lipscomb": 0.0,
    "Montana": 0.0,
    "Omaha": 0.0,
    "Wofford": 0.0,
    "Bryant": 0.0,
    "Robert Morris": 0.0,
    "American/Mount St. Mary's": 0.0,
    "Norfolk State": 0.0,
    "SIUE": 0.0,
    "Alabama State/Saint Francis": 0.0}
second_place_odds_2025_538 = {
    "Duke": 30.7,
    "Florida": 25.0,
    "Houston": 24.0,
    "Auburn": 22.9,
    "Alabama": 10.3,
    "Saint John's": 8.3,
    "Tennessee": 10.5,
    "Michigan State": 8.6,
    "Wisconsin": 2.7,
    "Texas Tech": 7.0,
    "Kentucky": 2.3,
    "Iowa State": 4.4,
    "Arizona": 3.2,
    "Maryland": 4.6,
    "Purdue": 1.5,
    "Texas A&M": 2.5,
    "Oregon": 0.7,
    "Memphis": 0.6,
    "Clemson": 2.6,
    "Michigan": 1.7,
    "BYU": 1.4,
    "Missouri": 1.2,
    "Illinois": 2.0,
    "Ole Miss": 1.4,
    "Saint Mary's": 1.1,
    "Kansas": 2.2,
    "UCLA": 0.7,
    "Marquette": 1.3,
    "Gonzaga": 2.9,
    "Connecticut": 1.5,
    "Louisville": 2.5,
    "Mississippi State": 0.3,
    "Baylor": 0.5,
    "Oklahoma": 0.2,
    "Georgia": 0.3,
    "Creighton": 0.7,
    "Utah State": 0.1,
    "Arkansas": 0.2,
    "New Mexico": 0.4,
    "Vanderbilt": 0.1,
    "VCU": 0.9,
    "Drake": 0.5,
    "UNC/San Diego State": 0.5,
    "Texas/Xavier": 0.8,
    "Colorado State": 0.8,
    "Liberty": 0.1,
    "McNeese": 0.1,
    "UC San Diego": 0.4,
    "Grand Canyon": 0.1,
    "High Point": 0.1,
    "Yale": 0.1,
    "Akron": 0.0,
    "UNC Wilmington": 0.0,
    "Troy": 0.0,
    "Lipscomb": 0.0,
    "Montana": 0.0,
    "Omaha": 0.0,
    "Wofford": 0.0,
    "Bryant": 0.0,
    "Robert Morris": 0.0,
    "American/Mount St. Mary's": 0.0,
    "Norfolk State": 0.0,
    "SIUE": 0.0,
    "Alabama State/Saint Francis": 0.0}
final_four_odds_2025_538 = {
    "Duke": 51.3,
    "Florida": 39.7,
    "Houston": 38.2,
    "Auburn": 39.9,
    "Alabama": 19.9,
    "Saint John's": 17.3,
    "Tennessee": 23.1,
    "Michigan State": 18.5,
    "Wisconsin": 6.9,
    "Texas Tech": 14.0,
    "Kentucky": 6.9,
    "Iowa State": 10.3,
    "Arizona": 7.2,
    "Maryland": 10.1,
    "Purdue": 4.8,
    "Texas A&M": 5.6,
    "Oregon": 2.2,
    "Memphis": 1.8,
    "Clemson": 7.2,
    "Michigan": 4.5,
    "BYU": 3.7,
    "Missouri": 3.2,
    "Illinois": 5.9,
    "Ole Miss": 3.8,
    "Saint Mary's": 3.0,
    "Kansas": 5.1,
    "UCLA": 2.3,
    "Marquette": 3.7,
    "Gonzaga": 6.7,
    "Connecticut": 3.7,
    "Louisville": 6.2,
    "Mississippi State": 1.0,
    "Baylor": 1.3,
    "Oklahoma": 0.7,
    "Georgia": 0.9,
    "Creighton": 1.8,
    "Utah State": 0.5,
    "Arkansas": 0.5,
    "New Mexico": 1.1,
    "Vanderbilt": 0.4,
    "VCU": 2.6,
    "Drake": 1.4,
    "UNC/San Diego State": 0.9,
    "Texas/Xavier": 2.6,
    "Colorado State": 2.0,
    "Liberty": 0.4,
    "McNeese": 0.3,
    "UC San Diego": 1.4,
    "Grand Canyon": 0.3,
    "High Point": 0.4,
    "Yale": 0.4,
    "Akron": 0.1,
    "UNC Wilmington": 0.1,
    "Troy": 0.1,
    "Lipscomb": 0.1,
    "Montana": 0.0,
    "Omaha": 0.0,
    "Wofford": 0.0,
    "Bryant": 0.0,
    "Robert Morris": 0.0,
    "American/Mount St. Mary's": 0.0,
    "Norfolk State": 0.0,
    "SIUE": 0.0,
    "Alabama State/Saint Francis": 0.0}
elite_eight_odds_2025_538 = {
    "Duke": 71.0,
    "Florida": 58.6,
    "Houston": 56.2,
    "Auburn": 56.5,
    "Alabama": 45.5,
    "Saint John's": 38.9,
    "Tennessee": 47.4,
    "Michigan State": 40.3,
    "Wisconsin": 20.7,
    "Texas Tech": 31.2,
    "Kentucky": 18.5,
    "Iowa State": 26.0,
    "Arizona": 15.2,
    "Maryland": 19.8,
    "Purdue": 10.6,
    "Texas A&M": 12.2,
    "Oregon": 6.2,
    "Memphis": 4.7,
    "Clemson": 15.4,
    "Michigan": 9.6,
    "BYU": 12.7,
    "Missouri": 9.5,
    "Illinois": 15.4,
    "Ole Miss": 10.7,
    "Saint Mary's": 10.5,
    "Kansas": 13.0,
    "UCLA": 7.6,
    "Marquette": 10.7,
    "Gonzaga": 13.0,
    "Connecticut": 8.5,
    "Louisville": 12.2,
    "Mississippi State": 2.7,
    "Baylor": 3.4,
    "Oklahoma": 2.0,
    "Georgia": 2.3,
    "Creighton": 4.3,
    "Utah State": 2.4,
    "Arkansas": 2.0,
    "New Mexico": 3.9,
    "Vanderbilt": 2.1,
    "VCU": 8.1,
    "Drake": 4.9,
    "UNC/San Diego State": 3.3,
    "Texas/Xavier": 7.8,
    "Colorado State": 5.2,
    "Liberty": 1.1,
    "McNeese": 1.1,
    "UC San Diego": 4.0,
    "Grand Canyon": 1.1,
    "High Point": 1.4,
    "Yale": 1.3,
    "Akron": 0.3,
    "UNC Wilmington": 0.4,
    "Troy": 0.6,
    "Lipscomb": 0.5,
    "Montana": 0.2,
    "Omaha": 0.1,
    "Wofford": 0.3,
    "Bryant": 0.2,
    "Robert Morris": 0.3,
    "American/Mount St. Mary's": 0.0,
    "Norfolk State": 0.1,
    "SIUE": 0.0,
    "Alabama State/Saint Francis": 0.0}
sweet_sixteen_odds_2025_538 = {
    "Duke": 88.9,
    "Florida": 78.2,
    "Houston": 73.6,
    "Auburn": 71.5,
    "Alabama": 69.3,
    "Saint John's": 68.4,
    "Tennessee": 73.2,
    "Michigan State": 66.1,
    "Wisconsin": 46.8,
    "Texas Tech": 59.0,
    "Kentucky": 42.3,
    "Iowa State": 54.0,
    "Arizona": 56.2,
    "Maryland": 53.9,
    "Purdue": 34.9,
    "Texas A&M": 41.1,
    "Oregon": 34.0,
    "Memphis": 19.0,
    "Clemson": 48.5,
    "Michigan": 32.0,
    "BYU": 32.9,
    "Missouri": 24.0,
    "Illinois": 34.5,
    "Ole Miss": 24.4,
    "Saint Mary's": 22.3,
    "Kansas": 25.3,
    "UCLA": 17.7,
    "Marquette": 22.7,
    "Gonzaga": 21.3,
    "Connecticut": 16.7,
    "Louisville": 20.2,
    "Mississippi State": 5.8,
    "Baylor": 7.0,
    "Oklahoma": 4.7,
    "Georgia": 5.0,
    "Creighton": 8.3,
    "Utah State": 7.4,
    "Arkansas": 5.8,
    "New Mexico": 9.9,
    "Vanderbilt": 6.5,
    "VCU": 18.9,
    "Drake": 14.6,
    "UNC/San Diego State": 10.2,
    "Texas/Xavier": 20.0,
    "Colorado State": 20.5,
    "Liberty": 7.1,
    "McNeese": 7.5,
    "UC San Diego": 19.1,
    "Grand Canyon": 6.6,
    "High Point": 9.1,
    "Yale": 7.8,
    "Akron": 2.8,
    "UNC Wilmington": 2.3,
    "Troy": 3.2,
    "Lipscomb": 2.5,
    "Montana": 1.4,
    "Omaha": 0.7,
    "Wofford": 1.7,
    "Bryant": 1.3,
    "Robert Morris": 1.8,
    "American/Mount St. Mary's": 0.2,
    "Norfolk State": 0.4,
    "SIUE": 0.1,
    "Alabama State/Saint Francis": 0.0}
round_32_odds_2025_538 = {
    "Duke": 98.5,
    "Florida": 97.3,
    "Houston": 98.2,
    "Auburn": 98.7,
    "Alabama": 92.7,
    "Saint John's": 95.5,
    "Tennessee": 93.4,
    "Michigan State": 93.4,
    "Wisconsin": 89.8,
    "Texas Tech": 89.7,
    "Kentucky": 83.8,
    "Iowa State": 88.3,
    "Arizona": 88.4,
    "Maryland": 81.4,
    "Purdue": 71.3,
    "Texas A&M": 75.4,
    "Oregon": 74.0,
    "Memphis": 48.7,
    "Clemson": 78.7,
    "Michigan": 59.1,
    "BYU": 59.9,
    "Missouri": 58.3,
    "Illinois": 59.9,
    "Ole Miss": 54.5,
    "Saint Mary's": 68.6,
    "Kansas": 72.2,
    "UCLA": 63.5,
    "Marquette": 63.2,
    "Gonzaga": 71.0,
    "Connecticut": 68.6,
    "Louisville": 63.5,
    "Mississippi State": 47.2,
    "Baylor": 52.8,
    "Oklahoma": 31.4,
    "Georgia": 29.0,
    "Creighton": 36.5,
    "Utah State": 36.5,
    "Arkansas": 27.8,
    "New Mexico": 36.8,
    "Vanderbilt": 31.4,
    "VCU": 40.1,
    "Drake": 41.7,
    "UNC/San Diego State": 45.5,
    "Texas/Xavier": 40.1,
    "Colorado State": 51.3,
    "Liberty": 26.0,
    "McNeese": 21.3,
    "UC San Diego": 40.9,
    "Grand Canyon": 18.6,
    "High Point": 28.7,
    "Yale": 24.6,
    "Akron": 11.6,
    "UNC Wilmington": 10.3,
    "Troy": 16.2,
    "Lipscomb": 11.7,
    "Montana": 10.2,
    "Omaha": 4.5,
    "Wofford": 6.6,
    "Bryant": 6.6,
    "Robert Morris": 7.3,
    "American/Mount St. Mary's": 1.5,
    "Norfolk State": 2.7,
    "SIUE": 1.8,
    "Alabama State/Saint Francis": 1.2}


fanduel_champ_odds_2025 = {
    "Duke": 290,
    "Florida": 390,
    "Auburn": 500,
    "Houston": 700,
    "Alabama": 2000,
    "Tennessee": 2200,
    "Texas Tech": 2800,
    "Iowa State": 2900,
    "Michigan State": 3000,
    "Saint John's": 3100,
    "Arizona": 3900,
    "Gonzaga": 4500,
    "Kentucky": 5500,
    "Wisconsin": 6000,
    "Illinois": 6000,
    "Missouri": 7500,
    "Maryland": 7500,
    "Kansas": 7500,
    "Texas A&M": 9500,
    "Clemson": 11000,
    "BYU": 11000,
    "Purdue": 11000,
    "Louisville": 12000,
    "Saint Mary's": 13000,
    "Connecticut": 14000,
    "Marquette": 15000,
    "Ole Miss": 15000,
    "UCLA": 16000,
    "Michigan": 18000,
    "Baylor": 21000,
    "Oregon": 23000,
    "Mississippi State": 23000,
    "Creighton": 25000,
    "VCU": 30000,
    "UNC/San Diego State": 23628,
    "Vanderbilt": 55000,
    "Arkansas": 75000,
    "Texas/Xavier": 48669,
    "Colorado State": 95000,
    "Georgia": 95000,
    "Memphis": 100000,
    "Oklahoma": 100000,
    "Utah State": 100000,
    "New Mexico": 100000,
    "Drake": 1000000,
    "Liberty": 1000000,
    "McNeese": 1000000,
    "UC San Diego": 1000000,
    "Grand Canyon": 1000000,
    "High Point": 1000000,
    "Yale": 1000000,
    "Akron": 1000000,
    "UNC Wilmington": 1000000,
    "Troy": 1000000,
    "Lipscomb": 1000000,
    "Montana": 1000000,
    "Omaha": 1000000,
    "Wofford": 1000000,
    "Bryant": 1000000,
    "Robert Morris": 1000000,
    "American/Mount St. Mary's": 1000000,
    "Norfolk State": 1000000,
    "SIUE": 1000000,
    "Alabama State/Saint Francis": 1000000 }
fanduel_second_place_odds_2025 = {
    "Duke": 160,
    "Florida": 196,
    "Auburn": 250,
    "Houston": 350,
    "Alabama": 890,
    "Tennessee": 1000,
    "Texas Tech": 1160,
    "Iowa State": 1380,
    "Michigan State": 1200,
    "Saint John's": 3100,
    "Arizona": 1550,
    "Gonzaga": 1600,
    "Kentucky": 1800,
    "Wisconsin": 2500,
    "Illinois": 3000,
    "Missouri": 2900,
    "Maryland": 2100,
    "Kansas": 2900,
    "Texas A&M": 2900,
    "Clemson": 4200,
    "BYU": 3900,
    "Purdue": 3600,
    "Louisville": 4400,
    "Saint Mary's": 4700,
    "Connecticut": 6000,
    "Marquette": 7500,
    "Ole Miss": 5500,
    "UCLA": 6000,
    "Michigan": 6500,
    "Baylor": 9500,
    "Oregon": 8500,
    "Mississippi State": 10000,
    "Creighton": 9000,
    "VCU": 9000,
    "UNC/San Diego State": 9200,
    "Vanderbilt": 20000,
    "Arkansas": 18000,
    "Texas/Xavier": 13000,
    "Colorado State": 24000,
    "Georgia": 24000,
    "Memphis": 37000,
    "Oklahoma": 30000,
    "Utah State": 100000,
    "New Mexico": 30000,
    "Drake": 50000,
    "Liberty": 100000,
    "McNeese": 40000,
    "UC San Diego": 22000,
    "Grand Canyon": 100000,
    "High Point": 100000,
    "Yale": 40000,
    "Akron": 1000000,
    "UNC Wilmington": 1000000,
    "Troy": 1000000,
    "Lipscomb": 1000000,
    "Montana": 1000000,
    "Omaha": 1000000,
    "Wofford": 1000000,
    "Bryant": 1000000,
    "Robert Morris": 1000000,
    "American/Mount St. Mary's": 1000000,
    "Norfolk State": 1000000,
    "SIUE": 1000000,
    "Alabama State/Saint Francis": 1000000  }
fanduel_final_four_odds_2025 = {
    "Duke": -135,
    "Florida": -125,
    "Auburn": 100,
    "Houston": 140,
    "Alabama": 430,
    "Tennessee": 350,
    "Texas Tech": 500,
    "Iowa State": 500,
    "Michigan State": 500,
    "Saint John's": 630,
    "Arizona": 800,
    "Gonzaga": 850,
    "Kentucky": 850,
    "Wisconsin": 1100,
    "Illinois": 1000,
    "Missouri": 1400,
    "Maryland": 1100,
    "Kansas": 1400,
    "Texas A&M": 1200,
    "Clemson": 1400,
    "BYU": 2000,
    "Purdue": 1400,
    "Louisville": 1800,
    "Saint Mary's": 2300,
    "Connecticut": 2400,
    "Marquette": 2200,
    "Ole Miss": 2100,
    "UCLA": 2000,
    "Michigan": 2200,
    "Baylor": 3600,
    "Oregon": 3100,
    "Mississippi State": 3600,
    "Creighton": 3300,
    "VCU": 3700,
    "UNC/San Diego State": 3472,
    "Vanderbilt": 7500,
    "Arkansas": 7500,
    "Texas/Xavier": 4822,
    "Colorado State": 6000,
    "Georgia": 7500,
    "Memphis": 8500,
    "Oklahoma": 8500,
    "Utah State": 10000,
    "New Mexico": 7500,
    "Drake": 16000,
    "Liberty": 25000,
    "McNeese": 10000,
    "UC San Diego": 5500,
    "Grand Canyon": 25000,
    "High Point": 25000,
    "Yale": 17000,
    "Akron": 25000,
    "UNC Wilmington": 25000,
    "Troy": 1000000,
    "Lipscomb": 1000000,
    "Montana": 1000000,
    "Omaha": 1000000,
    "Wofford": 1000000,
    "Bryant": 1000000,
    "Robert Morris": 1000000,
    "American/Mount St. Mary's": 1000000,
    "Norfolk State": 1000000,
    "SIUE": 1000000,
    "Alabama State/Saint Francis": 1000000 }
fanduel_elite_eight_odds_2025 = {
    "Duke": -240,
    "Florida": -260,
    "Auburn": -192,
    "Houston": -136,
    "Alabama": 122,
    "Tennessee": 126,
    "Texas Tech": 178,
    "Iowa State": 178,
    "Michigan State": 164,
    "Saint John's": 210,
    "Arizona": 390,
    "Gonzaga": 450,
    "Kentucky": 320,
    "Wisconsin": 300,
    "Illinois": 400,
    "Missouri": 490,
    "Maryland": 460,
    "Kansas": 490,
    "Texas A&M": 600,
    "Clemson": 610,
    "BYU": 590,
    "Purdue": 640,
    "Louisville": 920,
    "Saint Mary's": 690,
    "Connecticut": 1080,
    "Marquette": 790,
    "Ole Miss": 720,
    "UCLA": 700,
    "Michigan": 1020,
    "Baylor": 1600,
    "Oregon": 1380,
    "Mississippi State": 1750,
    "Creighton": 1550,
    "VCU": 1040,
    "UNC/San Diego State": 1096,
    "Vanderbilt": 1750,
    "Arkansas": 1650,
    "Texas/Xavier": 1550,
    "Colorado State": 2000,
    "Georgia": 3200,
    "Memphis": 2800,
    "Oklahoma": 2900,
    "Utah State": 2800,
    "New Mexico": 1800,
    "Drake": 3800,
    "Liberty": 10000,
    "McNeese": 3400,
    "UC San Diego": 2000,
    "Grand Canyon": 10000,
    "High Point": 10000,
    "Yale": 6500,
    "Akron": 25000,
    "UNC Wilmington": 25000,
    "Troy": 15000,
    "Lipscomb": 15000,
    "Montana": 25000,
    "Omaha": 25000,
    "Wofford": 25000,
    "Bryant": 50000,
    "Robert Morris": 25000,
    "American/Mount St. Mary's": 100000,
    "Norfolk State": 100000,
    "SIUE": 100000,
    "Alabama State/Saint Francis": 100000}
fanduel_sweet_sixteen_odds_2025 = {
    "Duke": -700,
    "Florida": -700,
    "Auburn": -430,
    "Houston": -300,
    "Alabama": -250,
    "Tennessee": -260,
    "Texas Tech": -172,
    "Iowa State": -156,
    "Michigan State": -215,
    "Saint John's": -146,
    "Arizona": -196,
    "Gonzaga": 280,
    "Kentucky": 104,
    "Wisconsin": -118,
    "Illinois": 148,
    "Missouri": 194,
    "Maryland": -156,
    "Kansas": 200,
    "Texas A&M": 114,
    "Clemson": 124,
    "BYU": 215,
    "Purdue": 130,
    "Louisville": 550,
    "Saint Mary's": 320,
    "Connecticut": 630,
    "Marquette": 290,
    "Ole Miss": 270,
    "UCLA": 290,
    "Michigan": 215,
    "Baylor": 960,
    "Oregon": 235,
    "Mississippi State": 880,
    "Creighton": 840,
    "VCU": 380,
    "UNC/San Diego State": 433,
    "Vanderbilt": 740,
    "Arkansas": 610,
    "Texas/Xavier": 547,
    "Colorado State": 350,
    "Georgia": 1550,
    "Memphis": 460,
    "Oklahoma": 1480,
    "Utah State": 1000,
    "New Mexico": 670,
    "Drake": 1160,
    "Liberty": 1220,
    "McNeese": 700,
    "UC San Diego": 390,
    "Grand Canyon": 1320,
    "High Point": 1260,
    "Yale": 920,
    "Akron": 2200,
    "UNC Wilmington": 3600,
    "Troy": 2200,
    "Lipscomb": 3200,
    "Montana": 10000,
    "Omaha": 13000,
    "Wofford": 8000,
    "Bryant": 8000,
    "Robert Morris": 15000,
    "American/Mount St. Mary's": 25000,
    "Norfolk State": 25000,
    "SIUE": 25000,
    "Alabama State/Saint Francis": 25000}
fanduel_round_32_odds_2025 = {
    "Duke": -30000,
    "Florida": -30000,
    "Auburn": -30000,
    "Houston": -50000,
    "Alabama": -7000,
    "Tennessee": -4000,
    "Texas Tech": -2000,
    "Iowa State": -1300,
    "Michigan State": -3500,
    "Saint John's": -3500,
    "Arizona": -1100,
    "Gonzaga": -265,
    "Kentucky": -610,
    "Wisconsin": -2500,
    "Illinois": -164,
    "Missouri": -275,
    "Maryland": -600,
    "Kansas": -192,
    "Texas A&M": -315,
    "Clemson": -345,
    "BYU": -152,
    "Purdue": -335,
    "Louisville": -138,
    "Saint Mary's": -170,
    "Connecticut": -178,
    "Marquette": -166,
    "Ole Miss": -131,
    "UCLA": -205,
    "Michigan": -142,
    "Baylor": 105,
    "Oregon": -265,
    "Mississippi State": -126,
    "Creighton": 115,
    "VCU": 126,
    "UNC/San Diego State": 110,
    "Vanderbilt": 140,
    "Arkansas": 158,
    "Texas/Xavier": 136,
    "Colorado State": -128,
    "Georgia": 215,
    "Memphis": 106,
    "Oklahoma": 146,
    "Utah State": 168,
    "New Mexico": 138,
    "Drake": 220,
    "Liberty": 215,
    "McNeese": 270,
    "UC San Diego": 118,
    "Grand Canyon": 430,
    "High Point": 265,
    "Yale": 250,
    "Akron": 680,
    "UNC Wilmington": 980,
    "Troy": 440,
    "Lipscomb": 760,
    "Montana": 1100,
    "Omaha": 1280,
    "Wofford": 1400,
    "Bryant": 1280,
    "Robert Morris": 2000,
    "American/Mount St. Mary's": 5000,
    "Norfolk State": 5000,
    "SIUE": 5500,
    "Alabama State/Saint Francis": 5000}


champ_odds_2024 = {
    "Connecticut": 23.4,
    "Purdue": 13.2,
    "Arizona": 10.5,
    "Houston": 9.8,
    "Tennessee": 7.7,
    "Auburn": 7.3,
    "UNC": 4.4,
    "Iowa State": 4.1,
    "Duke": 3.8,
    "Creighton": 2.5,
    "Illinois": 2.0,
    "Alabama": 1.4,
    "Kentucky": 1.2,
    "Gonzaga": 1.2,
    "Marquette": 0.8,
    "Florida": 0.6,
    "Baylor": 0.7,
    "Michigan State": 0.6,
    "Kansas": 0.5,
    "Wisconsin": 0.7,
    "BYU": 0.5,
    "New Mexico": 0.3,
    "Texas": 0.3,
    "Texas Tech": 0.3,
    "Nebraska": 0.2,
    "TCU": 0.2,
    "Mississippi State": 0.2,
    "Washington State": 0.2,
    "Clemson": 0.2,
    "Florida Atlantic": 0.2,
    "James Madison": 0.2,
    "San Diego State": 0.2,
    "Northwestern": 0.1,
    "Saint Mary's": 0.2,
    "Texas A&M": 0.1,
    "Dayton": 0.1,
    "Drake": 0.1,
    "South Carolina": 0.1,
    "Virginia/Colorado State": 0.1,
    "Vermont": 0.0,
    "Boise State/Colorado": 0.1,
    "NC State": 0.0,
    "Nevada": 0.0,
    "McNeese State": 0.0,
    "Oregon": 0.0,
    "Grand Canyon": 0.0,
    "Utah State": 0.0,
    "Yale": 0.0,
    "College of Charleston": 0.0,
    "Western Kentucky": 0.0,
    "UAB": 0.0,
    "Akron": 0.0,
    "Duquesne": 0.0,
    "Samford": 0.0,
    "Colgate": 0.0,
    "Morehead State": 0.0,
    "Oakland": 0.0,
    "Longwood": 0.0,
    "South Dakota State": 0.0,
    "Stetson": 0.0,
    "Long Beach State": 0.0,
    "Howard/Wagner": 0,
    "Montana State/Grambling": 0,
    "Saint Peter's": 0.0,
    }
second_place_odds_2024 = {
    "Connecticut": 33.2,
    "Purdue": 25.4,
    "Arizona": 18.7,
    "Houston": 20.3,
    "Tennessee": 16.5,
    "Auburn": 12.4,
    "UNC": 9.8,
    "Iowa State": 8.9,
    "Duke": 8.9,
    "Creighton": 7.4,
    "Illinois": 4.4,
    "Alabama": 3.6,
    "Kentucky": 4.7,
    "Gonzaga": 3.5,
    "Marquette": 2.3,
    "Florida": 2.1,
    "Baylor": 2.0,
    "Michigan State": 1.2,
    "Kansas": 1.2,
    "Wisconsin": 1.7,
    "BYU": 1.3,
    "New Mexico": 1.0,
    "Texas": 0.9,
    "Texas Tech": 1.1,
    "Nebraska": 0.7,
    "TCU": 0.5,
    "Mississippi State": 0.6,
    "Washington State": 0.5,
    "Clemson": 0.4,
    "Florida Atlantic": 0.4,
    "James Madison": 0.4,
    "San Diego State": 0.5,
    "Northwestern": 0.2,
    "Saint Mary's": 0.6,
    "Texas A&M": 0.6,
    "Dayton": 0.3,
    "Drake": 0.3,
    "South Carolina": 0.2,
    "Virginia/Colorado State": 0.1,
    "Vermont": 0.1,
    "Boise State/Colorado": 0.4,
    "NC State": 0.2,
    "Nevada": 0.2,
    "McNeese State": 0.1,
    "Oregon": 0.1,
    "Grand Canyon": 0.1,
    "Utah State": 0.1,
    "Yale": 0.1,
    "College of Charleston": 0.1,
    "Western Kentucky": 0.1,
    "UAB": 0.1,
    "Akron": 0.0,
    "Duquesne": 0.0,
    "Samford": 0.0,
    "Colgate": 0.0,
    "Morehead State": 0.0,
    "Oakland": 0.0,
    "Longwood": 0.0,
    "South Dakota State": 0.0,
    "Stetson": 0.0,
    "Long Beach State": 0.0,
    "Howard/Wagner": 0,
    "Montana State/Grambling": 0,
    "Saint Peter's": 0.0,
    }
final_four_odds_2024 = {
    "Connecticut": 43.1,
    "Purdue": 39.4,
    "Arizona": 40.8,
    "Houston": 35.4,
    "Tennessee": 27.4,
    "Auburn": 19.1,
    "UNC": 20.3,
    "Iowa State": 18.0,
    "Duke": 19.1,
    "Creighton": 14.4,
    "Illinois": 9.8,
    "Alabama": 12.2,
    "Kentucky": 13.0,
    "Gonzaga": 8.0,
    "Marquette": 7.7,
    "Florida": 6.8,
    "Baylor": 8.8,
    "Michigan State": 3.9,
    "Kansas": 2.4,
    "Wisconsin": 5.2,
    "BYU": 3.4,
    "New Mexico": 3.7,
    "Texas": 1.5,
    "Texas Tech": 3.8,
    "Nebraska": 2.0,
    "TCU": 1.8,
    "Mississippi State": 2.5,
    "Washington State": 1.7,
    "Clemson": 1.7,
    "Florida Atlantic": 1.2,
    "James Madison": 1.2,
    "San Diego State": 2.0,
    "Northwestern": 0.8,
    "Saint Mary's": 3.2,
    "Texas A&M": 1.0,
    "Dayton": 0.9,
    "Drake": 0.9,
    "South Carolina": 0.4,
    "Virginia/Colorado State": 0.5,
    "Vermont": 0.2,
    "Boise State/Colorado": 1.8,
    "NC State": 0.7,
    "Nevada": 0.7,
    "McNeese State": 0.3,
    "Oregon": 0.3,
    "Grand Canyon": 0.7,
    "Utah State": 0.1,
    "Yale": 0.1,
    "College of Charleston": 0.1,
    "Western Kentucky": 0.1,
    "UAB": 0.1,
    "Akron": 0.1,
    "Duquesne": 0.0,
    "Samford": 0.0,
    "Colgate": 0.0,
    "Morehead State": 0.0,
    "Oakland": 0.0,
    "Longwood": 0.0,
    "South Dakota State": 0.0,
    "Stetson": 0.0,
    "Long Beach State": 0.0,
    "Howard/Wagner": 0,
    "Montana State/Grambling": 0,
    "Saint Peter's": 0.0,
    }
elite_eight_odds_2024 = {
    "Connecticut": 57.7,
    "Purdue": 62.7,
    "Arizona": 59.5,
    "Houston": 48.4,
    "Tennessee": 50.0,
    "Auburn": 29.4,
    "UNC": 39.7,
    "Iowa State": 43.3,
    "Duke": 28.3,
    "Creighton": 32.9,
    "Illinois": 30.3,
    "Alabama": 29.9,
    "Kentucky": 32.8,
    "Gonzaga": 17.2,
    "Marquette": 24.6,
    "Florida": 17.3,
    "Baylor": 19.3,
    "Michigan State": 10.4,
    "Kansas": 12.4,
    "Wisconsin": 9.9,
    "BYU": 15.7,
    "New Mexico": 8.6,
    "Texas": 8.6,
    "Texas Tech": 14.2,
    "Nebraska": 4.9,
    "TCU": 5.6,
    "Mississippi State": 7.4,
    "Washington State": 5.9,
    "Clemson": 5.5,
    "Florida Atlantic": 3.7,
    "James Madison": 3.7,
    "San Diego State": 5.9,
    "Northwestern": 2.5,
    "Saint Mary's": 9.4,
    "Texas A&M": 4.2,
    "Dayton": 3.8,
    "Drake": 3.9,
    "South Carolina": 2.8,
    "Virginia/Colorado State": 2.0,
    "Vermont": 0.4,
    "Boise State/Colorado": 6.4,
    "NC State": 3.7,
    "Nevada": 3.2,
    "McNeese State": 1.3,
    "Oregon": 3.0,
    "Grand Canyon": 2.3,
    "Utah State": 0.5,
    "Yale": 0.4,
    "College of Charleston": 0.9,
    "Western Kentucky": 0.8,
    "UAB": 0.3,
    "Akron": 0.7,
    "Duquesne": 0.7,
    "Samford": 0.3,
    "Colgate": 0.2,
    "Morehead State": 0.2,
    "Oakland": 0.2,
    "Longwood": 0.1,
    "South Dakota State": 0.1,
    "Stetson": 0.1,
    "Long Beach State": 0,
    "Howard/Wagner": 0,
    "Montana State/Grambling": 0,
    "Saint Peter's": 0,   
    }
sweet_sixteen_odds_2024 = {
    "Connecticut": 81.3,
    "Purdue": 83.7,
    "Arizona": 79.9,
    "Houston": 74.5,
    "Tennessee": 74.7,
    "Auburn": 68.6,
    "UNC": 63.1,
    "Iowa State": 69.1,
    "Duke": 55.6,
    "Creighton": 68.4,
    "Illinois": 59.0,
    "Alabama": 61.6,
    "Kentucky": 56.1,
    "Gonzaga": 48.9,
    "Marquette": 48.4,
    "Florida": 32.6,
    "Baylor": 54.1,
    "Michigan State": 20.3,
    "Kansas": 40.2,
    "Wisconsin": 25.4,
    "BYU": 35.6,
    "New Mexico": 26.5,
    "Texas": 19,
    "Texas Tech": 29.8,
    "Nebraska": 13.3,
    "TCU": 13.2,
    "Mississippi State": 16.5,
    "Washington State": 15.7,
    "Clemson": 17.9,
    "Florida Atlantic": 11.2,
    "James Madison": 15.0,
    "San Diego State": 23.4,
    "Northwestern": 7.2,
    "Saint Mary's": 25.5,
    "Texas A&M": 11.6,
    "Dayton": 10.4,
    "Drake": 13.3,
    "South Carolina": 13.9,
    "Virginia/Colorado State": 6.3,
    "Vermont": 4.0,
    "Boise State/Colorado": 16.4,
    "NC State": 12.9,
    "Nevada": 9.4,
    "McNeese State": 7.7,
    "Oregon": 13.6,
    "Grand Canyon": 9.1,
    "Utah State": 2.9,
    "Yale": 4.9,
    "College of Charleston": 3.8,
    "Western Kentucky": 2.5,
    "UAB": 3.1,
    "Akron": 4.1,
    "Duquesne": 4.3,
    "Samford": 3.2,
    "Colgate": 1.5,
    "Morehead State": 1.2,
    "Oakland": 1.2,
    "Longwood": 0.7,
    "South Dakota State": 1.9,
    "Stetson": 0.3,
    "Long Beach State": 0.4,
    "Howard/Wagner": 0.1,
    "Montana State/Grambling": 0.1,
    "Saint Peter's": 0,
    }
round_32_odds_2024 = {
    "Connecticut": 97.7,
    "Purdue": 99.1,
    "Arizona": 96.8,
    "Houston": 96.5,
    "Tennessee": 98.7,
    "Auburn": 88.2,
    "UNC": 98.1,
    "Iowa State": 91.3,
    "Duke": 85.9,
    "Creighton": 88.5,
    "Illinois": 91.8,
    "Alabama": 87,
    "Kentucky": 92.2,
    "Gonzaga": 78.4,
    "Marquette": 87.5,
    "Florida": 61.9,
    "Baylor": 90.9,
    "Michigan State": 53.2,
    "Kansas": 81.5,
    "Wisconsin": 56.9,
    "BYU": 78.9,
    "New Mexico": 55.1,
    "Texas": 66.6,
    "Texas Tech": 62.4,
    "Nebraska": 50.5,
    "TCU": 69.5,
    "Mississippi State": 46.8,
    "Washington State": 53.8,
    "Clemson": 44.9,
    "Florida Atlantic": 57.6,
    "James Madison": 43.1,
    "San Diego State": 75.5,
    "Northwestern": 42.4,
    "Saint Mary's": 65.1,
    "Texas A&M": 49.5,
    "Dayton": 50.6,
    "Drake": 46.2,
    "South Carolina": 51.7,
    "Virginia/Colorado State": 33.4,
    "Vermont": 14.1,
    "Boise State/Colorado": 38,
    "NC State": 37.6,
    "Nevada": 49.4,
    "McNeese State": 21.6,
    "Oregon": 48.3,
    "Grand Canyon": 34.9,
    "Utah State": 30.5,
    "Yale": 11.8,
    "College of Charleston": 13.0,
    "Western Kentucky": 12.5,
    "UAB": 24.5,
    "Akron": 11.5,
    "Duquesne": 21.1,
    "Samford": 18.5,
    "Colgate": 9.1,
    "Morehead State": 8.2,
    "Oakland": 7.8,
    "Longwood": 3.5,
    "South Dakota State": 8.7,
    "Stetson": 2.3,
    "Long Beach State": 3.2,
    "Howard/Wagner": 1.9,
    "Montana State/Grambling": 0.9,
    "Saint Peter's": 1.3,
    }

champ_odds_2023 = {
    "Houston": 15.0,
    "Alabama": 13.5,
    "UCLA": 10.6,
    "Purdue": 6.3,
    "Texas": 6.0,
    "Tennessee": 5.7,
    "Connecticut": 5.1,
    "Gonzaga": 4.7,
    "Arizona": 4.1,
    "Kansas": 3.8,
    "Marquette": 3.3,
    "Saint Mary's": 1.8,
    "Creighton": 1.7,
    "San Diego State": 1.7,
    "Baylor": 1.6,
    "Xavier": 1.6,
    "Kansas State": 1.1,
    "Utah State": 0.9,
    "Iowa State": 0.9,
    "Duke": 0.8,
    "Kentucky": 0.8,
    "West Virginia": 0.7,
    "Texas A&M": 0.7,
    "Indiana": 0.7,
    "Memphis": 0.6,
    "Maryland": 0.6,
    "Arkansas": 0.5,
    "Virginia": 0.5,
    "Florida Atlantic": 0.5,
    "Michigan State": 0.5,
    "Auburn": 0.5,
    "TCU": 0.5,
    "Boise State": 0.3,
    "USC": 0.3,
    "Miami FL": 0.3,
    "Providence": 0.2,
    "Iowa": 0.2,
    "Illinois": 0.2,
    "Penn State": 0.2,
    "Northwestern": 0.1,
    "Missouri": 0.1,
    "NC State": 0.10,
    "Drake": 0.10,
    "Oral Roberts": 0.08,
    "Nevada/Arizona State": 0.09,
    "Kent State": 0.06,
    "VCU": 0.06,
    "Charleston": 0.04,
    "Iona": 0.03,
    "Pittsburgh": 0.11,
    "Furman": 0.01,
    "Louisiana": 0.007,
    "UC Santa Barbara": 0.005,
    "Montana State": 0.005,
    "Vermont": 0.004,
    "Grand Canyon": 0.002,
    "Princeton": 0.002,
    "Colgate": 0.001,
    "Kennesaw State": 0.001,
    "Northern Kentucky": 0.001,
    "UNC Asheville": 0.001,
    "Texas A&M Corpus Chris": 0.002,
    "Howard": 0.001,
    "FDU/Texas Southern": 0.001
    }
second_place_odds_2023 = {
    "Houston": 23.5,
    "Alabama": 23.4,
    "UCLA": 17.3,
    "Purdue": 12.7,
    "Texas": 11.0,
    "Tennessee": 11.3,
    "Connecticut": 9.0,
    "Gonzaga": 8.7,
    "Arizona": 9.0,
    "Kansas": 7.5,
    "Marquette": 7.7,
    "Saint Mary's": 3.8,
    "Creighton": 4.2,
    "San Diego State": 4.2,
    "Baylor": 4.1,
    "Xavier": 3.8,
    "Kansas State": 3.3,
    "Utah State": 2.5,
    "Iowa State": 2.1,
    "Duke": 2.2,
    "Kentucky": 2.2,
    "West Virginia": 1.8,
    "Texas A&M": 1.7,
    "Indiana": 1.8,
    "Memphis": 1.7,
    "Maryland": 1.5,
    "Arkansas": 1.4,
    "Virginia": 1.6,
    "Florida Atlantic": 1.5,
    "Michigan State": 1.5,
    "Auburn": 1.3,
    "TCU": 1.3,
    "Boise State": 0.9,
    "USC": 1.0,
    "Miami FL": 0.8,
    "Providence": 0.8,
    "Iowa": 0.7,
    "Illinois": 0.7,
    "Penn State": 0.6,
    "Northwestern": 0.4,
    "Missouri": 0.5,
    "NC State": 0.4,
    "Drake": 0.4,
    "Oral Roberts": 0.3,
    "Nevada/Arizona State": 0.28,
    "Kent State": 0.3,
    "VCU": 0.2,
    "Charleston": 0.2,
    "Iona": 0.1,
    "Pittsburgh": 0.38,
    "Furman": 0.08,
    "Louisiana": 0.05,
    "UC Santa Barbara": 0.04,
    "Montana State": 0.03,
    "Vermont": 0.03,
    "Grand Canyon": 0.01,
    "Princeton": 0.02,
    "Colgate": 0.01,
    "Kennesaw State": 0.008,
    "Northern Kentucky": 0.003,
    "UNC Asheville": 0.002,
    "Texas A&M Corpus Chris": 0.002,
    "Howard": 0.001,
    "Southern": 0.001,
    "FDU/Texas Southern": 0.001
    }
final_four_odds_2023 = {
    "Houston": 38.6,
    "Alabama": 35.8,
    "UCLA": 29.0,
    "Purdue": 23.5,
    "Texas": 21.3,
    "Tennessee": 20.7,
    "Connecticut": 16.4,
    "Gonzaga": 16.6,
    "Arizona": 16.7,
    "Kansas": 15.1,
    "Marquette": 16.1,
    "Saint Mary's": 7.9,
    "Creighton": 8.7,
    "San Diego State": 8.7,
    "Baylor": 8.8,
    "Xavier": 9.6,
    "Kansas State": 8.4,
    "Utah State": 5.6,
    "Iowa State": 5.6,
    "Duke": 5.4,
    "Kentucky": 5.9,
    "West Virginia": 4.1,
    "Texas A&M": 4.7,
    "Indiana": 5.2,
    "Memphis": 4.2,
    "Maryland": 3.5,
    "Arkansas": 3.5,
    "Virginia": 4.1,
    "Florida Atlantic": 3.8,
    "Michigan State": 4.3,
    "Auburn": 3.8,
    "TCU": 3.4,
    "Boise State": 2.6,
    "USC": 3.2,
    "Miami FL": 2.8,
    "Providence": 2.7,
    "Iowa": 2.2,
    "Illinois": 1.9,
    "Penn State": 2.1,
    "Northwestern": 1.3,
    "Missouri": 1.4,
    "NC State": 1.2,
    "Drake": 1.5,
    "Oral Roberts": 1.2,
    "Nevada/Arizona State": 1.1,
    "Kent State": 1.1,
    "VCU": 0.7,
    "Charleston": 0.6,
    "Iona": 0.4,
    "Pittsburgh": 1.4,
    "Furman": 0.3,
    "Louisiana": 0.2,
    "UC Santa Barbara": 0.2,
    "Montana State": 0.2,
    "Vermont": 0.2,
    "Grand Canyon": 0.09,
    "Princeton": 0.1,
    "Colgate": 0.1,
    "Kennesaw State": 0.06,
    "Northern Kentucky": 0.03,
    "UNC Asheville": 0.01,
    "Texas A&M Corpus Chris": 0.005,
    "Howard": 0.002,
    "Southern": 0.001,
    "FDU/Texas Southern": 0.01
    }
elite_eight_odds_2023 = {
    "Houston": 56.7,
    "Alabama": 52.2,
    "UCLA": 46.5,
    "Purdue": 36.7,
    "Texas": 39.8,
    "Tennessee": 32.1,
    "Connecticut": 31.0,
    "Gonzaga": 30.1,
    "Arizona": 34.0,
    "Kansas": 31.6,
    "Marquette": 33.1,
    "Saint Mary's": 17.5,
    "Creighton": 20.0,
    "San Diego State": 17.4,
    "Baylor": 20.9,
    "Xavier": 22.6,
    "Kansas State": 20.8,
    "Utah State": 14.1,
    "Iowa State": 14.0,
    "Duke": 10.8,
    "Kentucky": 14.9,
    "West Virginia": 8.7,
    "Texas A&M": 11.7,
    "Indiana": 12.2,
    "Memphis": 8.3,
    "Maryland": 7.7,
    "Arkansas": 9.4,
    "Virginia": 9.9,
    "Florida Atlantic": 7.7,
    "Michigan State": 11.5,
    "Auburn": 9.0,
    "TCU": 8.6,
    "Boise State": 6.7,
    "USC": 9.2,
    "Miami FL": 7.6,
    "Providence": 8.1,
    "Iowa": 5.9,
    "Illinois": 5.9,
    "Penn State": 6.1,
    "Northwestern": 4.1,
    "Missouri": 4.8,
    "NC State": 4.4,
    "Drake": 4.6,
    "Oral Roberts": 3.2,
    "Nevada/Arizona State": 3.4,
    "Kent State": 3.7,
    "VCU": 2.8,
    "Charleston": 2.7,
    "Iona": 1.9,
    "Pittsburgh": 4.7,
    "Furman": 1.4,
    "Louisiana": 1.0,
    "UC Santa Barbara": 1.1,
    "Montana State": 1.2,
    "Vermont": 1.1,
    "Grand Canyon": 0.5,
    "Princeton": 0.7,
    "Colgate": 0.6,
    "Kennesaw State": 0.5,
    "Northern Kentucky": 0.2,
    "UNC Asheville": 0.1,
    "Texas A&M Corpus Chris": 0.041,
    "Howard": 0.03,
    "Southern": 0.03,
    "FDU/Texas Southern": 0.01
    }
sweet_sixteen_odds_2023 = {
    "Houston": 71.6,
    "Alabama": 69.8,
    "UCLA": 71.1,
    "Purdue": 63.4,
    "Texas": 60.4,
    "Tennessee": 57.7,
    "Connecticut": 51.1,
    "Gonzaga": 60.3,
    "Arizona": 56.4,
    "Kansas": 60.8,
    "Marquette": 53.2,
    "Saint Mary's": 33.5,
    "Creighton": 39.1,
    "San Diego State": 45.2,
    "Baylor": 42.4,
    "Xavier": 49.3,
    "Kansas State": 42.9,
    "Utah State": 28.0,
    "Iowa State": 32.4,
    "Duke": 26.2,
    "Kentucky": 31.3,
    "West Virginia": 15.7,
    "Texas A&M": 22.9,
    "Indiana": 37.1,
    "Memphis": 18.9,
    "Maryland": 14.2,
    "Arkansas": 22.8,
    "Virginia": 32.1,
    "Florida Atlantic": 17.7,
    "Michigan State": 23.0,
    "Auburn": 15.9,
    "TCU": 24.1,
    "Boise State": 16.4,
    "USC": 19.4,
    "Miami FL": 27.3,
    "Providence": 20.2,
    "Iowa": 11.4,
    "Illinois": 16.0,
    "Penn State": 14.1,
    "Northwestern": 11.4,
    "Missouri": 12.5,
    "NC State": 13.2,
    "Drake": 19.1,
    "Oral Roberts": 11.2,
    "Nevada/Arizona State": 12.2,
    "Kent State": 16.5,
    "VCU": 8.8,
    "Charleston": 13.4,
    "Iona": 6.6,
    "Pittsburgh": 15,
    "Furman": 9.3,
    "Louisiana": 4.9,
    "UC Santa Barbara": 5.3,
    "Montana State": 5.6,
    "Vermont": 4.3,
    "Grand Canyon": 3.5,
    "Princeton": 3.1,
    "Colgate": 2.7,
    "Kennesaw State": 3.4,
    "Northern Kentucky": 1.1,
    "UNC Asheville": 1.0,
    "Texas A&M Corpus Chris": 0.31,
    "Howard": 0.4,
    "Southern": 0.04,
    "FDU/Texas Southern": 0.01
    }
round_32_odds_2023 = {
    "Houston": 93.8,
    "Alabama": 97.6,
    "UCLA": 94.6,
    "Purdue": 98.3,
    "Texas": 88.8,
    "Tennessee": 84.1,
    "Connecticut": 80.1,
    "Gonzaga": 87.0,
    "Arizona": 87.0,
    "Kansas": 95.4,
    "Marquette": 83.7,
    "Saint Mary's": 69.3,
    "Creighton": 67.7,
    "San Diego State": 70.4,
    "Baylor": 78.3,
    "Xavier": 85.0,
    "Kansas State": 78.4,
    "Utah State": 62.4,
    "Iowa State": 62.3,
    "Duke": 62.7,
    "Kentucky": 57.3,
    "West Virginia": 51.8,
    "Texas A&M": 57.6,
    "Indiana": 63.4,
    "Memphis": 51.2,
    "Maryland": 48.2,
    "Arkansas": 55.5,
    "Virginia": 67.7,
    "Florida Atlantic": 48.8,
    "Michigan State": 52.6,
    "Auburn": 54.7,
    "TCU": 60.8,
    "Boise State": 55.4,
    "USC": 47.4,
    "Miami FL": 55.9,
    "Providence": 42.7,
    "Iowa": 45.3,
    "Illinois": 44.5,
    "Penn State": 42.4,
    "Northwestern": 44.6,
    "Missouri": 37.6,
    "NC State": 32.3,
    "Drake": 44.1,
    "Oral Roberts": 37.3,
    "Nevada/Arizona State": 39.2,
    "Kent State": 36.6,
    "VCU": 30.7,
    "Charleston": 29.6,
    "Iona": 19.9,
    "Pittsburgh": 37.7,
    "Furman": 32.3,
    "Louisiana": 15.9,
    "UC Santa Barbara": 21.7,
    "Montana State": 21.6,
    "Vermont": 16.3,
    "Grand Canyon": 13.0,
    "Princeton": 13.0,
    "Colgate": 11.2,
    "Kennesaw State": 15.0,
    "Northern Kentucky": 6.2,
    "UNC Asheville": 5.4,
    "Texas A&M Corpus Chris": 2.5,
    "Howard": 4.6,
    "Southern": 1.1,
    "FDU/Texas Southern": 0.6
    }

champ_odds_2022 = {
    "Gonzaga": 27.5,
    "Arizona": 8.9,
    "Kansas": 6.6,
    "Baylor": 6.4,
    "Kentucky": 6.2,
    "Auburn": 5.6,
    "Tennessee": 5.1,
    "Houston": 5.0,
    "Texas Tech": 4.0,
    "UCLA": 3.8,
    "Villanova": 3.6,
    "Iowa": 3.5,
    "Duke": 3.3,
    "Purdue": 1.9,
    "LSU": 0.9,
    "Texas": 0.7,
    "Saint Mary's": 0.7,
    "Connecticut": 0.7,
    "Illinois": 0.7,
    "Arkansas": 0.5,
    "San Diego State": 0.5,
    "Loyola Chicago": 0.4,
    "San Francisco": 0.3,
    "Wisconsin": 0.3,
    "Virginia Tech": 0.3,
    "Alabama": 0.3,
    "Colorado State": 0.2,
    "Ohio State": 0.2,
    "Murray State": 0.2,
    "Boise State": 0.2,
    "Michigan": 0.2,
    "USC": 0.2,
    "North Carolina": 0.1,
    "Iowa State": 0.1,
    "Providence": 0.1,
    "Memphis": 0.1,
    "Davidson": 0.1,
    "TCU": 0.1,
    "Michigan State": 0.1,
    "Seton Hall": 0.09,
    "Creighton": 0.06,
    "Miami FL": 0.06,
    "UAB": 0.06,
    "Marquette": 0.05,
    "Vermont": 0.05,
    "Indiana": 0.07,
    "Rutgers/ND": 0.048,
    "South Dakota State": 0.03,
    "Chattanooga": 0.02,
    "Richmond": 0.01,
    "New Mexico State": 0.01,
    "Colgate": 0.001,
    "Jacksonville State": 0.001,
    "Montana State": 0.001,
    "Akron": 0.001,
    "Saint Peter's": 0.001,
    "Longwood": 0.001,
    "Delaware": 0.001,
    "Cal State Fullerton": 0.001,
    "Yale": 0.001,
    "Georgia State": 0.001,
    "Norfolk State": 0.001,
    "Texas Southern": 0.001,
    "Wright State": 0.001
    }
second_place_odds_2022 = {
    "Gonzaga": 38.5,
    "Arizona": 18.1,
    "Kansas": 14.6,
    "Baylor": 11.6,
    "Kentucky": 11.0,
    "Auburn": 13.2,
    "Tennessee": 11.4,
    "Houston": 10.5,
    "Texas Tech": 7.9,
    "UCLA": 7.4,
    "Villanova": 8.5,
    "Iowa": 8.7,
    "Duke": 6.7,
    "Purdue": 4.2,
    "LSU": 2.8,
    "Texas": 1.8,
    "Saint Mary's": 1.7,
    "Connecticut": 1.7,
    "Illinois": 2.1,
    "Arkansas": 1.4,
    "San Diego State": 1.6,
    "Loyola Chicago": 1.2,
    "San Francisco": 0.9,
    "Wisconsin": 1.3,
    "Virginia Tech": 0.8,
    "Alabama": 0.8,
    "Colorado State": 0.7,
    "Ohio State": 0.7,
    "Murray State": 0.5,
    "Boise State": 0.5,
    "Michigan": 0.6,
    "USC": 0.7,
    "North Carolina": 0.5,
    "Iowa State": 0.6,
    "Providence": 0.6,
    "Memphis": 0.4,
    "Davidson": 0.4,
    "TCU": 0.4,
    "Michigan State": 0.4,
    "Seton Hall": 0.4,
    "Creighton": 0.3,
    "Miami FL": 0.3,
    "UAB": 0.3,
    "Marquette": 0.2,
    "Vermont": 0.2,
    "Indiana": 0.28,
    "Rutgers/ND": 0.14,
    "South Dakota State": 0.2,
    "Chattanooga": 0.1,
    "Richmond": 0.10,
    "New Mexico State": 0.06,
    "Colgate": 0.01,
    "Jacksonville State": 0.006,
    "Montana State": 0.005,
    "Akron": 0.004,
    "Saint Peter's": 0.004,
    "Longwood": 0.004,
    "Delaware": 0.002,
    "Cal State Fullerton": 0.002,
    "Yale": 0.001,
    "Georgia State": 0.001,
    "Norfolk State": 0.001,
    "Texas Southern": 0.001,
    "Wright State": 0.001
    }
final_four_odds_2022 = {
    "Gonzaga": 53.7,
    "Arizona": 29.1,
    "Kansas": 27.9,
    "Baylor": 25.2,
    "Kentucky": 23.6,
    "Auburn": 26.3,
    "Tennessee": 20.0,
    "Houston": 17.6,
    "Texas Tech": 15.4,
    "UCLA": 17.2,
    "Villanova": 15.7,
    "Iowa": 18.3,
    "Duke": 13.6,
    "Purdue": 11.4,
    "LSU": 7.6,
    "Texas": 5.2,
    "Saint Mary's": 5.1,
    "Connecticut": 4.4,
    "Illinois": 4.7,
    "Arkansas": 3.6,
    "San Diego State": 4.6,
    "Loyola Chicago": 3.1,
    "San Francisco": 3.2,
    "Wisconsin": 4.5,
    "Virginia Tech": 2.8,
    "Alabama": 2.4,
    "Colorado State": 2.0,
    "Ohio State": 1.9,
    "Murray State": 1.9,
    "Boise State": 1.5,
    "Michigan": 1.8,
    "USC": 2.5,
    "North Carolina": 2.0,
    "Iowa State": 2.1,
    "Providence": 2.1,
    "Memphis": 1.2,
    "Davidson": 1.3,
    "TCU": 1.3,
    "Michigan State": 1.3,
    "Seton Hall": 1.3,
    "Creighton": 1.2,
    "Miami FL": 1.4,
    "UAB": 0.8,
    "Marquette": 1.1,
    "Vermont": 0.7,
    "Indiana": 0.11,
    "South Dakota State": 0.9,
    "Chattanooga": 0.5,
    "Richmond": 0.5,
    "New Mexico State": 0.3,
    "Rutgers/ND": 0.7,
    "Colgate": 0.1,
    "Jacksonville State": 0.06,
    "Montana State": 0.03,
    "Akron": 0.05,
    "Saint Peter's": 0.04,
    "Longwood": 0.03,
    "Delaware": 0.03,
    "Cal State Fullerton": 0.02,
    "Yale": 0.02,
    "Georgia State": 0.009,
    "Norfolk State": 0.009,
    "Texas Southern": 0.007,
    "Wright State": 0.004
    }
elite_eight_odds_2022 = {
    "Gonzaga": 70.8,
    "Arizona": 47.2,
    "Kansas": 44.3,
    "Baylor": 43.3,
    "Kentucky": 41.3,
    "Auburn": 47.9,
    "Tennessee": 39.2,
    "Houston": 29.8,
    "Texas Tech": 38.2,
    "UCLA": 31.4,
    "Villanova": 32.3,
    "Iowa": 31.4,
    "Duke": 35.5,
    "Purdue": 24.1,
    "LSU": 18.2,
    "Texas": 12.2,
    "Saint Mary's": 11.7,
    "Connecticut": 9.9,
    "Illinois": 10.8,
    "Arkansas": 8.5,
    "San Diego State": 10.1,
    "Loyola Chicago": 9.0,
    "San Francisco": 8.6,
    "Wisconsin": 13.1,
    "Virginia Tech": 7.6,
    "Alabama": 9.9,
    "Colorado State": 6.5,
    "Ohio State": 6.2,
    "Murray State": 5.7,
    "Boise State": 3.9,
    "Michigan": 6.2,
    "USC": 7.8,
    "North Carolina": 5.9,
    "Iowa State": 6.7,
    "Providence": 5.7,
    "Memphis": 3.3,
    "Davidson": 6.1,
    "TCU": 4.0,
    "Michigan State": 6.1,
    "Seton Hall": 3.9,
    "Creighton": 3.6,
    "Miami FL": 5.1,
    "UAB": 2.5,
    "Marquette": 3.6,
    "Vermont": 2.3,
    "Indiana": 3.4,
    "South Dakota State": 3.0,
    "Chattanooga": 1.7,
    "Richmond": 1.8,
    "New Mexico State": 1.2,
    "Rutgers/ND": 3.5,
    "Colgate": 0.9,
    "Jacksonville State": 0.4,
    "Montana State": 0.4,
    "Akron": 0.4,
    "Saint Peter's": 0.3,
    "Longwood": 0.3,
    "Delaware": 0.3,
    "Cal State Fullerton": 0.3,
    "Yale": 0.2,
    "Georgia State": 0.07,
    "Norfolk State": 0.1,
    "Texas Southern": 0.053,
    "Wright State": 0.04
    }
sweet_sixteen_odds_2022 = {
    "Gonzaga": 84.4,
    "Arizona": 76.3,
    "Kansas": 68.7,
    "Baylor": 71.9,
    "Kentucky": 64.9,
    "Auburn": 68.8,
    "Tennessee": 65.4,
    "Houston": 54.4,
    "Texas Tech": 63.7,
    "UCLA": 58.2,
    "Villanova": 58.8,
    "Iowa": 60.4,
    "Duke": 63.6,
    "Purdue": 50.5,
    "LSU": 40.2,
    "Texas": 27.9,
    "Saint Mary's": 27.5,
    "Connecticut": 39.1,
    "Illinois": 28.2,
    "Arkansas": 36.0,
    "San Diego State": 21.2,
    "Loyola Chicago": 22.2,
    "San Francisco": 19.1,
    "Wisconsin": 34.8,
    "Virginia Tech": 19.9,
    "Alabama": 23.1,
    "Colorado State": 16.7,
    "Ohio State": 16.9,
    "Murray State": 14.1,
    "Boise State": 8.1,
    "Michigan": 16.0,
    "USC": 16.8,
    "North Carolina": 16.1,
    "Iowa State": 19.8,
    "Providence": 18.9,
    "Memphis": 7.1,
    "Davidson": 17.1,
    "TCU": 11.7,
    "Michigan State": 17.2,
    "Seton Hall": 11.5,
    "Creighton": 9.7,
    "Miami FL": 12.3,
    "UAB": 9.7,
    "Marquette": 11.1,
    "Vermont": 14.9,
    "Indiana": 11.8,
    "South Dakota State": 12.3,
    "Chattanooga": 7.7,
    "Richmond": 8.4,
    "New Mexico State": 9.9,
    "Rutgers/ND": 10.8,
    "Colgate": 5.3,
    "Jacksonville State": 2.1,
    "Montana State": 2.4,
    "Akron": 2.5,
    "Saint Peter's": 1.9,
    "Longwood": 1.8,
    "Delaware": 2.1,
    "Cal State Fullerton": 2.2,
    "Yale": 1.7,
    "Georgia State": 0.4,
    "Norfolk State": 0.9,
    "Texas Southern": 0.47,
    "Wright State": 0.5
        }
round_32_odds_2022 = {
    "Gonzaga": 97.9,
    "Arizona": 97.1,
    "Kansas": 96.4,
    "Baylor": 94.5,
    "Kentucky": 91.1,
    "Auburn": 91.5,
    "Tennessee": 91.5,
    "Houston": 77.3,
    "Texas Tech": 89.7,
    "UCLA": 88.4,
    "Villanova": 89.4,
    "Iowa": 80.5,
    "Duke": 90.4,
    "Purdue": 89.0,
    "LSU": 62.4,
    "Texas": 55.5,
    "Saint Mary's": 63.0,
    "Connecticut": 70.6,
    "Illinois": 68.8,
    "Arkansas": 64.5,
    "San Diego State": 61.0,
    "Loyola Chicago": 54.3,
    "San Francisco": 54.8,
    "Wisconsin": 75.5,
    "Virginia Tech": 44.5,
    "Alabama": 62.3,
    "Colorado State": 50.4,
    "Ohio State": 45.7,
    "Murray State": 45.2,
    "Boise State": 50.6,
    "Michigan": 49.6,
    "USC": 54.5,
    "North Carolina": 55.3,
    "Iowa State": 37.6,
    "Providence": 55.9,
    "Memphis": 49.4,
    "Davidson": 49.8,
    "TCU": 49.9,
    "Michigan State": 50.2,
    "Seton Hall": 50.1,
    "Creighton": 39.0,
    "Miami FL": 45.5,
    "UAB": 22.7,
    "Marquette": 44.7,
    "Vermont": 35.5,
    "Indiana": 37.0,
    "South Dakota State": 44.1,
    "Chattanooga": 31.2,
    "Richmond": 19.5,
    "New Mexico State": 29.4,
    "Rutgers/ND": 37.7,
    "Colgate": 24.5,
    "Jacksonville State": 8.5,
    "Montana State": 10.3,
    "Akron": 11.6,
    "Saint Peter's": 8.9,
    "Longwood": 8.5,
    "Delaware": 10.6,
    "Cal State Fullerton": 9.6,
    "Yale": 11.0,
    "Georgia State": 2.1,
    "Norfolk State": 5.5,
    "Texas Southern": 3.6,
    "Wright State": 2.9
    }

champ_odds_2021 = {
    "Gonzaga": 34.4,
    "Illinois": 10.7,
    "Michigan": 10.4,
    "Baylor": 8.2,
    "Houston": 7.4,
    "Iowa": 6.4,
    "Ohio State": 3.7,
    "Alabama": 2.7,
    "Villanova": 1.2,
    "Loyola Chicago": 1.1,
    "Purdue": 1.0,
    "Florida State": 0.9,
    "Virginia": 0.9,
    "Arkansas": 0.9,
    "Tennessee": 0.8,
    "USC": 0.8,
    "Wisconsin": 0.7,
    "Colorado": 0.7,
    "San Diego State": 0.7,
    "Texas Tech": 0.6,
    "Connecticut": 0.6,
    "West Virginia": 0.6,
    "Kansas": 0.6,
    "BYU": 0.6,
    "Texas": 0.6,
    "Creighton": 0.5,
    "St. Bonaventure": 0.3,
    "Oklahoma State": 0.3,
    "North Carolina": 0.2,
    "Maryland": 0.2,
    "LSU": 0.2,
    "Rutgers": 0.2,
    "Florida": 0.2,
    "Georgia Tech": 0.1,
    "Oregon": 0.1,
    "Utah State": 0.1,
    "Clemson": 0.10,
    "Syracuse": 0.08,
    "Virginia Tech": 0.07,
    "Oklahoma": 0.06,
    "VCU": 0.05,
    "Michigan State/UCLA": 0.05,
    "Missouri": 0.03,
    "Georgetown": 0.03,
    "Wichita State/Drake": 0.023,
    "North Texas": 0.01,
    "UC Santa Barbara": 0.010,
    "Oregon State": 0.008,
    "Ohio": 0.005,
    "Abilene Christian": 0.004,
    "Colgate": 0.004,
    "Liberty": 0.004,
    "UNC Greensboro": 0.001,
    "Winthrop": 0.001,
    "Eastern Washington": 0.001,
    "Grand Canyon": 0.001,
    "Morehead State": 0.001,
    "Cleveland State": 0.001,
    "Oral Roberts": 0.001,
    "Drexel": 0.001,
    "Iona": 0.001,
    "Hartford": 0.001,
    "Mount St. Mary's/Texas Southern": 0.002,
    "Norfolk State/Appalachian State": 0.002
    }
second_place_odds_2021 = {
    "Gonzaga": 46.3,
    "Illinois": 22.2,
    "Michigan": 17.4,
    "Baylor": 18.0,
    "Houston": 16.8,
    "Iowa": 11.3,
    "Ohio State": 10.1,
    "Alabama": 5.8,
    "Villanova": 4.0,
    "Loyola Chicago": 3.3,
    "Purdue": 3.3,
    "Florida State": 2.3,
    "Virginia": 2.1,
    "Arkansas": 3.2,
    "Tennessee": 2.8,
    "USC": 1.9,
    "Wisconsin": 2.4,
    "Colorado": 1.8,
    "San Diego State": 2.4,
    "Texas Tech": 2.3,
    "Connecticut": 1.6,
    "West Virginia": 2.5,
    "Kansas": 1.6,
    "BYU": 1.6,
    "Texas": 1.6,
    "Creighton": 1.3,
    "St. Bonaventure": 0.9,
    "Oklahoma State": 1.4,
    "North Carolina": 1.0,
    "Maryland": 0.6,
    "LSU": 0.6,
    "Rutgers": 0.9,
    "Florida": 0.8,
    "Georgia Tech": 0.6,
    "Oregon": 0.4,
    "Utah State": 0.5,
    "Clemson": 0.5,
    "Syracuse": 0.5,
    "Virginia Tech": 0.4,
    "Oklahoma": 0.2,
    "VCU": 0.2,
    "Michigan State/UCLA": 0.26,
    "Missouri": 0.1,
    "Georgetown": 0.1,
    "Wichita State/Drake": 0.10,
    "North Texas": 0.10,
    "UC Santa Barbara": 0.05,
    "Oregon State": 0.06,
    "Ohio": 0.03,
    "Abilene Christian": 0.02,
    "Colgate": 0.04,
    "Liberty": 0.04,
    "UNC Greensboro": 0.010,
    "Winthrop": 0.02,
    "Eastern Washington": 0.004,
    "Grand Canyon": 0.005,
    "Morehead State": 0.005,
    "Cleveland State": 0.001,
    "Oral Roberts": 0.001,
    "Drexel": 0.001,
    "Iona": 0.001,
    "Hartford": 0.001,
    "Mount St. Mary's/Texas Southern": 0.002,
    "Norfolk State/Appalachian State": 0.002
    }
final_four_odds_2021 = {
    "Gonzaga": 60.5,
    "Illinois": 34.5,
    "Michigan": 37.6,
    "Baylor": 31.5,
    "Houston": 28.2,
    "Iowa": 19.3,
    "Ohio State": 21.0,
    "Alabama": 17.8,
    "Villanova": 9.5,
    "Loyola Chicago": 6.9,
    "Purdue": 8.0,
    "Florida State": 8.4,
    "Virginia": 4.7,
    "Arkansas": 8.5,
    "Tennessee": 6.7,
    "USC": 4.5,
    "Wisconsin": 5.6,
    "Colorado": 6.6,
    "San Diego State": 5.8,
    "Texas Tech": 6.2,
    "Connecticut": 5.8,
    "West Virginia": 6.3,
    "Kansas": 4.1,
    "BYU": 6.1,
    "Texas": 6.5,
    "Creighton": 3.1,
    "St. Bonaventure": 3.7,
    "Oklahoma State": 4.0,
    "North Carolina": 2.7,
    "Maryland": 2.6,
    "LSU": 2.5,
    "Rutgers": 2.5,
    "Florida": 2.8,
    "Georgia Tech": 1.8,
    "Oregon": 1.3,
    "Utah State": 1.9,
    "Clemson": 1.5,
    "Syracuse": 1.5,
    "Virginia Tech": 1.5,
    "Oklahoma": 0.7,
    "VCU": 0.7,
    "Michigan State/UCLA": 1.3,
    "Missouri": 0.4,
    "Georgetown": 0.7,
    "Wichita State/Drake": 0.38,
    "North Texas": 0.5,
    "UC Santa Barbara": 0.2,
    "Oregon State": 0.3,
    "Ohio": 0.1,
    "Abilene Christian": 0.2,
    "Colgate": 0.3,
    "Liberty": 0.2,
    "UNC Greensboro": 0.1,
    "Winthrop": 0.1,
    "Eastern Washington": 0.03,
    "Grand Canyon": 0.04,
    "Morehead State": 0.04,
    "Cleveland State": 0.01,
    "Oral Roberts": 0.009,
    "Drexel": 0.009,
    "Iona": 0.003,
    "Hartford": 0.001,
    "Mount St. Mary's/Texas Southern": 0.002,
    "Norfolk State/Appalachian State": 0.002
    }
elite_eight_odds_2021 = {
    "Gonzaga": 77.3,
    "Illinois": 52.7,
    "Michigan": 53.3,
    "Baylor": 46.6,
    "Houston": 49.9,
    "Iowa": 49.7,
    "Ohio State": 41.9,
    "Alabama": 37.9,
    "Villanova": 18.4,
    "Loyola Chicago": 13.9,
    "Purdue": 15.7,
    "Florida State": 16.8,
    "Virginia": 10.3,
    "Arkansas": 21.0,
    "Tennessee": 15.4,
    "USC": 17.5,
    "Wisconsin": 10.8,
    "Colorado": 13.4,
    "San Diego State": 14.7,
    "Texas Tech": 15.4,
    "Connecticut": 14.3,
    "West Virginia": 17.0,
    "Kansas": 17.5,
    "BYU": 16.2,
    "Texas": 17.5,
    "Creighton": 7.3,
    "St. Bonaventure": 7.8,
    "Oklahoma State": 10.6,
    "North Carolina": 6.0,
    "Maryland": 7.7,
    "LSU": 5.7,
    "Rutgers": 7.6,
    "Florida": 8.6,
    "Georgia Tech": 4.8,
    "Oregon": 6.9,
    "Utah State": 6.2,
    "Clemson": 5.2,
    "Syracuse": 5.2,
    "Virginia Tech": 5.3,
    "Oklahoma": 2.2,
    "VCU": 4.5,
    "Michigan State/UCLA": 4.8,
    "Missouri": 1.4,
    "Georgetown": 2.4,
    "Wichita State/Drake": 2.9,
    "North Texas": 1.8,
    "UC Santa Barbara": 0.9,
    "Oregon State": 1.4,
    "Ohio": 0.6,
    "Abilene Christian": 1.5,
    "Colgate": 1.4,
    "Liberty": 1.0,
    "UNC Greensboro": 0.6,
    "Winthrop": 0.6,
    "Eastern Washington": 0.5,
    "Grand Canyon": 0.6,
    "Morehead State": 0.4,
    "Cleveland State": 0.1,
    "Oral Roberts": 0.1,
    "Drexel": 0.09,
    "Iona": 0.05,
    "Hartford": 0.02,
    "Mount St. Mary's/Texas Southern": 0.008,
    "Norfolk State/Appalachian State": 0.003
    }
sweet_sixteen_odds_2021 = {
   "Gonzaga": 91.2,
   "Illinois": 67.8,
   "Michigan": 72.7,
   "Baylor": 67.2,
   "Houston": 70.6,
   "Iowa": 70.6,
   "Ohio State": 66.2,
   "Alabama": 58.6,
   "Villanova": 45.8,
   "Loyola Chicago": 22.3,
   "Purdue": 40.1,
   "Florida State": 46.9,
   "Virginia": 43.3,
   "Arkansas": 43.8,
   "Tennessee": 45.3,
   "USC": 41.0,
   "Wisconsin": 20.1,
   "Colorado": 37.2,
   "San Diego State": 35.7,
   "Texas Tech": 32.8,
   "Connecticut": 25.3,
   "West Virginia": 44.1,
   "Kansas": 43.9,
   "BYU": 36.5,
   "Texas": 40.5,
   "Creighton": 38.3,
   "St. Bonaventure": 15.4,
   "Oklahoma State": 37.6,
   "North Carolina": 12.5,
   "Maryland": 15.6,
   "LSU": 11.8,
   "Rutgers": 16.2,
   "Florida": 19.3,
   "Georgia Tech": 9.4,
   "Oregon": 15.6,
   "Utah State": 17.1,
   "Clemson": 12.2,
   "Syracuse": 17.2,
   "Virginia Tech": 13.5,
   "Oklahoma": 5.1,
   "VCU": 11.3,
   "Michigan State/UCLA": 15.6,
   "Missouri": 3.6,
   "Georgetown": 11.7,
   "Wichita State/Drake": 11.4,
   "North Texas": 9.0,
   "UC Santa Barbara": 10.2,
   "Oregon State": 9.4,
   "Ohio": 8.2,
   "Abilene Christian": 7.4,
   "Colgate": 6.3,
   "Liberty": 7.7,
   "UNC Greensboro": 4.7,
   "Winthrop": 5.0,
   "Eastern Washington": 3.7,
   "Grand Canyon": 2.5,
   "Morehead State": 2.9,
   "Cleveland State": 1.0,
   "Oral Roberts": 1.0,
   "Drexel": 0.5,
   "Iona": 0.4,
   "Hartford": 0.2,
   "Mount St. Mary's/Texas Southern": 0.11,
   "Norfolk State/Appalachian State": 0.04
    }
round_32_odds_2021 = {
   "Gonzaga": 99.6,
   "Illinois": 96.1,
   "Michigan": 98.4,
   "Baylor": 97.5,
   "Houston": 94.4,
   "Iowa": 91.0,
   "Ohio State": 93.8,
   "Alabama": 95.7,
   "Villanova": 80.7,
   "Loyola Chicago": 61.9,
   "Purdue": 72.6,
   "Florida State": 81.2,
   "Virginia": 74.3,
   "Arkansas": 78.1,
   "Tennessee": 73.0,
   "USC": 70.3,
   "Wisconsin": 56.4,
   "Colorado": 68.0,
   "San Diego State": 62.2,
   "Texas Tech": 60.5,
   "Connecticut": 57.4,
   "West Virginia": 84.1,
   "Kansas": 82.4,
   "BYU": 63.9,
   "Texas": 74.8,
   "Creighton": 70.9,
   "St. Bonaventure": 53.1,
   "Oklahoma State": 73.6,
   "North Carolina": 43.6,
   "Maryland": 42.6,
   "LSU": 46.9,
   "Rutgers": 54.6,
   "Florida": 55.6,
   "Georgia Tech": 38.1,
   "Oregon": 54.4,
   "Utah State": 39.5,
   "Clemson": 45.4,
   "Syracuse": 37.8,
   "Virginia Tech": 44.4,
   "Oklahoma": 53.6,
   "VCU": 45.6,
   "Michigan State/UCLA": 36.1,
   "Missouri": 46.4,
   "Georgetown": 32.0,
   "Wichita State/Drake": 29.6,
   "North Texas": 27.4,
   "UC Santa Barbara": 29.1,
   "Oregon State": 26.1,
   "Ohio": 25.7,
   "Abilene Christian": 25.2,
   "Colgate": 21.9,
   "Liberty": 26.4,
   "UNC Greensboro": 18.8,
   "Winthrop": 19.3,
   "Eastern Washington": 17.6,
   "Grand Canyon": 9.0,
   "Morehead State": 15.9,
   "Cleveland State": 5.6,
   "Oral Roberts": 6.2,
   "Drexel": 3.9,
   "Iona": 4.3,
   "Hartford": 2.5,
   "Mount St. Mary's/Texas Southern": 1.7,
   "Norfolk State/Appalachian State": 0.4
    }



## PAST AUCTION RESULTS
auction_results_2025 = {}
auction_results_2024 = {
    "Florida Atlantic": 975.00,
    "South Dakota State": 300.00,
    "Grand Canyon": 800.00,
    "Nevada": 1075.00,
    "Oakland": 400.00,
    "Boise State/Colorado": 1325.00,
    "Arizona": 7200.00,
    "Drake": 1025.00,
    "James Madison": 1050.00,
    "Long Beach State": 400.00,
    "Nebraska": 1100.00,
    "Dayton": 1125.00,
    "College of Charleston": 775.00,
    "Purdue": 9050.00,
    "Tennessee": 8050.00,
    "Stetson": 325.00,
    "Saint Mary's": 3350.00,
    "San Diego State": 2450.00,
    "Longwood": 450.00,
    "Mississippi State": 1325.00,
    "McNeese State": 1375.00,
    "Gonzaga": 3700.00,
    "Clemson": 1775.00,
    "Creighton": 5400.00,
    "Western Kentucky": 500.00,
    "Utah State": 1200.00,
    "NC State": 1200.00,
    "UNC": 8850.00,
    "Kentucky": 5475.00,
    "Texas": 1975.00,
    "Florida": 1875.00,
    "Akron": 700.00,
    "Auburn": 6350.00,
    "Iowa State": 7050.00,
    "Baylor": 5050.00,
    "Oregon": 1425.00,
    "Morehead State": 875.00,
    "Howard/Wagner": 400.00,
    "Washington State": 1700.00,
    "Connecticut": 12300.00,
    "Samford": 1025.00,
    "South Carolina": 1925.00,
    "Kansas": 2825.00,
    "TCU": 1700.00,
    "Virginia/Colorado State": 1500.00,
    "Texas A&M": 1750.00,
    "Wisconsin": 2550.00,
    "Yale": 700.00,
    "Duke": 5150.00,
    "Northwestern": 1275.00,
    "Michigan State": 2050.00,
    "New Mexico": 2125.00,
    "Houston": 11500.00,
    "Colgate": 575.00,
    "Montana State/Grambling": 500.00,
    "Vermont": 825.00,
    "BYU": 3625.00,
    "Duquesne": 650.00,
    "Illinois": 5200.00,
    "Saint Peter's": 525.00,
    "Alabama": 5275.00,
    "Texas Tech": 3350.00,
    "Marquette": 6150.00,
    "UAB": 1050.00
    }
auction_results_2023 = {
    "Louisiana": 575.00,
    "Howard": 225.00,
    "Michigan State": 1425.00,
    "Creighton": 2600.00,
    "Grand Canyon": 425.00,
    "USC": 975.00,
    "Connecticut": 3250.00,
    "Maryland": 950.00,
    "Saint Mary's": 925.00,
    "Duke": 3050.00,
    "Memphis": 1450.00,
    "Tennessee": 3450.00,
    "Oral Roberts": 775.00,
    "Marquette": 3075.00,
    "Providence": 975.00,
    "Montana State": 600.00,
    "Boise State": 1050.00,
    "Kansas State": 2550.00,
    "Kentucky": 1925.00,
    "Charleston": 975.00,
    "UCLA": 3025.00,
    "Vermont": 475.00,
    "Alabama": 6600.00,
    "Florida Atlantic": 1075.00,
    "Arkansas": 1325.00,
    "Virginia": 1975.00,
    "Missouri": 600.00,
    "Colgate": 550.00,
    "Drake": 600.00,
    "Gonzaga": 4025.00,
    "VCU": 1050.00,
    "Iona": 375.00,
    "Xavier": 2800.00,
    "Furman": 625.00,
    "Northwestern": 900.00,
    "Purdue": 4375.00,
    "Miami FL": 1550.00,
    "Texas A&M Corpus Chris": 275.00,
    "FDU/Texas Southern": 225.00,
    "Texas A&M": 1375.00,
    "West Virginia": 1000.00,
    "Nevada/Arizona State": 750.00,
    "Princeton": 525.00,
    "NC State": 825.00,
    "Houston": 5275.00,
    "Northern Kentucky": 425.00,
    "TCU": 1275.00,
    "Texas": 4950.00,
    "Auburn": 1150.00,
    "Arizona": 4250.00,
    "Kennesaw State": 450.00,
    "UNC Asheville": 475.00,
    "Iowa State": 1675.00,
    "Baylor": 3375.00,
    "Penn State": 900.00,
    "San Diego State": 2150.00,
    "Iowa": 975.00,
    "Pittsburgh": 825.00,
    "Indiana": 2175.00,
    "Kansas": 5775.00,
    "Kent State": 825.00,
    "Utah State": 1100.00,
    "UC Santa Barbara": 525.00,
    "Illinois": 925.00
    }
auction_results_2022 = {
    "Iowa State": 632.00,
    "Georgia State": 168.00,
    "South Dakota State": 601.00,
    "Rutgers/ND": 450.00,
    "Akron": 275.00,
    "Arkansas": 1475.00,
    "Vermont": 625.00,
    "Tennessee": 3900.00,
    "Murray State": 825.00,
    "New Mexico State": 600.00,
    "Cal State Fullerton": 300.00,
    "Houston": 3200.00,
    "Connecticut": 1925.00,
    "Illinois": 2250.00,
    "TCU": 750.00,
    "USC": 1000.00,
    "Kansas": 6100.00,
    "Indiana": 900.00,
    "Providence": 1325.00,
    "Marquette": 800.00,
    "San Francisco": 1075.00,
    "Wisconsin": 2375.00,
    "Richmond": 375.00,
    "LSU": 2025.00,
    "Ohio State": 1100.00,
    "Miami FL": 925.00,
    "Wright State": 250.00,
    "North Carolina": 1175.00,
    "Boise State": 700.00,
    "Seton Hall": 750.00,
    "Colorado State": 925.00,
    "Duke": 4025.00,
    "Virginia Tech": 1050.00,
    "UAB": 450.00,
    "Texas Southern": 250.00,
    "Saint Mary's": 1550.00,
    "Yale": 300.00,
    "Texas": 1350.00,
    "Memphis": 900.00,
    "Creighton": 725.00,
    "Gonzaga": 11725.00,
    "Davidson": 925.00,
    "Auburn": 5550.00,
    "Delaware": 275.00,
    "Jacksonville State": 325.00,
    "Norfolk State": 250.00,
    "UCLA": 4025.00,
    "Michigan State": 1025.00,
    "Arizona": 8000.00,
    "San Diego State": 950.00,
    "Michigan": 1500.00,
    "Colgate": 675.00,
    "Purdue": 3875.00,
    "Kentucky": 6050.00,
    "Longwood": 300.00,
    "Loyola Chicago": 1250.00,
    "Baylor": 5350.00,
    "Villanova": 5050.00,
    "Montana State": 350.00,
    "Alabama": 1375.00,
    "Saint Peter's": 325.00,
    "Chattanooga": 550.00,
    "Iowa": 4100.00,
    "Texas Tech": 4200.00
    }
auction_results_2021 = {
    "Loyola Chicago": 700,
    "Wichita State/Drake": 380,
    "Colorado": 1400,
    "Florida": 677,
    "Winthrop": 453,
    "Oral Roberts": 157,
    "Villanova": 1150,
    "Maryland": 750,
    "Purdue": 1900,
    "Oregon": 900,
    "Eastern Washington": 303,
    "Hartford": 179,
    "Texas Tech": 1650,
    "Houston": 4002,
    "USC": 1403,
    "Morehead State": 389,
    "Michigan State/UCLA": 955,
    "Syracuse": 655,
    "Utah State": 700,
    "Iowa": 4000,
    "VCU": 608,
    "Creighton": 1632,
    "Georgetown": 600,
    "Missouri": 525,
    "Rutgers": 1025,
    "Tennessee": 1601,
    "Oklahoma State": 1865,
    "Texas": 2565,
    "San Diego State": 1650,
    "Wisconsin": 1199,
    "Baylor": 6902,
    "Arkansas": 1956,
    "Drexel": 195,
    "BYU": 1250,
    "LSU": 1350,
    "Ohio": 675,
    "Virginia": 2078,
    "UC Santa Barbara": 675,
    "Kansas": 2450,
    "Michigan": 5600,
    "Colgate": 550,
    "St. Bonaventure": 950,
    "Alabama": 3729,
    "Mount St. Mary's/Texas Southern": 156,
    "Norfolk State/Appalachian State": 199,
    "Iona": 221,
    "Clemson": 850,
    "Abilene Christian": 387,
    "Cleveland State": 260,
    "Florida State": 2901,
    "Virginia Tech": 852,
    "Connecticut": 1700,
    "Gonzaga": 12200,
    "Oklahoma": 900,
    "North Texas": 645,
    "Illinois": 7755,
    "Ohio State": 4252,
    "Georgia Tech": 778,
    "West Virginia": 2608,
    "Oregon State": 628,
    "UNC Greensboro": 500,
    "Grand Canyon": 400,
    "Liberty": 707,
    "North Carolina": 1031
    }


auction_total_2024 = sum(auction_results_2024.values())
auction_total_2023 = sum(auction_results_2023.values())
auction_total_2022 = sum(auction_results_2022.values())
auction_total_2021 = sum(auction_results_2021.values())

past_pots = {
    2021: auction_total_2021,
    2022: auction_total_2022, 
    2023: auction_total_2023, 
    2024: auction_total_2024}
team_seeds_data = {
    2021: team_seeds_2021,
    2022: team_seeds_2022,
    2023: team_seeds_2023,
    2024: team_seeds_2024,
    2025: team_seeds_2025}
log_data = []
auction_relative = {}
auction_2025 = CalcuttaAuction(
    champ_odds_2025_538, second_place_odds_2025_538, final_four_odds_2025_538, elite_eight_odds_2025_538, sweet_sixteen_odds_2025_538, round_32_odds_2025_538, 
    fanduel_champ_odds_2025, fanduel_second_place_odds_2025, fanduel_final_four_odds_2025, fanduel_elite_eight_odds_2025, fanduel_sweet_sixteen_odds_2025, fanduel_round_32_odds_2025,
    KenPom_champ_odds_2025, KenPom_second_place_odds_2025, KenPom_final_four_odds_2025, KenPom_elite_eight_odds_2025, KenPom_sweet_sixteen_odds_2025, KenPom_round_32_odds_2025,
    round_32_vig, team_seeds_2025, auction_results_2025, auction_relative)
fair_shares_2025 = auction_2025.calculate_fair_value()[1]
auction = auction_2025


initial_fair_values, initial_fair_shares = auction.calculate_fair_value()
auction.print_results_table(initial_fair_values, initial_fair_shares)
auction.run_live_update()  








# auction_2021 = CalcuttaAuction(
#     champ_odds_2021, second_place_odds_2021, final_four_odds_2021, elite_eight_odds_2021, sweet_sixteen_odds_2021, round_32_odds_2021, 
#     fanduel_champ_odds_2025, fanduel_second_place_odds_2025, fanduel_final_four_odds_2025, fanduel_elite_eight_odds_2025, fanduel_sweet_sixteen_odds_2025, fanduel_round_32_odds_2025, 
#     round_32_vig, team_seeds_2021, auction_results_2025, auction_relative)
# auction_2022 = CalcuttaAuction(
#     champ_odds_2022, second_place_odds_2022, final_four_odds_2022, elite_eight_odds_2022, sweet_sixteen_odds_2022, round_32_odds_2022, 
#     fanduel_champ_odds_2025, fanduel_second_place_odds_2025, fanduel_final_four_odds_2025, fanduel_elite_eight_odds_2025, fanduel_sweet_sixteen_odds_2025, fanduel_round_32_odds_2025, 
#     round_32_vig, team_seeds_2022, auction_results_2025, auction_relative)
# auction_2023 = CalcuttaAuction(
#     champ_odds_2023, second_place_odds_2023, final_four_odds_2023, elite_eight_odds_2023, sweet_sixteen_odds_2023, round_32_odds_2023, 
#     fanduel_champ_odds_2025, fanduel_second_place_odds_2025, fanduel_final_four_odds_2025, fanduel_elite_eight_odds_2025, fanduel_sweet_sixteen_odds_2025, fanduel_round_32_odds_2025, 
#     round_32_vig, team_seeds_2023, auction_results_2025, auction_relative)
# auction_2024 = CalcuttaAuction(
#     champ_odds_2024, second_place_odds_2024, final_four_odds_2024, elite_eight_odds_2024, sweet_sixteen_odds_2024, round_32_odds_2024, 
#     fanduel_champ_odds_2025, fanduel_second_place_odds_2025, fanduel_final_four_odds_2025, fanduel_elite_eight_odds_2025, fanduel_sweet_sixteen_odds_2025, fanduel_round_32_odds_2025, 
#     round_32_vig, team_seeds_2024, auction_results_2025, auction_relative)


# fair_shares_2021 = auction_2021.calculate_fair_value()[1]
# fair_shares_2022 = auction_2022.calculate_fair_value()[1]
# fair_shares_2023 = auction_2023.calculate_fair_value()[1]
# fair_shares_2024 = auction_2024.calculate_fair_value()[1]





# fair_share_data = {
#     2021: fair_shares_2021,
#     2022: fair_shares_2022,
#     2023: fair_shares_2023,
#     2024: fair_shares_2024}
# auction_results_data = {
#     2021: auction_results_2021,
#     2022: auction_results_2022,
#     2023: auction_results_2023,
#     2024: auction_results_2024}

# optimal_params_by_year = { 
#     '2021': (0.0886, 4.22) 
# }
    

## CODE BELOW RUNS THE PROGRAM



#auction.cross_validation(auction_results_data, fair_share_data)

# for year in [2021, 2022, 2023, 2024]:
#     auction_results = auction_results_data[year]  
#     fair_shares= fair_share_data[year]
#     a = 0.0886
#     b = 4.22
#     df = auction.generate_auction_df_for_year_and_params(auction_results, fair_shares, (a, b), year)
#     print(f"Generated DataFrame for {year} with parameters a={a}, b={b})")


#auction.generate_team_odds(Fanduel = True)










# for team in auction.fanduel_champ_odds:
#     odds_list = [fanduel_round_32_odds_2025[team], fanduel_sweet_sixteen_odds_2025[team], fanduel_elite_eight_odds_2025[team], fanduel_final_four_odds_2025[team], fanduel_second_place_odds_2025[team], fanduel_champ_odds_2025[team]]

#     KenPom_champ_odds, devig_fanduel_champ_odds = round(auction.champ_odds[team]*100,2), round(auction.fanduel_champ_odds[team]*100,2)
#     KenPom_second_place_odds, devig_fanduel_second_place_odds = round(auction.second_place_odds[team]*100,2), round(auction.fanduel_second_place_odds[team]*100,2)
#     KenPom_final_four_odds, devig_fanduel_final_four_odds = round(auction.final_four_odds[team]*100.2), round(auction.fanduel_final_four_odds[team]*100,2)
#     KenPom_elite_eight_odds, devig_fanduel_elite_eight_odds = round(auction.elite_eight_odds[team]*100,2), round(auction.fanduel_elite_eight_odds[team]*100,2)
#     KenPom_sweet_sixteen_odds, devig_fanduel_sweet_sixteen_odds = round(auction.sweet_sixteen_odds[team]*100,2), round(auction.fanduel_sweet_sixteen_odds[team]*100,2)
#     KenPom_round_32_odds, devig_fanduel_round_32_odds = round(auction.round_32_odds[team]*100,2), round(auction.fanduel_round_32_odds[team]*100,2)
        
#     KenPom_list = [KenPom_round_32_odds, KenPom_sweet_sixteen_odds, KenPom_elite_eight_odds, KenPom_final_four_odds, KenPom_second_place_odds, KenPom_champ_odds]
#     devig_odds_list = [devig_fanduel_round_32_odds, devig_fanduel_sweet_sixteen_odds, devig_fanduel_elite_eight_odds, devig_fanduel_final_four_odds, devig_fanduel_second_place_odds, devig_fanduel_champ_odds]
#     # combined_odds_list = 
    
#     print("FD Raw", team, odds_list)
#     print("538", team, KenPom_list)
#     print("Fanduel", team, devig_odds_list)
#     print("")


# auction.generate_devigged_fd_odds_csv()
# print("538", auction.devig_odds(champ_odds_2025_538, expected_total=1, odds_type="Percentage"))
# print("Fanduel", auction.devig_odds(fanduel_champ_odds_2025, expected_total=1, odds_type="American"))

#print(auction.past_auction_study(auction_results_2022, 2022))



