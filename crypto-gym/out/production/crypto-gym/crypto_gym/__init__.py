from gym.envs.registration import register

register(
    id='crypto-v0',
    entry_point='crypto_gym.envs:CryptoEnv',
)
register(
    id='crypto-extrahard-v0',
    entry_point='crypto_gym.envs:CryptoExtraHardEnv',
)