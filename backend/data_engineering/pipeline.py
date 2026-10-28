"""
End-to-end Feature Engineering and Dataset Pipeline.
Coordinates feature extraction, normalization, target encoding, and partitioned dataset generation.
"""

from typing import Dict, Tuple, Optional, Union
from pathlib import Path
import pandas as pd

from .extractor import TemporalFeatureExtractor
from .preprocessor import FeaturePreprocessor
from .dataset import DatasetManager


class FeaturePipeline:
    """
    Unified pipeline executing temporal extraction, preprocessing, and ML dataset preparation.
    """

    def __init__(
        self,
        window_sizes: Optional[list] = None,
        preprocessor: Optional[FeaturePreprocessor] = None
    ):
        self.extractor = TemporalFeatureExtractor(window_sizes=window_sizes)
        self.preprocessor = preprocessor if preprocessor is not None else FeaturePreprocessor()
        self.dataset_manager = DatasetManager()

    def process_dataframe(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """
        Extracts temporal features, encodes target labels, and scales numeric predictors.
        """
        # 1. Temporal & spatial feature extraction
        extracted_df = self.extractor.extract_features(df)

        # 2. Format target labels
        labeled_df = self.dataset_manager.format_targets(extracted_df)

        # 3. Scale and encode features
        if fit or not self.preprocessor.is_fitted:
            processed_df = self.preprocessor.fit_transform(labeled_df)
        else:
            processed_df = self.preprocessor.transform(labeled_df)

        return processed_df

    def create_partitioned_datasets(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Dict[str, pd.DataFrame]:
        """
        Executes end-to-end processing and chronologically splits into train, val, and test sets.
        Fits preprocessor ONLY on the training split to prevent any data leakage.
        """
        # 1. Feature extraction on full timeline to allow continuous rolling windows
        extracted_df = self.extractor.extract_features(df)
        labeled_df = self.dataset_manager.format_targets(extracted_df)

        # 2. Chronological partition before fitting scaler
        raw_train, raw_val, raw_test = self.dataset_manager.split_chronological(
            labeled_df, train_ratio=train_ratio, val_ratio=val_ratio, test_ratio=test_ratio
        )

        # 3. Fit preprocessor strictly on training data
        train_df = self.preprocessor.fit_transform(raw_train)
        val_df = self.preprocessor.transform(raw_val)
        test_df = self.preprocessor.transform(raw_test)

        # Transform entire dataset with train-fitted scaler
        full_df = self.preprocessor.transform(labeled_df)

        return {
            "full": full_df,
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }
