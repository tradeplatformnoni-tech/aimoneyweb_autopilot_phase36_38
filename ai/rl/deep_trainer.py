import torch,random,os,time,joblib
import numpy as np
from torch import nn,optim

MODEL_PATH="models/deep_rl_model.pt"
device="cpu"

class PolicyNet(nn.Module):
    def __init__(self): super().__init__(); self.net=nn.Sequential(
        nn.Linear(4,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU(),nn.Linear(32,1))
    def forward(self,x): return torch.tanh(self.net(x))

def train_rl(data=None,epochs=10):
    net=PolicyNet().to(device)
    opt=optim.Adam(net.parameters(),lr=0.001)
    for _ in range(epochs):
        x=torch.randn(32,4); y=torch.randn(32,1)
        pred=net(x); loss=((pred-y)**2).mean()
        opt.zero_grad(); loss.backward(); opt.step()
    torch.save(net.state_dict(),MODEL_PATH)
    return {"trained":True,"path":MODEL_PATH}

def load_signal(pnl,dd,risk,sent):
    if not os.path.exists(MODEL_PATH): return 0
    net=PolicyNet(); net.load_state_dict(torch.load(MODEL_PATH,map_location=device))
    with torch.no_grad():
        x=torch.tensor([[pnl,dd,risk,sent]],dtype=torch.float32)
        return float(net(x).item())
