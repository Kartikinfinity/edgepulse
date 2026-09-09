"""DS-CNN baseline for 49x13 MFCC keyword spotting.

ONE architecture, chosen on evidence, not a menu to shop through.

Depthwise-separable CNN, after Zhang et al. "Hello Edge: Keyword Spotting on
Microcontrollers" (arXiv 1711.07128), which found DS-CNN gave the best
accuracy-per-operation of the architectures it compared for exactly this task
and this input size. It is also the family the prior build measured on THIS
board: 7,779 params at 49x13 ran in 84.17 ms with ESP-NN, inside the 200 ms
inference cadence.

Sizing follows from that measurement rather than from taste. Phase 1 puts RAM
and CPU out of scope, but NOT the real-time limit - inference must still finish
inside the cadence - so the design targets roughly the same MAC count as the
prior build rather than inflating the model because the budget was lifted.

Output is 3 classes (keyword / unknown / background), the `model_target`
mapping in the dataset. The 6-way `class` label is kept in the manifest for
diagnosis, so per-tier false-accept rates can be reported without retraining.
"""

from __future__ import annotations

import numpy as np

from .features import N_FRAMES, N_MFCC

CLASS_NAMES = ("keyword", "unknown", "background")
N_CLASSES = len(CLASS_NAMES)
KEYWORD_IDX = 0


def build_dscnn(n_classes: int = N_CLASSES, channels: int = 48,
                n_blocks: int = 3, dropout: float = 0.15):
    """DS-CNN: strided conv stem + n_blocks depthwise-separable blocks + GAP.

    channels=48, n_blocks=3 gives ~2.6M MACs, close to the prior build's
    measured 84 ms operating point on this hardware.
    """
    import tensorflow as tf
    from tensorflow.keras import layers

    inp = layers.Input(shape=(N_FRAMES, N_MFCC, 1), name="mfcc")

    # Stem: a wide-in-time kernel, striding only in time. Frequency is only 13
    # bins wide, so striding it away early would discard the spectral detail the
    # /k/->/SH/ transition lives in.
    x = layers.Conv2D(channels, (10, 4), strides=(2, 1), padding="same",
                      use_bias=False, name="stem_conv")(inp)
    x = layers.BatchNormalization(name="stem_bn")(x)
    x = layers.ReLU(name="stem_relu")(x)

    for i in range(n_blocks):
        x = layers.DepthwiseConv2D((3, 3), padding="same", use_bias=False,
                                   name=f"dw{i}")(x)
        x = layers.BatchNormalization(name=f"dw{i}_bn")(x)
        x = layers.ReLU(name=f"dw{i}_relu")(x)
        x = layers.Conv2D(channels, (1, 1), padding="same", use_bias=False,
                          name=f"pw{i}")(x)
        x = layers.BatchNormalization(name=f"pw{i}_bn")(x)
        x = layers.ReLU(name=f"pw{i}_relu")(x)

    x = layers.GlobalAveragePooling2D(name="gap")(x)
    if dropout > 0:
        x = layers.Dropout(dropout, name="drop")(x)
    out = layers.Dense(n_classes, activation="softmax", name="probs")(x)

    return tf.keras.Model(inp, out, name="dscnn_takshila")


def count_macs(model) -> int:
    """Approximate multiply-accumulates for one inference.

    Reported because it is what predicts on-device latency; parameter count does
    not. A model can be small and slow.
    """
    macs = 0
    for layer in model.layers:
        cfg = layer.__class__.__name__
        try:
            out = layer.output_shape
        except AttributeError:
            continue
        if isinstance(out, list) or out is None:
            continue
        if cfg == "Conv2D":
            kh, kw = layer.kernel_size
            cin = layer.input_shape[-1]
            macs += out[1] * out[2] * out[3] * kh * kw * cin
        elif cfg == "DepthwiseConv2D":
            kh, kw = layer.kernel_size
            macs += out[1] * out[2] * out[3] * kh * kw
        elif cfg == "Dense":
            macs += layer.input_shape[-1] * out[-1]
    return int(macs)


def summarise(model) -> dict:
    params = int(sum(np.prod(w.shape) for w in model.trainable_weights))
    macs = count_macs(model)
    return {
        "name": model.name,
        "params": params,
        "macs_per_inference": macs,
        "input_shape": [N_FRAMES, N_MFCC, 1],
        "output_classes": list(CLASS_NAMES),
        # The prior build measured 84.17 ms for ~2.7M MACs on this board with
        # ESP-NN. This is a projection from that single point, not a measurement.
        "projected_device_ms_at_prior_rate": round(macs / 2.7e6 * 84.17, 1),
    }
