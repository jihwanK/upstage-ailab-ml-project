import pickle

def load_model(filename):
    return pickle.load(open(filename, 'rb'))

model = load_model("../../../data/model/model.pkl")
