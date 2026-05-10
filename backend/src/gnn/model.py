import torch
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv # This is the GraphSAGE layer

class PatentGNN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(PatentGNN, self).__init__()
        # Layer 1: Look at immediate neighbors
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        # Layer 2: Look at neighbors of neighbors
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        # 1. First hop of information
        x = self.conv1(x, edge_index)
        x = F.relu(x) # Activate neurons
        x = F.dropout(x, p=0.2, training=self.training) # Prevent "over-memorizing"
        
        # 2. Second hop of information
        x = self.conv2(x, edge_index)
        return x # This is your "Graph-Aware" Embedding