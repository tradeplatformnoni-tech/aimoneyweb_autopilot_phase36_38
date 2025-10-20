import random
class BayesOptimizer:
    def __init__(self):
        self.best_score=-1e9
        self.best_params={"alpha":0.5,"beta":0.5}
    def suggest(self):
        # explore around current best
        a=max(0.0,min(1.0,self.best_params["alpha"]+random.uniform(-0.1,0.1)))
        b=max(0.0,min(1.0,self.best_params["beta"]+random.uniform(-0.1,0.1)))
        return {"alpha":a,"beta":b}
    def observe(self,params,score):
        if score>self.best_score:
            self.best_score=score
            self.best_params=params
    def status(self):
        return {"best_score":self.best_score,"best_params":self.best_params}
