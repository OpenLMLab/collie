import sys

sys.path.append('../../')
sys.path.append("/mnt/petrelfs/gutianle/Megatron-LM/")


from transformers import LlamaTokenizer
from transformers.generation.utils import GenerationConfig

from collie.data import CollieDatasetForTraining
from collie.config import CollieConfig
from collie.controller.trainer import Trainer
from collie.metrics import BaseMetric
from collie.models.llama.model import LlamaForCausalLM
from collie.metrics.decode import DecodeMetric
from collie.utils import env, setup_distribution
from collie.utils.monitor import StepTimeMonitor, TGSMonitor, MemoryMonitor, LossMonitor, EvalMonitor, LRMonitor

class LLaMaWithMonitor:
    """
    LLaMaWithMonitor是一个测试各种Monitor是否成功运行的类。
    Monitor的选择有StepTimeMonitor, TSGMonitor, MemoryMonitor, LossMonitor和EvalMonitor（具体可见`collie.utils.monitor`）
    本类提供九种测试选择：
        * test_step_time_monitor：测试StepTimeMonitor
        * test_tgs_monitor：测试TGSMonitor
        * test_memory_monitor：测试MemoryMonitor
        * test_loss_monitor：测试LossMonitor
        * test_eval_monitor：测试EvalMonitor
        * test_lr_monitor：测试LRMonitor
        * test_all_monitors：测试所有的Monitor混合使用
        * test_tensorboard：测试Tensorboard模式
        * test_csv：测试csv模式
        * test_wandb：测试wandb模式
    """
    def __init__(self) -> None:
        self.monitors = None
        # set deepspeed config
        self.config = self._setConfig()
        # initialize deepspeed env
        setup_distribution(self.config)
        
    def _setConfig(self):
        config = CollieConfig.from_pretrained("decapoda-research/llama-7b-hf")
        config.tp_size = 4
        config.dp_size = 1
        config.pp_size = 1
        config.train_epochs = 10
        config.train_micro_batch_size = 1
        config.ds_config = {
            "fp16": {"enabled": True},
            "optimizer": {
                "type": "Adam",
                "params": {
                    "lr": 2e-5
                }
            },
            "monitor_config": {
                "enabled": True,
                "tensorboard": {
                    "enabled": True,
                    "output_path": "./ds_logs/",
                    "job_name": "alpaca_monitor"
                }
            }
        }
        return config

    def _train(self):
        monitors = self.monitors
        assert monitors != None, "Variable monitors is none"
        tokenizer = LlamaTokenizer.from_pretrained("decapoda-research/llama-7b-hf", add_eos_token=True)
        model = LlamaForCausalLM.from_config(self.config)
        train_dataset = [
            {
                'input': 'Collie is ',
                'output': 'a python package for finetuning large language models'
            } for _ in range(100) 
        ]
        # convert to collie dataset
        train_dataset = CollieDatasetForTraining(train_dataset, tokenizer)
        trainer = Trainer(
            model = model,
            train_dataset = train_dataset,
            monitors = monitors,
            metrics = {'decode': DecodeMetric(tokenizer=tokenizer)},
            config = self.config
        )
        trainer.train()
        
    def _eval(self):
        monitors = self.monitors
        assert monitors != None, "Variable monitors is none"
        tokenizer = LlamaTokenizer.from_pretrained("decapoda-research/llama-7b-hf", add_eos_token=True)
        model = LlamaForCausalLM.from_config(self.config)
        eval_dataset = [
            {
                'input': 'Collie is ',
                'output': 'a python package for finetuning large language models'
            } for _ in range(8) 
        ]
        # convert to collie dataset
        eval_dataset = CollieDatasetForTraining(eval_dataset, tokenizer)
        trainer = Trainer(
            model = model,
            eval_dataset = eval_dataset,
            monitors = monitors,
            metrics = {'decode': DecodeMetric(tokenizer=tokenizer)},
            generation_config=GenerationConfig(max_new_tokens=32, 
                                        eos_token_id=2, 
                                        pad_token_id=0, 
                                        bos_token_id=1),
            config = self.config
        )
        trainer.eval()
        
    """
    测试StepTimeMonitor
    """
    def test_step_time_monitor(self):
        self.monitors = [StepTimeMonitor(self.config)]
        self._train()
    
    """
    测试TGSMonitor
    """
    def test_tgs_monitor(self):
        self.monitors = [TGSMonitor(self.config)]
        self._train()
    
    """
    测试MemoryMonitor
    """
    def test_memory_monitor(self):
        self.monitors = [MemoryMonitor(self.config)]
        self._train()
    
    """
    测试LossMonitor
    """
    def test_loss_monitor(self):
        self.monitors = [LossMonitor(self.config)]
        self._train()
    
    """
    测试eval的结果
    """
    def test_eval_monitor(self):
        self.monitors = [EvalMonitor(self.config)]
        self._eval()
        
    """
    测试learning rate的结果
    """
    def test_lr_monitor(self):
        self.monitors = [LRMonitor(self.config)]
        self._train()
    
    """
    测试所有monitor混合的结果
    """
    def test_all_monitors(self):
        self.config.eval_batch_size = 1
        self.config.eval_per_n_steps = 1
        
        self.monitors = [
            StepTimeMonitor(self.config),
            TGSMonitor(self.config),
            MemoryMonitor(self.config),
            LossMonitor(self.config),
            EvalMonitor(self.config)
        ]
        self._train()
    
    """
    测试Tensorboard
    """
    def test_tensorboard(self):
        self._train()
    
    """
    测试csv
    """
    def test_csv(self):
        self.config.ds_config["monitor_config"] = {
            "enabled": True,
            "csv_monitor": {
                "enabled": True,
                "output_path": "./ds_logs/",
                "job_name": "alpaca_monitor"
            }
        }
        self.test_memory_monitor()
        
    """
    测试wandb
    """
    def test_wandb(self):
        self.config.ds_config['monitor_config'] = {
            "enabled": True,
            "group": "my_group",
            "team": "my_team",
            "project": "my_project"
        }
        self.test_memory_monitor()

# CUDA_VISIBLE_DEVICES=0,1,2,3 torchrun --rdzv_backend=c10d --rdzv_endpoint=localhost:28002 --nnodes=1 --nproc_per_node=4 test_monitor.py
monitor_test = LLaMaWithMonitor()
# monitor_test.test_step_time_monitor()
monitor_test.test_lr_monitor()
    