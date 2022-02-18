from fedml_api.distributed.split_nn.message_define import MyMessage
from fedml_core.distributed.facilitator.facilitator_manager import FacilitatorManager
from fedml_core.distributed.communication.message import Message
import logging
import torch

class SplitNNFacilitatorManager(FacilitatorManager):

    def __init__(self, arg_dict, trainer, backend="MPI"):
        super().__init__(arg_dict["args"], arg_dict["comm"], arg_dict["rank"],
                         arg_dict["max_rank"] + 1, backend)
        self.trainer = trainer
        self.round_idx = 0

    def run(self):
        super().run()

    def register_message_receive_handlers(self):
        self.register_message_receive_handler(MyMessage.MSG_TYPE_C2F_SEND_ACTS,
                                              self.handle_message_acts) # Done
        self.register_message_receive_handler(MyMessage.MSG_TYPE_C2F_VALIDATION_MODE,
                                              self.handle_message_validation_mode) # Done
        self.register_message_receive_handler(MyMessage.MSG_TYPE_C2F_VALIDATION_OVER,
                                              self.handle_message_validation_over) # Done
        self.register_message_receive_handler(MyMessage.MSG_TYPE_C2F_PROTOCOL_FINISHED,
                                              self.handle_message_finish_protocol) # Done
        self.register_message_receive_handler(MyMessage.MSG_TYPE_S2F_GRADS,
                                              self.handle_message_gradients) # Done

    def handle_message_gradients(self, msg_params):
        grads = msg_params.get(MyMessage.MSG_ARG_KEY_GRADS)
        logging.info("Step 6a: Facilitator performs back and sends it back to client {} ".format(self.trainer.active_node))
        grads = self.trainer.backward_pass(grads)
        self.send_grads_to_client(self.trainer.active_node,grads)

    def handle_message_acts(self, msg_params):
        acts, rank_info = msg_params.get(MyMessage.MSG_ARG_KEY_ACTS)
        acts, rank_info = self.trainer.forward_pass(acts, rank_info)
        logging.info("Step 4a: Facilitator receceives and performs forward prop")
        self.send_activations_to_server(acts, rank_info, self.trainer.SERVER_RANK)


    def send_activations_to_server(self, acts: torch.Tensor, rank_info: list, receive_id:int):
        logging.info("Step 4b: Facilitator Sends them to server")
        message = Message(MyMessage.MSG_TYPE_F2S_SEND_ACTS, self.get_sender_id(), receive_id)
        message.add_params(MyMessage.MSG_ARG_KEY_ACTS, (acts, rank_info))
        self.send_message(message)

    def send_grads_to_client(self, receive_id: int, grads: torch.Tensor):
        logging.info("Step 6b: Facilitator sends grads back to client {} ".format(self.trainer.active_node))
        message = Message(MyMessage.MSG_TYPE_F2C_GRADS, self.get_sender_id(), receive_id)
        message.add_params(MyMessage.MSG_ARG_KEY_GRADS, grads)
        self.send_message(message)

    def handle_message_validation_mode(self, msg_params):
        logging.info("Step 9 Alternative: Received the validation signal from client")
        self.send_validation_signal_to_server(self.trainer.SERVER_RANK)
        self.trainer.eval_mode()

    def send_validation_signal_to_server(self, receive_id: int):
        message = Message(MyMessage.MSG_TYPE_F2S_VALIDATION_MODE, self.get_sender_id(), receive_id)
        self.send_message(message)

    def handle_message_validation_over(self, msg_params):
        self.trainer.validation_over()
        self.send_validation_over_to_server(self.trainer.SERVER_RANK)

    def send_validation_over_to_server(self, receive_id: int):
        message = Message(MyMessage.MSG_TYPE_F2S_VALIDATION_OVER, self.get_sender_id(), receive_id)
        self.send_message(message)

    def handle_message_finish_protocol(self, msg_params):
        logging.info("Step 16: Facilitator received finish and is passing it on")
        self.send_finish_to_server(self.trainer.SERVER_RANK)

    def send_finish_to_server(self, receive_id: int):
        message = Message(MyMessage.MSG_TYPE_F2S_PROTOCOL_FINISHED, self.get_sender_id(), receive_id)
        self.send_message(message)