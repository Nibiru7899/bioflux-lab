"""A small bipartite stoichiometric message-passing network and MLP."""
import time

import numpy as np
import torch
from safetensors.torch import save_file
from torch import nn

from bioflux.storage import write_json


def seed_all(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True, warn_only=True)


class MLP(nn.Module):
    def __init__(self, features, hidden=64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(features, hidden), nn.SiLU(),
                                 nn.Linear(hidden, hidden), nn.SiLU(), nn.Linear(hidden, 4))

    def forward(self, x, masks):
        return self.net(x)


class BipartiteMPNN(nn.Module):
    def __init__(self, stoich, hidden=32):
        super().__init__()
        matrix = torch.as_tensor(np.array(stoich, copy=True), dtype=torch.float32)
        # Separate substrate/product channels retain direction and coefficient magnitude.
        for name, adjacency in [('positive', matrix.clamp(min=0)), ('negative', (-matrix).clamp(min=0))]:
            self.register_buffer(name, adjacency / adjacency.sum(1, keepdim=True).clamp(min=1))
            transpose = adjacency.T.contiguous()
            self.register_buffer(name + '_t', transpose / transpose.sum(1, keepdim=True).clamp(min=1))
        self.large_graph = matrix.shape[1] > 500
        if self.large_graph:
            for name in ['positive', 'negative', 'positive_t', 'negative_t']:
                self.register_buffer('sparse_' + name, getattr(self, name).to_sparse_coo(), persistent=False)
        self.metabolites = nn.Parameter(torch.randn(matrix.shape[0], hidden) * 0.05)
        self.reactions = nn.Parameter(torch.randn(matrix.shape[1], hidden) * 0.05)
        self.reaction_input = nn.Linear(3, hidden)
        self.environment_input = nn.Linear(2, hidden)
        self.to_metabolite = nn.ModuleList([nn.Linear(3 * hidden, hidden) for _ in range(2)])
        self.to_reaction = nn.ModuleList([nn.Linear(3 * hidden, hidden) for _ in range(2)])
        self.head = nn.Sequential(nn.Linear(4 * hidden + 2, hidden), nn.SiLU(), nn.Linear(hidden, 4))

    def forward(self, x, masks):
        environment = x[:, :2]
        active = 1 - masks
        reaction_input = torch.cat([masks.unsqueeze(-1),
                                    environment[:, None, :].expand(-1, masks.shape[1], -1)], dim=-1)
        r = self.reactions[None] + self.reaction_input(reaction_input)
        m = self.metabolites[None] + self.environment_input(environment)[:, None]
        for to_m, to_r in zip(self.to_metabolite, self.to_reaction):
            messages = r * active.unsqueeze(-1)
            m = torch.nn.functional.silu(to_m(torch.cat([
                m, self.propagate('positive', messages), self.propagate('negative', messages)], dim=-1)))
            r = torch.nn.functional.silu(to_r(torch.cat([
                r, self.propagate('positive_t', m), self.propagate('negative_t', m)], dim=-1)))
        # Intervention pooling prevents the rare deletion signal vanishing in a global mean.
        deleted = (r * masks.unsqueeze(-1)).sum(1) / masks.sum(1, keepdim=True).clamp(min=1)
        return self.head(torch.cat([r.mean(1), m.mean(1), deleted, r.amax(1), environment], dim=1))

    def propagate(self, name, values):
        if not self.large_graph:
            return getattr(self, name) @ values
        batch, nodes, hidden = values.shape
        flattened = values.permute(1, 0, 2).reshape(nodes, batch * hidden)
        output = torch.sparse.mm(getattr(self, 'sparse_' + name), flattened)
        return output.reshape(output.shape[0], batch, hidden).permute(1, 0, 2)


def train_network(kind, x, masks, target, observed, train_indices, validation_indices,
                  stoich, config, seed, checkpoint, budget=None):
    seed_all(seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(device)
    model = (BipartiteMPNN(stoich, config['hidden_dim']) if kind == 'gnn'
             else MLP(x.shape[1])).to(device)
    # Scaling is estimated exclusively from observed training labels.
    scales = np.array([max(float(np.std(target[train_indices, j][observed[train_indices, j] > 0])), 0.1)
                       if observed[train_indices, j].sum() else 1.0 for j in range(3)], np.float32)
    scaled = target.copy()
    scaled[:, :3] /= scales
    tx = torch.tensor(x, device=device)
    tm = torch.tensor(masks, device=device)
    ty = torch.tensor(scaled, device=device)
    to = torch.tensor(observed, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.0001)
    best, best_state, stale, history = float('inf'), None, 0, []
    started = time.perf_counter()
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    def loss_at(indices):
        prediction = model(tx[indices], tm[indices])
        regression = ((prediction[:, :3] - ty[indices, :3]).square() * to[indices, :3]).sum()
        regression /= to[indices, :3].sum().clamp(min=1)
        classification = nn.functional.binary_cross_entropy_with_logits(prediction[:, 3], ty[indices, 3])
        return regression + classification

    for epoch in range(config['epochs']):
        if budget:
            budget.check()
        model.train()
        shuffled = np.random.permutation(train_indices)
        losses = []
        for offset in range(0, len(shuffled), config['batch_size']):
            if budget:
                budget.check()
            batch = shuffled[offset:offset + config['batch_size']]
            optimizer.zero_grad(set_to_none=True)
            loss = loss_at(batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5)
            optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            validation_loss = np.mean([float(loss_at(validation_indices[i:i + config['batch_size']]))
                                      for i in range(0, len(validation_indices), config['batch_size'])])
        history.append(dict(epoch=epoch + 1, train_loss=float(np.mean(losses)), validation_loss=float(validation_loss)))
        if validation_loss < best - 1e-5:
            best, stale = validation_loss, 0
            best_state = {k: v.detach().cpu().clone().contiguous() for k, v in model.state_dict().items()}
            save_file(best_state, str(checkpoint))
            write_json(checkpoint.with_suffix('.json'), dict(status='partial', kind=kind, seed=seed,
                       scales=scales.tolist(), hidden_dim=config['hidden_dim'],
                       epoch=epoch + 1, best_validation_loss=float(best)))
        else:
            stale += 1
        if stale >= config['patience']:
            break
    model.load_state_dict(best_state)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    save_file(best_state, str(checkpoint))
    metadata = dict(kind=kind, seed=seed, scales=scales.tolist(), hidden_dim=config['hidden_dim'],
                    device=str(device), epochs=len(history), best_validation_loss=float(best),
                    torch_version=torch.__version__,
                    device_name=torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU',
                    peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(device) if device.type == 'cuda' else 0,
                    peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(device) if device.type == 'cuda' else 0,
                    training_seconds=time.perf_counter() - started, history=history)
    write_json(checkpoint.with_suffix('.json'), dict(status='complete', **metadata))
    return model, metadata


def predict_network(model, x, masks, scales, batch_size=128):
    device = next(model.parameters()).device
    model.eval()
    outputs = []
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            values = model(torch.tensor(x[start:start + batch_size], device=device),
                           torch.tensor(masks[start:start + batch_size], device=device))
            values[:, :3] = values[:, :3].clamp(min=0) * torch.tensor(scales, device=device)
            values[:, 3] = values[:, 3].sigmoid()
            outputs.append(values.cpu().numpy())
    return np.concatenate(outputs)
