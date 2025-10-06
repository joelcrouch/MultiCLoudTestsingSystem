"""
Protein dataset loading and preprocessing
Supports CB513, CullPDB, and CASP datasets
Downloads from public sources, parses FASTA format
"""

import os
import requests
import gzip
import numpy as np
from typing import List, Tuple, Dict, Optional
import torch
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import pickle