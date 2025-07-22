
# Main.py
from predict import simulate_season
from probability_models import MODEL_REGISTRY

def main():
    print("\n🚀 Running simulations across all probability models:")
    for model_name in MODEL_REGISTRY:
        simulate_season(model_name=model_name)

if __name__ == "__main__":
    print("Starting Full Model Comparison Simulation Suite...")
    main()