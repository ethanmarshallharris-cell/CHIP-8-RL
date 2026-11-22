"""
The neural network that turns screens into features for the agent.

Stable-Baselines3's standard image network (NatureCNN) was designed for 84 x 84 Atari
screens and is too aggressive for CHIP-8's 64 x 32, so this is a smaller version of the
same idea: three convolution layers, then one fully connected layer.
"""

import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn


class Chip8CNN(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim=256):
        super().__init__(observation_space, features_dim)
        channels = observation_space.shape[0]           # 4 stacked frames
        self.cnn = nn.Sequential(
            nn.Conv2d(channels, 32, kernel_size=4, stride=2), nn.ReLU(),   # 32x64 -> 15x31
            nn.Conv2d(32, 64, kernel_size=3, stride=2), nn.ReLU(),         # -> 7x15
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),         # -> 5x13
            nn.Flatten(),
        )
        with torch.no_grad():
            sample = torch.as_tensor(observation_space.sample()[None]).float()
            n_flat = self.cnn(sample).shape[1]
        self.linear = nn.Sequential(nn.Linear(n_flat, features_dim), nn.ReLU())

    def forward(self, observations):
        return self.linear(self.cnn(observations))
