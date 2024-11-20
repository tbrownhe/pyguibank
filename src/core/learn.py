from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from loguru import logger
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

"""
Most of this was lifted from these:
https://towardsdatascience.com/multi-class-text-classification-with-scikit-learn-12f1e60e0a9f
https://github.com/drojasug/ClassifyingExpensesSciKitLearn/blob/master/MyBudget.ipynb
"""


def save_model(
    model_path: Path, vectorizer: CountVectorizer, classifier: LinearSVC
) -> None:
    logger.info("Freezing machine learning model")
    joblib.dump((vectorizer, classifier), model_path)


def load_model(model_path: Path) -> tuple[CountVectorizer, LinearSVC]:
    logger.info("Loading machine learning model")
    vectorizer, classifier = joblib.load(model_path)
    return vectorizer, classifier


def standard_in_out(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Ensures that any future tweaks of the classifier inputs and outputs apply
    equally to all dependent functions.
    """
    # Concatenate account nickname and description to allow account differentiation.
    X = df[["AccountName", "Description"]].apply(
        lambda row: " ".join(row.values.astype(str)), axis=1
    )
    Y = df["Category"]
    return X, Y


def train(df: pd.DataFrame, model=LinearSVC(), test=False) -> None:
    """
    Uses the categorized transactions in the DataFrame to train the chosen ML model.
    """
    logger.info("Training {m} model", m=str(model))

    # Define the inputs and outputs
    # Input includes the account nickname to enable account differentiation.
    X, Y = standard_in_out(df)

    if test:
        # Train the model on a large fraction of the transactions
        x_train, x_test, y_train, y_test = train_test_split(
            X, Y, test_size=0.3, random_state=0
        )
    else:
        # Train the model on the entire available set
        x_train, x_test, y_train, y_test = X, [], Y, []

    # Create and train the ML model using the training set
    vectorizer = CountVectorizer()
    x_train_counts = vectorizer.fit_transform(x_train)
    tfidf = TfidfTransformer()
    x_train_tfidf = tfidf.fit_transform(x_train_counts)
    classifier = model.fit(x_train_tfidf, y_train)

    if test:
        # Test the accuracy of the model
        x_test_counts = vectorizer.transform(x_test)
        y_pred = classifier.predict(x_test_counts)
        score = classifier.score(x_test_counts, y_test)
        logger.info("Classifier accuracy is {a}", a="{0:.1%}".format(score))
        # plot confusion matrix is broken, not sure why
        plot_confusion_matrix(y_test, y_pred, df["Category"].unique())
    else:
        # Save the trained model to disk
        save_model(vectorizer, classifier)


def plot_confusion_matrix(y_test, y_pred, category_list) -> None:
    """
    Generate a confusion matrix
    """
    logger.info("Generating Confusion Matrix")
    conf_mat = confusion_matrix(y_test, y_pred, labels=category_list)
    fig, ax = plt.subplots(figsize=(6, 6))
    sns.heatmap(
        conf_mat,
        annot=True,
        fmt="d",
        xticklabels=category_list,
        yticklabels=category_list,
    )
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.show()


def predict(model_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    """
    Use trained model to predict category of transactions.
    """
    logger.info("Classifying uncategorized transactions")

    # Load the pre-trained model components
    vectorizer, classifier = load_model(model_path)

    # Get the standardized input for the learning model
    X, _ = standard_in_out(df)

    # Apply the trained model to new transactions
    df["Category"] = classifier.predict(vectorizer.transform(X))

    return df


if __name__ == "__main__":
    print("This module is not designed to be run as __main__")
