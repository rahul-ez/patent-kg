import torch
import torch.nn as nn
from torch_geometric.nn import SAGEConv

class PatentGraphSAGE(nn.Module):
    """
    3-layer GraphSAGE architecture with a residual projection connection and 
    a multi-layer perceptron (MLP) head to predict composite novelty scores.
    """
    def __init__(self, in_dim=780, proj_dim=256, sage1_dim=128, sage2_dim=64, sage3_dim=32):
        super().__init__()
        
        # 1. Feature projection layer
        self.input_proj = nn.Sequential(
            nn.Linear(in_dim, proj_dim),
            nn.LayerNorm(proj_dim)
        )
        
        # 2. GraphSAGE Layers
        self.conv1 = SAGEConv(proj_dim, sage1_dim)
        self.bn1 = nn.BatchNorm1d(sage1_dim)
        
        self.conv2 = SAGEConv(sage1_dim, sage2_dim)
        self.bn2 = nn.BatchNorm1d(sage2_dim)
        
        # Residual projection link to match dimensions (256 -> 64)
        self.res_proj = nn.Linear(proj_dim, sage2_dim, bias=False)
        
        self.conv3 = SAGEConv(sage2_dim, sage3_dim)
        self.bn3 = nn.BatchNorm1d(sage3_dim)
        
        # 3. Output prediction head (predicts novelty [0-1] range)
        self.head = nn.Sequential(
            nn.Linear(sage3_dim, 16),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(16, 1)
        )

    def forward(self, x, edge_index):
        """
        Runs the forward pass up to the 64-dimensional embedding layer (Conv 2 + residual),
        incorporating semantic meaning and local graph neighborhood structure.
        """
        # Feature projection
        x_proj = self.input_proj(x)
        x_proj_act = torch.relu(x_proj)
        
        # Conv Layer 1
        h1 = self.conv1(x_proj_act, edge_index)
        h1 = self.bn1(h1)
        h1 = torch.relu(h1)
        
        # Conv Layer 2
        h2 = self.conv2(h1, edge_index)
        h2 = self.bn2(h2)
        
        # Add residual connection from projected inputs
        res = self.res_proj(x_proj_act)
        h2 = h2 + res
        h2 = torch.relu(h2)
        
        return h2

    def predict_novelty(self, x, edge_index):
        """
        Runs the full forward pass to yield predicted patent novelty scores.
        """
        # 64-dimensional representation
        h2 = self.forward(x, edge_index)
        
        # Conv Layer 3
        h3 = self.conv3(h2, edge_index)
        h3 = self.bn3(h3)
        h3 = torch.relu(h3)
        
        # Output prediction score
        return self.head(h3)
