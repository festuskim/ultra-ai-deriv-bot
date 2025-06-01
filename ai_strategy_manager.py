class AdvancedStrategyManager:
    def adapt_stake(self, profit, current_stake):
        if profit > 0:
            return current_stake + profit * 0.2
        return max(1.0, current_stake * 0.8)