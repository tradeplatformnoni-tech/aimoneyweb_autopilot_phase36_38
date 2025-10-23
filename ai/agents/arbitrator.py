def arbitrate(votes, fallback=0):
    if sum(votes)>1: return 1
    elif sum(votes)<-1: return -1
    else: return fallback
