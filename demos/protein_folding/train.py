"""
Main training script for protein secondary structure prediction
Integrates with (hopefully on first try) multi-cloud distributed training infrastructure
"""

import argparse
import json
import os
import time
import torch
from torch.utils.data import DataLoader
from typing import Dict

from data_loader import (
    create_dataloaders,
    DataLoader,
    ProteinDataset,
    train_val_test_split
)

from protein_trainer import (
    count_parameters, 
    get_model_size_mb,
    ProteinTrainer,
    ProteinTransformer 
)