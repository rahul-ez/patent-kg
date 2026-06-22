import torch
import logging
from gnn.model import PatentGraphSAGE
from config.paths import VECTOR_STORE

logger = logging.getLogger(__name__)

_GNN_MODEL = None

def get_model():
    """
    Retrieve or initialize the globally cached instance of the PatentGraphSAGE model.
    Loads model parameters from the trained model checkpoint once.
    """
    global _GNN_MODEL
    if _GNN_MODEL is None:
        model_path = VECTOR_STORE / "gnn_model.pt"
        if not model_path.exists():
            # Support alternative model name
            model_path = VECTOR_STORE / "patent_gnn.pt"
        if not model_path.exists():
            raise FileNotFoundError(f"Trained GNN model checkpoint not found at {VECTOR_STORE}")
            
        logger.info("Loading trained GraphSAGE model from %s ...", model_path)
        model = PatentGraphSAGE()
        checkpoint = torch.load(model_path, map_location="cpu")
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _GNN_MODEL = model
        logger.info("GraphSAGE model loaded successfully and cached.")
        
    return _GNN_MODEL

def run_gnn_inference(data):
    """
    Run GraphSAGE live forward pass on the constructed PyTorch Geometric Data object.
    Uses GPU/CUDA acceleration if available, otherwise falls back to CPU.
    
    Returns:
        (np.ndarray, np.ndarray):
            - 64-dimensional GraphSAGE node embeddings (shape: [N, 64])
            - Predicted raw novelty scores from the output head (shape: [N, 1])
    """
    model = get_model()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = model.to(device)
    x = data.x.to(device)
    edge_index = data.edge_index.to(device)
    
    with torch.no_grad():
        # Retrieve the 64-dimensional latent embeddings (forward pass)
        embeddings = model(x, edge_index)
        # Retrieve the head novelty predictions
        preds = model.predict_novelty(x, edge_index)
        
    return embeddings.cpu().numpy(), preds.cpu().numpy()
