"""Model factory for crop recommendation classification experiments."""

from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier


def build_classifiers(random_state: int = 42) -> dict[str, ClassifierMixin]:
    """Create fresh, reproducible classifier instances for comparison."""
    return {
        "Decision Tree": DecisionTreeClassifier(random_state=random_state),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000,
            random_state=random_state,
        ),
        "K-Nearest Neighbours": KNeighborsClassifier(n_neighbors=5),
        "Support Vector Machine": SVC(random_state=random_state),
        "Naive Bayes": GaussianNB(),
    }

