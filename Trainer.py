from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
from train_rf_data import generate_training_set


def train_model():
    X, y = generate_training_set()

    # Remove team names from features
    X_model = X.drop(columns=["team_a", "team_b"])

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_model,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Train model
    base_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
    )
    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    print("\n===== MODEL REPORT =====")
    print(classification_report(y_test, preds))
    print(f"Accuracy: {accuracy_score(y_test, preds):.3f}")

    # Save model
    joblib.dump(model, "Model/rf_matchup_model.joblib")
    print("✅ Model saved to Model/rf_matchup_model.joblib")

    return model


if __name__ == "__main__":
    train_model()
