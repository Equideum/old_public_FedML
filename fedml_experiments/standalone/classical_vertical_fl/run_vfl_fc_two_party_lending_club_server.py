import os
import sys

from sklearn.utils import shuffle

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "../../../")))
from fedml_api.data_preprocessing.lending_club_loan.lending_club_dataset import loan_load_two_party_data
from fedml_api.standalone.classical_vertical_fl.vfl_fixture_server import FederatedLearningFixture
from fedml_api.standalone.classical_vertical_fl.party_models_server import VFLGuestModel, VFLHostModel, VFLServerModel
from fedml_api.model.finance.vfl_models_standalone import LocalModel, DenseModel
from fedml_api.standalone.classical_vertical_fl.vfl_server import VerticalMultiplePartyLogisticRegressionFederatedLearning


def run_experiment(train_data, test_data, batch_size, learning_rate, epoch):
    print("hyper-parameters:")
    print("batch size: {0}".format(batch_size))
    print("learning rate: {0}".format(learning_rate))

    Xa_train, Xb_train, y_train = train_data
    Xa_test, Xb_test, y_test = test_data

    print("################################ Wire Federated Models ############################")

    # create local models for both party A and party B
    party_a_local_model = LocalModel(input_dim=Xa_train.shape[1], output_dim=10, learning_rate=learning_rate)
    party_b_local_model = LocalModel(input_dim=Xb_train.shape[1], output_dim=20, learning_rate=learning_rate)

    # Instantiates the Guest, Host and Server
    partyA = VFLGuestModel(local_model=party_a_local_model)
    partyB = VFLHostModel(local_model=party_b_local_model)
    server_vfl = VFLServerModel(party_a_local_model.get_output_dim(), party_b_local_model.get_output_dim())


    # Adds a dense model for the host and guest
    server_dense_model_host = DenseModel(party_b_local_model.get_output_dim(), 1, learning_rate=learning_rate, bias=False)
    server_dense_model_guest = DenseModel(party_a_local_model.get_output_dim(), 1, learning_rate=learning_rate, bias=True)
    server_vfl.set_dense_model(server_dense_model_host,"host")
    server_vfl.set_dense_model(server_dense_model_guest, "guest")

    party_B_id = "B"
    federatedLearning = VerticalMultiplePartyLogisticRegressionFederatedLearning(partyA,server_vfl)
    federatedLearning.add_party(id=party_B_id, party_model=partyB)
    federatedLearning.set_debug(is_debug=False)

    print("################################ Train Federated Models ############################")

    fl_fixture = FederatedLearningFixture(federatedLearning)

    train_data = {federatedLearning.get_main_party_id(): {"X": Xa_train, "Y": y_train},
                  "party_list": {party_B_id: Xb_train}}
    test_data = {federatedLearning.get_main_party_id(): {"X": Xa_test, "Y": y_test},
                 "party_list": {party_B_id: Xb_test}}

    fl_fixture.fit(train_data=train_data, test_data=test_data, epochs=epoch, batch_size=batch_size)


if __name__ == '__main__':
    print("################################ Prepare Data ############################")
    data_dir = "../../../data/lending_club_loan/"
    train, test = loan_load_two_party_data(data_dir)
    Xa_train, Xb_train, y_train = train
    Xa_test, Xb_test, y_test = test

    batch_size = 256
    epoch = 10
    lr = 0.001

    Xa_train, Xb_train, y_train = shuffle(Xa_train, Xb_train, y_train)
    Xa_test, Xb_test, y_test = shuffle(Xa_test, Xb_test, y_test)
    train = [Xa_train, Xb_train, y_train]
    test = [Xa_test, Xb_test, y_test]
    run_experiment(train_data=train, test_data=test, batch_size=batch_size, learning_rate=lr, epoch=epoch)

    # reference training result:
    # --- epoch: 99, batch: 1547, loss: 0.11550658332804839, acc: 0.9359105089400196, auc: 0.8736984159409958
    # --- (0.9270889578726378, 0.5111934752243287, 0.5054099033579607, None)