import random, numpy as np
def agent_votes(pnl,dd,var,sentiment):
    strat_vote = np.sign(pnl - dd)
    risk_vote  = -1 if var>0.02 else 1
    sent_vote  = 1 if sentiment>0 else -1
    votes = [strat_vote, risk_vote, sent_vote]
    decision = np.sign(sum(votes))
    return float(decision), votes
