from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


def save_model(model_path: Path, pipeline: Pipeline, amount: bool) -> None:
    logger.info("Saving machine learning model")
    joblib.dump((pipeline, amount), model_path)


def load_model(model_path: Path) -> tuple[Pipeline, bool]:
    logger.info("Loading machine learning model")
    return joblib.load(model_path)


def prepare_data(
    df: pd.DataFrame, amount: bool
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    # Define numeric and text feature sets
    numeric_features = ["Amount"] if amount else []
    text_features = ["Company", "AccountType", "Description"]
    features = {"text": "TextFeatures", "num": numeric_features}

    # Create text features column
    df[features["text"]] = df[text_features].apply(
        lambda row: " ".join(row.values.astype(str)), axis=1
    )

    # Inputs are concatenated text features plus numeric columns
    X = df[[features["text"]] + features["num"]]
    Y = df["Category"]

    return X, Y, features


def prepare_pipeline(features: dict) -> Pipeline:
    # Build the preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(), features["text"]),
            ("num", StandardScaler(), features["num"]),
        ]
    )

    # Build the pipeline
    classifier = LinearSVC()
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    return pipeline


def plot_confusion_matrix(y_test, y_pred, categories, normalized=True) -> None:
    """
    Generate a confusion matrix.
    """
    conf_mat = confusion_matrix(y_test, y_pred, labels=categories)
    if normalized:
        conf_mat_normalized = conf_mat.astype("float") / conf_mat.sum(
            axis=1, keepdims=True
        )
        sns.heatmap(
            conf_mat_normalized,
            annot=True,
            fmt=".2f",
            xticklabels=categories,
            yticklabels=categories,
            cmap="Blues",
        )
    else:
        sns.heatmap(
            conf_mat,
            annot=True,
            fmt="d",
            xticklabels=categories,
            yticklabels=categories,
        )
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.show()


def train_pipeline_test(df: pd.DataFrame, amount=False) -> None:
    """
    Train a classification model for testing only.

    Several models were tested with and without a numeric Amount
    column included. The Amount column always degraded performance
    by a fraction of a percent. With text input only, accuracy was
    - LogisticRegression: 94.0%
    - LinearSVC: 97.2%
    - RandomForest: 93.1%
    """
    logger.info("Training classification model to test accuracy")

    # Prepare the training set and preprocessor
    X, Y, features = prepare_data(df, amount)
    pipeline = prepare_pipeline(features)

    # Train-Test split
    x_train, x_test, y_train, y_test = train_test_split(
        X, Y, test_size=0.3, random_state=0
    )

    # Train pipeline
    pipeline.fit(x_train, y_train)

    # Report accuracy and display confusion matrix
    y_pred = pipeline.predict(x_test)
    logger.info("Accuracy: {0:.1%}".format(accuracy_score(y_test, y_pred)))
    plot_confusion_matrix(y_test, y_pred, sorted(df["Category"].unique()))


def train_pipeline_save(df: pd.DataFrame, model_path: Path, amount=False) -> None:
    """
    Train a classification model to save for future categorization.
    """
    logger.info("Training classification pipeline for later use.")

    # Prepare the training set and preprocessor
    x_train, y_train, features = prepare_data(df, amount)
    pipeline = prepare_pipeline(features)

    # Train base pipeline
    pipeline.fit(x_train, y_train)

    save_model(model_path, pipeline, amount)
    logger.success("Pipeline saved to {d}", d=model_path)


def confidence_score(pipeline: Pipeline, x_test: pd.DataFrame):
    """Estimates confidence score based on pseudo-probability

    Args:
        x_test (_type_): _description_
        pipeline (Pipeline): _description_

    Returns:
        _type_: _description_
    """
    decision_scores = pipeline.decision_function(x_test)
    pseudo_probabilities = np.exp(decision_scores) / np.sum(
        np.exp(decision_scores), axis=1, keepdims=True
    )
    confidence = pseudo_probabilities.max(axis=1)
    return confidence


def predict(model_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    """
    Predict categories and confidence scores for new transactions.
    """
    logger.info("Classifying transactions")
    pipeline, amount = load_model(model_path)

    # Get data in same format that was used to train the pipeline
    X, _ = prepare_data(df, amount)

    # Predict categories and confidence scores
    df["Category"] = pipeline.predict(X)
    df["Confidence"] = confidence_score(X, pipeline)
    return df


if __name__ == "__main__":
    db_path = Path("") / "pyguibank.db"
