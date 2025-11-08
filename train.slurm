#!/bin/bash
#SBATCH --job-name=chess_training       # Job name
#SBATCH --partition=nvidia              # Partition (nvidia for GPU nodes)
#SBATCH --nodes=1                       # Number of nodes
#SBATCH --ntasks=1                      # Number of tasks (1 for single-node)
#SBATCH --cpus-per-task=12              # CPU cores (12 as requested)
#SBATCH --gres=gpu:4                    # GPUs (4 as requested)
#SBATCH --mem=64G                       # Memory (adjust as needed)
#SBATCH --time=24:00:00                 # Time limit (24 hours)
#SBATCH --output=logs/chess_train_%j.out   # Standard output log
#SBATCH --error=logs/chess_train_%j.err    # Standard error log
#SBATCH --mail-type=BEGIN,END,FAIL      # Email notifications
#SBATCH --mail-user=your_email@domain.com  # Your email

# ============================================================================
# Chess Model Training - SLURM Job Script
# ============================================================================

echo "=========================================="
echo "Job started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "=========================================="
echo ""

# Print GPU info
echo "GPU Information:"
nvidia-smi
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs
mkdir -p checkpoints

# Load required modules (adjust based on your HPC environment)
# Uncomment and modify these lines based on your cluster's module system
# module purge
# module load cuda/11.8
# module load python/3.10
# module load gcc/9.3.0

# Activate virtual environment (if using one)
# source ~/venvs/chess/bin/activate

# Or use conda
# conda activate chess

# Print Python and PyTorch info
echo "Python version:"
python --version
echo ""

echo "PyTorch version and CUDA availability:"
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'Number of GPUs: {torch.cuda.device_count()}')"
echo ""

# Set environment variables for optimal performance
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export CUDA_VISIBLE_DEVICES=0,1,2,3

echo "Environment:"
echo "  OMP_NUM_THREADS: $OMP_NUM_THREADS"
echo "  CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo ""

# ============================================================================
# Training Configuration
# ============================================================================

# Dataset path - CHANGE THIS to your dataset location
DATASET_PATH="/path/to/your/dataset.jsonl"

# Training parameters
MAX_SAMPLES=10000000        # 10 million samples
BATCH_SIZE=512              # Batch size per GPU (total = 512 * 4 = 2048)
EPOCHS=20                   # Number of epochs
LEARNING_RATE=0.001         # Learning rate
NUM_WORKERS=12              # DataLoader workers
VAL_SPLIT=0.05              # Validation split (5%)

# Output paths
SAVE_PATH="chess_model_final.pth"
CHECKPOINT_DIR="checkpoints"

echo "Training Configuration:"
echo "  Dataset: $DATASET_PATH"
echo "  Max samples: $MAX_SAMPLES"
echo "  Batch size: $BATCH_SIZE per GPU (total: $((BATCH_SIZE * 4)))"
echo "  Epochs: $EPOCHS"
echo "  Learning rate: $LEARNING_RATE"
echo "  Workers: $NUM_WORKERS"
echo "  Validation split: $VAL_SPLIT"
echo ""

# ============================================================================
# Run Training
# ============================================================================

echo "Starting training..."
echo "=========================================="
echo ""

python train.py \
    --dataset "$DATASET_PATH" \
    --max-samples $MAX_SAMPLES \
    --batch-size $BATCH_SIZE \
    --epochs $EPOCHS \
    --lr $LEARNING_RATE \
    --num-workers $NUM_WORKERS \
    --save-path "$SAVE_PATH" \
    --checkpoint-dir "$CHECKPOINT_DIR" \
    --val-split $VAL_SPLIT

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Training completed successfully!"
    echo "Final model saved to: $SAVE_PATH"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "Training failed with exit code: $?"
    echo "=========================================="
    exit 1
fi

echo ""
echo "Job finished at: $(date)"
echo ""

# Optional: Copy model to a different location
# cp $SAVE_PATH /path/to/final/destination/

# Optional: Clean up old checkpoints (keep only last 5)
# ls -t checkpoints/checkpoint_epoch_*.pth | tail -n +6 | xargs -r rm
