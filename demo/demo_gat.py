# coding=utf-8
import os

from tensorflow.python.keras.layers import Dense

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import tensorflow as tf
from tensorflow import keras
from tf_geometric.datasets.cora import CoraDataset
from tf_geometric.layers import GAT

graph, (train_index, valid_index, test_index) = CoraDataset().load_data()

num_classes = graph.y.shape[-1]

gat0 = GAT(64, activation=tf.nn.relu)
gat1 = GAT(num_classes)
dropout = keras.layers.Dropout(0.6)


def forward(graph, training=False):
    h = gat0([graph.x, graph.edge_index])
    h = dropout(h, training=training)
    h = gat1([h, graph.edge_index])
    return h


def compute_loss(logits, mask_index, vars):
    masked_logits = tf.gather(logits, mask_index)
    masked_labels = tf.gather(graph.y, mask_index)
    losses = tf.nn.softmax_cross_entropy_with_logits(
        logits=masked_logits,
        labels=masked_labels
    )

    kernel_vals = [var for var in vars if "kernel" in var.name]
    l2_losses = [tf.nn.l2_loss(kernel_var) for kernel_var in kernel_vals]

    return tf.reduce_mean(losses) + tf.add_n(l2_losses) * 5e-4


def evaluate():
    logits = forward(graph)
    masked_logits = tf.gather(logits, test_index)
    masked_labels = tf.gather(graph.y, test_index)

    y_pred = tf.argmax(masked_logits, axis=-1)
    y_true = tf.argmax(masked_labels, axis=-1)

    corrects = tf.cast(tf.equal(y_pred, y_true), tf.float32)
    accuracy = tf.reduce_mean(corrects)
    return accuracy


optimizer = tf.train.AdamOptimizer(learning_rate=1e-3)

for step in range(1000):
    with tf.GradientTape() as tape:
        logits = forward(graph, training=True)
        loss = compute_loss(logits, train_index, tape.watched_variables())

    vars = tape.watched_variables()
    grads = tape.gradient(loss, vars)
    optimizer.apply_gradients(zip(grads, vars))

    if step % 20 == 0:
        accuracy = evaluate()
        print("step = {}\tloss = {}\taccuracy = {}".format(step, loss, accuracy))