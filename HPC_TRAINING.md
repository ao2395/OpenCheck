# HPC Training Guide

This guide explains how to train the chess model on an HPC cluster with SLURM.

## Files

- `train.py` - Python training script with multi-GPU support
- `train.slurm` - SLURM batch script for job submission

## Quick Start

### 1. Prepare Your Environment

```bash
# Create a conda environment (recommended)
conda create -n chess python=3.10
conda activate chess

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install python-chess numpy tqdm

# Or use requirements.txt
pip install -r requirements.txt
```

### 2. Configure the SLURM Script

Edit `train.slurm` and update:

```bash
# Your dataset path
DATASET_PATH="/path/to/your/dataset.jsonl"

# Your email for notifications
#SBATCH --mail-user=your_email@domain.com

# Module loads (based on your cluster)
# module load cuda/11.8
# module load python/3.10
```

### 3. Make Script Executable

```bash
chmod +x train.py
```

### 4. Submit the Job

```bash
# Create logs directory
mkdir -p logs

# Submit to SLURM
sbatch train.slurm
```

### 5. Monitor the Job

```bash
# Check job status
squeue -u $USER

# View live output
tail -f logs/chess_train_<JOB_ID>.out

# Check GPU usage
ssh <node> nvidia-smi
```

## Resource Allocation

The SLURM script requests:
- **12 CPUs** - For data loading (12 DataLoader workers)
- **4 GPUs** - For parallel training with DataParallel
- **64GB RAM** - Enough for 10M dataset in memory
- **24 hours** - Adjust based on your dataset size

### Expected Performance

With 4 GPUs and 10M samples:
- **Loading time**: ~5 minutes
- **Training time**: ~3-4 hours (20 epochs)
- **Total job time**: ~4-5 hours

With full 300M samples (not recommended):
- **Loading time**: ~2 hours
- **Training time**: ~24+ hours (20 epochs)
- **Total job time**: ~30+ hours

## Configuration Options

### Command-line arguments for `train.py`:

```
--dataset PATH           Dataset JSONL file (required)
--max-samples N          Max samples to load (default: 10M)
--batch-size N           Batch size per GPU (default: 512)
--epochs N               Number of epochs (default: 20)
--lr FLOAT               Learning rate (default: 0.001)
--num-workers N          DataLoader workers (default: 12)
--save-path PATH         Output model path (default: chess_model.pth)
--checkpoint-dir PATH    Checkpoint directory (default: checkpoints)
--val-split FLOAT        Validation split (default: 0.05)
```

### Example with custom settings:

```bash
python train.py \
    --dataset /data/chess/positions.jsonl \
    --max-samples 20000000 \
    --batch-size 1024 \
    --epochs 30 \
    --lr 0.0005 \
    --num-workers 16
```

## Multi-GPU Training

The script automatically uses all available GPUs with DataParallel:

```python
# Automatic multi-GPU
if torch.cuda.device_count() > 1:
    model = DataParallel(model)
```

**Effective batch size** = `batch_size × num_gpus`
- With 4 GPUs and batch_size=512: **Total = 2048 samples/batch**

## Checkpointing

The script saves:
- **Best model**: `chess_model_final.pth` (highest validation accuracy)
- **Epoch checkpoints**: `checkpoints/checkpoint_epoch_N.pth` (every epoch)

Each checkpoint contains:
- Model state dict
- Optimizer state
- Scheduler state
- Training history
- Accuracy metrics

### Resume from checkpoint:

```python
# Load checkpoint
checkpoint = torch.load('checkpoints/checkpoint_epoch_15.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
start_epoch = checkpoint['epoch'] + 1
```

## Troubleshooting

### Out of Memory (OOM)

```bash
# Reduce batch size
--batch-size 256

# Reduce workers
--num-workers 8

# Request more RAM in SLURM
#SBATCH --mem=128G
```

### Job Killed (Time Limit)

```bash
# Increase time limit in train.slurm
#SBATCH --time=48:00:00

# Or reduce dataset size
--max-samples 5000000
```

### CUDA Not Available

```bash
# Check modules
module list

# Load CUDA
module load cuda/11.8

# Check PyTorch installation
python -c "import torch; print(torch.cuda.is_available())"
```

### Slow Data Loading

```bash
# Copy dataset to local fast storage first
cp /slow/storage/dataset.jsonl $TMPDIR/
python train.py --dataset $TMPDIR/dataset.jsonl ...
```

## Monitoring Training

### Real-time monitoring:

```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# Watch training progress
tail -f logs/chess_train_*.out | grep "Epoch"
```

### Check training metrics:

The output shows:
- Training/validation loss
- Training/validation accuracy
- Learning rate updates
- Checkpoint saves

```
Epoch 5/20
----------------------------------------------------------------------
Epoch 5 - Training: 100%|██████████| 17578/17578 [12:34<00:00, 23.31it/s, loss=1.2345, acc=62.45%]
Epoch 5 - Validation: 100%|██████████| 926/926 [01:23<00:00, 11.14it/s, loss=1.1234, acc=64.32%]

Results:
  Train Loss: 1.2345, Train Acc: 62.45%
  Val Loss: 1.1234, Val Acc: 64.32%
  Saved checkpoint: checkpoints/checkpoint_epoch_5.pth
  ✓ New best model! Saved to chess_model_final.pth (Val Acc: 64.32%)
```

## After Training

### 1. Copy the model to your local machine:

```bash
# From HPC to local
scp user@hpc:/path/to/chess_model_final.pth models/
```

### 2. Test the model:

```python
from src.engine.model import ChessEngine

engine = ChessEngine('models/chess_model_final.pth')
move = engine.get_best_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")
print(f"Best move: {move}")
```

### 3. Run OpenCheck:

```bash
python src/main.py
```

## Performance Tips

1. **Use fast storage**: Copy dataset to `$TMPDIR` or local SSD
2. **Optimize workers**: `num_workers = num_cpus` for best I/O
3. **Batch size**: Maximize without OOM (try 512-1024 per GPU)
4. **Pin memory**: Already enabled in script for faster GPU transfers
5. **Sample data**: 10M samples is optimal (don't use full 300M!)

## Common SLURM Commands

```bash
# Submit job
sbatch train.slurm

# Check queue
squeue -u $USER

# Cancel job
scancel <JOB_ID>

# Job details
scontrol show job <JOB_ID>

# Past jobs
sacct -u $USER --format=JobID,JobName,State,Elapsed,MaxRSS

# Node info
sinfo -N -l
```

## Cluster-Specific Notes

Different HPC clusters may require different module names:

```bash
# Example for different clusters

# Cluster A
module load cuda/11.8
module load python/3.10

# Cluster B
module load nvidia/cuda/11.8
module load lang/python/3.10.5

# Cluster C
module load cudatoolkit/11.8
module load anaconda3
```

Check your cluster's documentation or ask your admin for the correct modules.
