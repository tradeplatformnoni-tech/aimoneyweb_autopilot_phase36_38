import random,torch,os
MODEL="models/deep_rl_model.pt"
def mutate_weights(path=MODEL,scale=0.05):
    if not os.path.exists(path): return False
    w=torch.load(path,map_location="cpu")
    for k in w: w[k]+=torch.randn_like(w[k])*scale
    new_path=path.replace(".pt","_mut.pt"); torch.save(w,new_path)
    return new_path
