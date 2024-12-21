import re

import nltk
import pandas as pd
from scipy.sparse import hstack
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler


def preprocess_text(description: str) -> str:
    """
    Normalize and preprocess the transaction description.
    """
    # Download stopwords if necessary
    try:
        from nltk.corpus import stopwords
    except LookupError:
        nltk.download("stopwords")
        from nltk.corpus import stopwords

    # Normalize text and remove special characters
    stop_words = set(stopwords.words("english"))
    description = description.lower()
    description = re.sub(r"[^a-z0-9\s]", "", description)
    tokens = [word for word in description.split() if word not in stop_words]
    return " ".join(tokens)


def cluster_transactions(
    transactions: pd.DataFrame,
    eps=0.5,
    min_samples=2,
    include_amount=False,
):
    """
    Cluster similar transaction descriptions using TF-IDF and DBSCAN.

    Args:
        transactions (pd.DataFrame): DataFrame with 'Description' and 'Date'.
        eps (float): DBSCAN epsilon (distance threshold).
        min_samples (int): Minimum samples per cluster.

    Returns:
        pd.DataFrame: Transactions with an additional 'Cluster' column.
    """
    # Preprocess text
    transactions["Normalized"] = transactions["Description"].apply(preprocess_text)

    # Convert to numerical vectors using TF-IDF
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(transactions["Normalized"])

    # Construct the DBSCAN clusterer
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")

    if include_amount:
        # Normalize the 'Amount' column to 0-1 range
        scaler = MinMaxScaler()
        amount_scaled = scaler.fit_transform(transactions[["Amount"]])

        # Combine TF-IDF and Amount features
        combined_features = hstack([tfidf_matrix, amount_scaled])

        # Run the clustering for description + amount
        clusters = dbscan.fit_predict(combined_features)
    else:
        # Run the clustering for description only
        clusters = dbscan.fit_predict(tfidf_matrix)

    # Add cluster labels to the DataFrame
    index = transactions.columns.to_list().index("Description")
    transactions.insert(loc=index, column="Cluster", value=clusters)

    return transactions


def identify_recurring_clusters(
    transactions: pd.DataFrame, min_frequency=3, max_interval=35
):
    """
    Identify recurring clusters based on transaction dates and frequency.

    Args:
        transactions (pd.DataFrame): DataFrame with 'Cluster' and 'Date'.
        date_col (str): Name of the date column.
        min_frequency (int): Minimum number of occurrences for a cluster to be considered recurring.
        max_interval (int): Maximum interval (in days) for a cluster to be considered recurring.

    Returns:
        pd.DataFrame: Filtered DataFrame with recurring clusters.
    """
    recurring = []
    for cluster_id, group in transactions.groupby("Cluster"):
        if cluster_id == -1:  # Skip noise
            continue

        # Check frequency
        if len(group) < min_frequency:
            continue

        # Check regularity of dates
        group = group.sort_values("Date")
        intervals = group["Date"].diff().dt.days.dropna()
        if intervals.mean() <= max_interval:
            recurring.append(cluster_id)

    return transactions[transactions["Cluster"].isin(recurring)]


def filter_by_amount_variance(
    transactions: pd.DataFrame, max_variance: float
) -> pd.DataFrame:
    """
    Filter clusters to include only those with similar amounts.

    Args:
        transactions (pd.DataFrame): Transactions with 'Cluster' and 'Amount'.
        max_variance (float): Maximum allowable relative variance in amounts within a cluster.

    Returns:
        pd.DataFrame: Filtered transactions.
    """
    recurring = []
    for cluster_id, group in transactions.groupby("Cluster"):
        if cluster_id == -1:  # Skip noise
            continue

        # Compute relative variance in amounts
        variance = group["Amount"].std() / group["Amount"].mean()
        if variance <= max_variance:
            recurring.append(cluster_id)

    return transactions[transactions["Cluster"].isin(recurring)]


def recurring_transactions(transactions: pd.DataFrame, **kwargs):
    # Convert db date to datetime
    transactions["Date"] = pd.to_datetime(transactions["Date"])

    # Extract relevant arguments for each function
    cluster_kwargs = {
        key: kwargs[key]
        for key in ["eps", "min_samples", "include_amount"]
        if key in kwargs
    }
    recurring_kwargs = {
        key: kwargs[key] for key in ["min_frequency", "max_interval"] if key in kwargs
    }
    amount_kwargs = {key: kwargs[key] for key in ["max_variance"] if key in kwargs}

    # Cluster transactions
    transactions = cluster_transactions(transactions, **cluster_kwargs)

    # Identify recurring clusters
    transactions = identify_recurring_clusters(transactions, **recurring_kwargs)

    # Filter by amount variance
    if kwargs.get("include_amount", False):
        transactions = filter_by_amount_variance(transactions, **amount_kwargs)

    return transactions.sort_values(by=["Cluster", "Date"])
