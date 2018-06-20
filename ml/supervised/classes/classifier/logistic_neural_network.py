#! /usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
from .classifier import Classifier
import copy
import numpy as np
import math
import logging

logger = logging.getLogger("main")


class LogisticNeuralNetwork(Classifier):

    __layers = []
    __initial_weights = []
    __weights = []
    __regularization_factor = 0
    __activations = []
    __gradients = []
    __previous_gradients = []
    __alpha = 0
    __beta = 0
    __ins_per_batch = 0
    __epsilon = 0.000001

    def __init__(self, layers, initial_weights, regularization_factor, alpha, beta, ins_per_batch):
        self.__layers = copy.deepcopy(layers)
        self.__initial_weights = copy.deepcopy(initial_weights)
        self.__weights = copy.deepcopy(initial_weights)
        self.__regularization_factor = regularization_factor
        self.__alpha = alpha
        self.__beta = beta
        self.__ins_per_batch = ins_per_batch

        self.__reset()

    def __reset(self):
        self.__weights = copy.deepcopy(self.__initial_weights)

        activations = []

        for num_neuron in self.__layers:
            layer_activation = []

            for i in range(0, num_neuron):
                layer_activation.append(None)

            activations.append(layer_activation)

        self.__activations = activations

        self.__gradients = self.__gen_gradients_struct()
        self.__previous_gradients = self.__gen_gradients_struct()

    def __gen_gradients_struct(self):
        gradients = []

        for weights_per_layer in self.__weights:
            gradients_per_layer = []
            for weights_per_neuron in weights_per_layer:
                zeros = np.zeros(len(weights_per_neuron))
                gradients_per_layer.append(zeros.tolist())

            gradients.append(gradients_per_layer)

        return gradients

    def __numerical_validation(self, data_handler):
        # Store a copy of the current weights
        aux_weights = list(self.__weights)

        numerical_gradients = []
        for weights_per_layer in self.__weights:
            gradients_per_layer = []
            for weights_per_neuron in weights_per_layer:
                gradients_per_neuron = []
                for i_weight in range(len(weights_per_neuron)):
                    current_weight = weights_per_neuron[i_weight]

                    weights_per_neuron[i_weight] = current_weight + self.__epsilon
                    JplusE = self.__total_cost(data_handler)
                    weights_per_neuron[i_weight] = current_weight - self.__epsilon
                    JminusE = self.__total_cost(data_handler)

                    numerical_gradient = (JplusE - JminusE) / (2 * self.__epsilon)
                    gradients_per_neuron.append(numerical_gradient)
                    weights_per_neuron[i_weight] = current_weight

                gradients_per_layer.append(gradients_per_neuron)

            numerical_gradients.append(gradients_per_layer)

        # Return weights to normal
        self.__weights = aux_weights

        self.__backpropagation(data_handler)

        errors = None
        for layer, ng_layer in zip(self.__gradients, numerical_gradients):
            layer_error = np.array(layer) - np.array(ng_layer)
            layer_error = np.fabs(layer_error)

            if errors is not None:
                errors = np.append(errors, np.sum(layer_error))
            else:
                errors = np.array(np.sum(layer_error))

        logger.debug("\nFinal gradients:\n" + str(np.array(self.__gradients)))

        logger.debug("\nFinal numerical gradients:\n" + str(np.array(numerical_gradients)))

        logger.debug("\nDifference between gradient via backpropagation & numerical gradient:\n" + str(errors))

    def __train(self, data_handler):
        if len(data_handler.as_instances()) > self.__ins_per_batch:
            batches = data_handler.stratify(round(len(data_handler.as_instances()) / self.__ins_per_batch))
        else:
            batches = [data_handler.as_instances()]

        stop = False

        previous_error = 0
        num_examples = 0

        while not stop:
            for minBatch in batches:
                self.__backpropagation(minBatch)
                self.__previous_gradients = copy.deepcopy(self.__gradients)
                self.__gradients = self.__gen_gradients_struct()

            current_error = self.__total_cost(data_handler.as_instances())
            num_examples += len(data_handler.as_instances())
            print("%d;%.5f" % (num_examples, current_error))
            stop = math.fabs(current_error - previous_error) < 0.0001
            previous_error = current_error

    def __instance_cost(self, instance):
        fw = self.__propagate(instance[0])
        j_instance = 0

        for i, output in enumerate(fw):
            j_instance = j_instance \
                            - instance[1][i] * math.log(output) - (1 - instance[1][i]) * math.log(1 - output)

        return j_instance

    def __total_cost(self, instances):
        j = None

        for instance in instances:
            j_instance = self.__instance_cost(instance)

            if j is not None:
                j = np.append(j, j_instance)
            else:
                j = np.array(j_instance)

        logger.debug("\nCosts without regularization:" + str(j))
        j = np.sum(j)/len(instances)

        # logger.debug("\nActivations:\n" + str(self.__activations))

        s = 0

        for weights_per_layer in self.__weights:
            for weights_per_neuron in weights_per_layer:
                for i_weights in range(1, len(weights_per_neuron)):
                    s += weights_per_neuron[i_weights] ** 2

        s = (self.__regularization_factor / (2 * len(instances))) * s

        logger.debug("Total cost(with regularization):" + str(j + s))
        return j + s

    def __propagate(self, instance):
        self.__activations[0] = list(instance)

        # Add the bias
        self.__activations[0].insert(0, 1.0)

        for i_hl in range(1, len(self.__activations) - 1):
            weights = np.array(self.__weights[i_hl - 1])
            act = np.array(self.__activations[i_hl - 1])
            terms = weights.dot(act)
            zs = terms.tolist()

            # Applies sigmoid
            self.__activations[i_hl] = [self.__activation(z) for z in zs]

            # Add the bias
            self.__activations[i_hl].insert(0, 1.0)

        i_ol = len(self.__activations) - 1

        weights = np.array(self.__weights[i_ol - 1])
        act = np.array(self.__activations[i_ol - 1])
        terms = weights.dot(act)
        zs = terms.tolist()

        self.__activations[i_ol] = [self.__activation(z) for z in zs]

        return self.__activations[i_ol]

    def __activation(self, z):
        return 1 / (1 + math.exp(-z))

    def __backpropagation(self, instances):
        last_layer = len(self.__activations) - 1
        logger.debug("\nStarting back propagation")

        for instance in instances:
            logger.debug("\nInstance:" + str(instance))
            # Propagate instance
            fw = self.__propagate(instance[0])
            logger.debug("\nOutput after propagating instance:" + str(fw))

            deltas = []
            deltas_out = []
            # Calculate neurons deltas for output layer
            for i, output in enumerate(fw):
                deltas_out.append(output - instance[1][i])

            deltas.append(deltas_out)

            # Calculate neurons deltas for hidden layers
            for k in range(last_layer - 1, 0, -1):
                weights = np.array(self.__weights[k])
                weights = np.transpose(weights)

                d_kplus1 = np.array(deltas[len(deltas) - 1])

                terms = weights.dot(d_kplus1)

                a_terms = np.ones((len(self.__activations[k]))) - np.array(self.__activations[k])
                a_terms = a_terms * np.array(self.__activations[k])

                delta_in = np.array(terms * a_terms).tolist()
                delta_in.pop(0)
                deltas.append(delta_in)

            deltas.reverse()
            logger.debug("\nDeltas for this instance:\n" + str(deltas))

            # Update gradient for each weight in each layer
            for k in range(last_layer - 1, -1, -1):
                delt = np.array(deltas[k])
                act = np.array(self.__activations[k])
                d_aux = np.outer(delt, act)
                logger.debug("\nGradients on layer " + str(k) + "for this instance:\n" + str(d_aux))
                d_aux = np.array(self.__gradients[k]) + d_aux
                self.__gradients[k] = d_aux.tolist()

        # Apply regularization to calculated gradients
        for k in range(last_layer - 1, -1, -1):
            p_aux = np.array(self.__weights[k])
            p_aux[:, 0] = 0
            p_aux = p_aux * self.__regularization_factor

            d_aux = (np.array(self.__gradients[k]) + p_aux) / len(instances)
            self.__gradients[k] = d_aux.tolist()

        # Update weights in each layer
        for k in range(last_layer - 1, -1, -1):
            factor = self.__beta * np.array(self.__previous_gradients[k]) + np.array(self.__gradients[k])
            weights = np.array(self.__weights[k]) - self.__alpha * factor

            self.__weights[k] = weights.tolist()

    def __calculate_gradient_rms(self):
        gradient_mean_square = 0
        number_of_gradients = 0
        for layer in self.__previous_gradients:
            for neuron in layer:
                for gradient in neuron:
                    gradient_mean_square += gradient ** 2
                    number_of_gradients += 1

        gradient_rms = math.sqrt(gradient_mean_square / number_of_gradients)

        return gradient_rms

    def classify(self, train_data_handler, test_instances):
        self.__reset()

        self.__train(train_data_handler)

        classified_instances = []

        for instance in test_instances:
            result = self.__propagate(instance)

            if len(train_data_handler.classes()) == 2:
                result = (float(round(result[0])),)
            else:
                idx_max = np.argmax(result)

                for idx_prev in range(0, len(result)):
                    if idx_max == idx_prev:
                        result[idx_max] = 1.0
                    else:
                        result[idx_prev] = 0.0

                result = tuple(result)

            classified_instances.append((instance, result))

        return classified_instances
