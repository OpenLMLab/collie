""" **CoLLie** 中的通用 ``collate_fn`` 构造器
"""
import sys
sys.path.append("/mnt/petrelfs/zhangshuo/projects/collie/")
from typing import Sequence, Any, List, Tuple, Dict
import torch
import torch.nn.functional as F
import numpy as np

__all__ = [
    "ColliePadder"
]

class ColliePadder:
    """ **CoLLie** 中的通用 ``collate_fn`` 构造器
    :param padding_token: 用于填充模型输入数据 (input_ids) 的 token
    :param labels_padding_token: 用于填充模型标签数据 (labels) 的 token
    :param padding_left: 是否在左侧填充
    """
    def __init__(self, 
                 padding_token_id: int=0,
                 labels_padding_token_id: int=-100,
                 padding_left: bool = False) -> None:
        self.padding_token_id = padding_token_id
        self.labels_padding_token_id = labels_padding_token_id
        self.padding_left = padding_left
        self.mode = "input_ids"
        
    def collate_fn(self, batch: Sequence[Any]) -> torch.Tensor:
        """ 用于填充的 ``collate_fn``
        :param batch: 一个 batch 的数据
        :return: 填充后的 batch
        """
        if self.mode == "input_ids":
            padding_token_id = self.padding_token_id
        else:
            padding_token_id = self.labels_padding_token_id
        batch = list(batch)
        if isinstance(batch[0], torch.Tensor):
            pass
        elif isinstance(batch[0], (int, float)):
            batch = [torch.tensor(x) for x in batch]
        elif isinstance(batch[0], np.ndarray):
            batch = [torch.from_numpy(x) for x in batch]
        elif isinstance(batch[0], list):
            batch = [torch.tensor(x) for x in batch]
        else:
            raise TypeError(f"Unsupported type: {type(batch[0])}")
        for i in range(len(batch)):
            sample = batch[i]
            shape = []
            for s in sample.shape:
                if s > 1:
                    shape.append(s)
            if not shape:
                shape.append(1)
            sample = sample.view(*shape)
            batch[i] = sample
        max_shape = max([x.shape for x in batch])
        for i in range(len(batch)):
            shape = (torch.tensor(max_shape) - torch.tensor(batch[i].shape)).cpu().tolist()
            if self.padding_left:
                batch[i] = F.pad(batch[i], [shape.pop() if d % 2 == 0 else 0 for d in range(len(shape) * 2)], value=padding_token_id)
            else:
                batch[i] = F.pad(batch[i], [shape.pop() if (d + 1) % 2 == 0 else 0 for d in range(len(shape) * 2)], value=padding_token_id)
        return torch.stack(batch, dim=0)
    
    def __call__(self, batch: List[Tuple]) -> Any:
        assert len(batch[0]) == 2, "Samples from dataset must be a tuple of size 2. Eg: (input_ids, labels)"
        padded_batch = []
        for i in range(2):
            if i == 0:
                self.mode = "input_ids"
            else:
                self.mode = "labels"
            if isinstance(batch[0][i], (torch.Tensor, np.ndarray, list, int, float)):
                padded_batch.append(self.collate_fn([x[i] for x in batch]))
            elif isinstance(batch[0][i], tuple):
                padded_batch.append(tuple([self.collate_fn([x[i][j] for x in batch]) for j in range(len(batch[0][i]))]))
            elif isinstance(batch[0][i], Dict):
                padded_dict = {}
                for key in batch[0][i].keys():
                    if isinstance(batch[0][i][key], (torch.Tensor, np.ndarray, list, int, float)):
                        padded_dict[key] = self.collate_fn([x[i][key] for x in batch])
                    elif isinstance(batch[0][i][key], tuple) and isinstance(batch[0][i][key][0], (torch.Tensor, np.ndarray, list)):
                        padded_dict[key] = [self.collate_fn([x[i][key][j] for x in batch]) for j in range(len(batch[0][i][key]))]
                    else:
                        raise TypeError(f"Unsupported type: {type(batch[0][i][key])}")
                padded_batch.append(padded_dict)
            else:
                raise TypeError(f"Unsupported type: {type(batch[0][i])}")
        return tuple(padded_batch)