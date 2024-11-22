from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


def save_model(model_path: Path, pipeline) -> None:
    logger.info("Saving machine learning model")
    joblib.dump(pipeline, model_path)


def load_model(model_path: Path):
    logger.info("Loading machine learning model")
    return joblib.load(model_path)


def standard_in_out(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Prepares input and output for the model.
    """
    X = df[["AccountName", "Description"]].apply(
        lambda row: " ".join(row.values.astype(str)), axis=1
    )
    Y = df["Category"]
    return X, Y


def train(df: pd.DataFrame, model=None, test=False) -> None:
    """
    Train a classification model to categorize transactions.
    """
    logger.info("Training classification model")

    # Define the inputs and outputs
    X, Y = standard_in_out(df)

    if test:
        x_train, x_test, y_train, y_test = train_test_split(
            X, Y, test_size=0.3, random_state=0
        )
    else:
        x_train, x_test, y_train, y_test = X, [], Y, []

    # Create a pipeline for vectorization and classification
    vectorizer = TfidfVectorizer()
    classifier = model if model else LogisticRegression(max_iter=1000)
    pipeline = Pipeline([("vectorizer", vectorizer), ("classifier", classifier)])
    pipeline.fit(x_train, y_train)

    if test:
        y_pred = pipeline.predict(x_test)
        logger.info("Accuracy: {0:.1%}".format(accuracy_score(y_test, y_pred)))
        plot_confusion_matrix(y_test, y_pred, sorted(df["Category"].unique()))
    else:
        save_model("transaction_model.pkl", pipeline)


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


def predict(model_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    """
    Predict categories and confidence scores for new transactions.
    """
    logger.info("Classifying transactions")
    pipeline = load_model(model_path)
    X, _ = standard_in_out(df)

    # Predict categories and confidence scores
    probabilities = pipeline.named_steps["classifier"].predict_proba(
        pipeline.named_steps["vectorizer"].transform(X)
    )
    df["Category"] = pipeline.predict(X)
    df["Confidence"] = probabilities.max(axis=1)  # Maximum probability as confidence

    return df


if __name__ == "__main__":
    db_path = Path("") / "pyguibank.db"
