from strength_of_schedule import get_sos_info
from predict import simulate_season
from probability_models import MODEL_REGISTRY

def main():
    print("🔄 Step 1: Calculating Strength of Schedule...")
    sos_dict, league_avg = get_sos_info()

    print("\n🚀 Step 2: Running simulations across all probability models:")
    for model_name in MODEL_REGISTRY:
        simulate_season(sos_dict, league_avg, model_name=model_name)

if __name__ == "__main__":
    print("🏈 Starting Full Model Comparison Simulation Suite...")
    main()
