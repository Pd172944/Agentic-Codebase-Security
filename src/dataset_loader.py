"""Dataset loader for HuggingFace Code Vulnerability Security dataset."""

import random
from typing import List, Dict
from datasets import load_dataset
from src.utils.logger import setup_logger

logger = setup_logger("dataset_loader")

class DatasetLoader:
    """Loads and samples from the Code Vulnerability Security DPO dataset."""

    def __init__(
        self,
        dataset_name: str,
        sample_size: int,
        random_seed: int = 42,
        filter_language: str = None
    ):
        """
        Initialize dataset loader.

        Args:
            dataset_name: HuggingFace dataset identifier
            sample_size: Number of samples to load
            random_seed: Random seed for reproducibility
            filter_language: Optional language filter (e.g., "Python")
        """
        self.dataset_name = dataset_name
        self.sample_size = sample_size
        self.random_seed = random_seed
        self.filter_language = filter_language
        random.seed(random_seed)

        logger.info(f"Loading dataset: {dataset_name}")
        if filter_language:
            logger.info(f"Filtering for language: {filter_language}")
        self.dataset = None
        self.samples = None

    def load(self) -> List[Dict]:
        """
        Load dataset from HuggingFace and sample examples.

        Returns:
            List of sampled examples with required fields
        """
        try:
            # Load dataset
            logger.info("Fetching dataset from HuggingFace...")
            self.dataset = load_dataset(self.dataset_name, split="train")
            total_size = len(self.dataset)
            logger.info(f"Loaded {total_size} examples from dataset")

            # Filter by language if specified
            if self.filter_language:
                filtered_indices = [
                    i for i in range(total_size)
                    if self.dataset[i]["lang"] == self.filter_language
                ]
                logger.info(
                    f"Filtered to {len(filtered_indices)} {self.filter_language} examples"
                )
            else:
                filtered_indices = list(range(total_size))

            # Sample randomly from filtered set
            if self.sample_size >= len(filtered_indices):
                logger.warning(
                    f"Sample size {self.sample_size} >= available examples {len(filtered_indices)}. "
                    "Using all available examples."
                )
                indices = filtered_indices
            else:
                indices = random.sample(filtered_indices, self.sample_size)

            # Extract samples with proper field mapping
            self.samples = []
            for idx in indices:
                example = self.dataset[idx]
                self.samples.append({
                    "id": idx,
                    "language": example["lang"],
                    "vulnerability": example["vulnerability"],
                    "task_description": example["question"],
                    "vulnerable_code": example["rejected"],  # "rejected" is the vulnerable code
                    "fixed_code": example["chosen"],  # "chosen" is the secure/fixed code
                })

            logger.info(f"Sampled {len(self.samples)} examples")

            # Log language distribution
            lang_dist = {}
            for sample in self.samples:
                lang = sample["language"]
                lang_dist[lang] = lang_dist.get(lang, 0) + 1

            logger.info("Language distribution:")
            for lang, count in sorted(lang_dist.items()):
                logger.info(f"  {lang}: {count}")

            return self.samples

        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise

    def get_samples(self) -> List[Dict]:
        """Get loaded samples (loads if not already loaded)."""
        if self.samples is None:
            return self.load()
        return self.samples
